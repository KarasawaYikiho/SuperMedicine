import { connect, type Socket } from "node:net"
import { randomUUID } from "node:crypto"

const VERSION = 1
const DEFAULT_MAX_FRAME_BYTES = 1024 * 1024

export class BridgeError extends Error {
  code: string
  recoverable: boolean

  constructor(code: string, message: string, recoverable = false) {
    super(message)
    this.name = "BridgeError"
    this.code = code
    this.recoverable = recoverable
  }
}

type Pending = {
  resolve: (value: unknown) => void
  reject: (reason: Error) => void
  onEvent?: (event: string, data: unknown) => void
  timer: ReturnType<typeof setTimeout>
}

export class BridgeClient {
  readonly host: string
  readonly port: number
  readonly maxFrameBytes: number
  #token: string
  #socket?: Socket
  #connectingSocket?: Socket
  #connectPromise?: Promise<void>
  #buffer = Buffer.alloc(0)
  #pending = new Map<string, Pending>()
  #abandoned = new Map<string, number>()
  #requestTimeoutMs: number
  onDisconnect?: (error: BridgeError) => void

  constructor(
    host: string,
    port: number,
    token: string,
    maxFrameBytes = DEFAULT_MAX_FRAME_BYTES,
    requestTimeoutMs = 30_000,
  ) {
    if (
      host !== "127.0.0.1" ||
      !Number.isInteger(port) ||
      port < 1 ||
      !token ||
      !Number.isInteger(maxFrameBytes) ||
      maxFrameBytes < 256 ||
      !Number.isFinite(requestTimeoutMs) ||
      requestTimeoutMs < 1
    ) {
      throw new BridgeError("invalid_configuration", "Invalid local bridge configuration")
    }
    this.host = host
    this.port = port
    this.#token = token
    this.maxFrameBytes = maxFrameBytes
    this.#requestTimeoutMs = requestTimeoutMs
  }

  static fromEnvironment(environment = process.env): BridgeClient {
    return new BridgeClient(
      environment.SUPERMEDICINE_TUI_BRIDGE_HOST || "",
      Number(environment.SUPERMEDICINE_TUI_BRIDGE_PORT),
      environment.SUPERMEDICINE_TUI_BRIDGE_TOKEN || "",
    )
  }

  static environmentConfigured(environment = process.env): boolean {
    return Boolean(environment.SUPERMEDICINE_TUI_BRIDGE_PORT && environment.SUPERMEDICINE_TUI_BRIDGE_TOKEN)
  }

  async connect(): Promise<void> {
    if (this.#socket && !this.#socket.destroyed) return Promise.resolve()
    if (this.#connectPromise) return this.#connectPromise
    const attempt = new Promise<void>((resolve, reject) => {
      const socket = connect({ host: this.host, port: this.port })
      this.#connectingSocket = socket
      const fail = () => {
        socket.destroy()
        reject(new BridgeError("disconnected", "Python bridge is unavailable", true))
      }
      socket.once("connect", () => {
        socket.off("error", fail)
        this.#connectingSocket = undefined
        this.#socket = socket
        resolve()
      })
      socket.once("error", fail)
      socket.on("data", (chunk) => this.#receive(chunk))
      socket.on("close", () => this.#disconnect(socket))
      socket.on("error", () => this.#disconnect(socket))
    })
    this.#connectPromise = attempt
    try {
      await attempt
    } finally {
      if (this.#connectPromise === attempt) this.#connectPromise = undefined
      this.#connectingSocket = undefined
    }
  }

  request(
    method: string,
    params: Record<string, unknown> = {},
    onEvent?: Pending["onEvent"],
    timeoutMs = this.#requestTimeoutMs,
  ): Promise<any> {
    return this.startRequest(method, params, onEvent, timeoutMs).promise
  }

  startRequest(
    method: string,
    params: Record<string, unknown> = {},
    onEvent?: Pending["onEvent"],
    timeoutMs = this.#requestTimeoutMs,
  ): {
    id: string
    promise: Promise<any>
    cancel: () => void
  } {
    const id = randomUUID()
    const promise = new Promise((resolve, reject) => {
      if (!Number.isFinite(timeoutMs) || timeoutMs < 1) {
        reject(new BridgeError("invalid_request", "Bridge request timeout is invalid"))
        return
      }
      if (!this.#socket || this.#socket.destroyed) {
        reject(new BridgeError("disconnected", "Python bridge is disconnected", true))
        return
      }
      const timer = setTimeout(() => {
        const pending = this.#pending.get(id)
        if (!pending) return
        this.#pending.delete(id)
        this.#rememberAbandoned(id)
        try {
          this.cancel(id, method)
        } catch {
          // The timeout already rejects the request; disconnect cleanup owns the socket.
        }
        pending.reject(new BridgeError("client_timeout", "Bridge request timed out", true))
      }, timeoutMs)
      this.#pending.set(id, { resolve, reject, onEvent, timer })
      try {
        this.#write({ version: VERSION, id, type: "request", method, params, token: this.#token })
      } catch (error) {
        clearTimeout(timer)
        this.#pending.delete(id)
        reject(error instanceof Error ? error : new BridgeError("invalid_request", "Bridge request is invalid"))
      }
    })
    return { id, promise, cancel: () => this.cancel(id, method) }
  }

  cancel(id: string, method = "cancel"): void {
    this.#write({ version: VERSION, id, type: "cancel", method, params: {}, token: this.#token })
  }

  disconnect(): void {
    const socket = this.#socket
    this.#socket = undefined
    this.#connectingSocket?.destroy()
    this.#connectingSocket = undefined
    socket?.destroy()
    this.#buffer = Buffer.alloc(0)
    this.#abandoned.clear()
    const error = new BridgeError("disconnected", "Python bridge disconnected", true)
    this.#rejectAll(error)
    this.onDisconnect?.(error)
  }

  close(): void {
    const socket = this.#socket
    this.#socket = undefined
    this.#connectingSocket?.destroy()
    this.#connectingSocket = undefined
    socket?.destroy()
    this.#buffer = Buffer.alloc(0)
    this.#abandoned.clear()
    this.#rejectAll(new BridgeError("disconnected", "Python bridge closed", true))
    this.#token = ""
  }

  #write(frame: object): void {
    if (!this.#socket || this.#socket.destroyed) {
      throw new BridgeError("disconnected", "Python bridge is disconnected", true)
    }
    let payload: string
    try {
      payload = `${JSON.stringify(frame)}\n`
    } catch {
      throw new BridgeError("invalid_request", "Bridge request is not serializable")
    }
    if (Buffer.byteLength(payload) > this.maxFrameBytes) {
      throw new BridgeError("frame_too_large", "Bridge request exceeded the frame limit")
    }
    this.#socket.write(payload)
  }

  #receive(chunk: Buffer): void {
    this.#buffer = Buffer.concat([this.#buffer, chunk])
    if (this.#buffer.length > this.maxFrameBytes && !this.#buffer.includes(10)) {
      this.#protocolFailure("Bridge response exceeded the frame limit")
      return
    }
    let newline = this.#buffer.indexOf(10)
    while (newline >= 0) {
      const raw = this.#buffer.subarray(0, newline)
      this.#buffer = this.#buffer.subarray(newline + 1)
      if (raw.length > this.maxFrameBytes) {
        this.#protocolFailure("Bridge response exceeded the frame limit")
        return
      }
      try {
        this.#handle(JSON.parse(raw.toString("utf8")))
      } catch {
        this.#protocolFailure("Python bridge sent an invalid response")
        return
      }
      newline = this.#buffer.indexOf(10)
    }
  }

  #handle(frame: any): void {
    if (!frame || frame.version !== VERSION || typeof frame.id !== "string") {
      this.#protocolFailure("Python bridge sent a mismatched response")
      return
    }
    const pending = this.#pending.get(frame.id)
    if (!pending) {
      const expiresAt = this.#abandoned.get(frame.id)
      if (expiresAt && expiresAt > Date.now()) {
        if (frame.type === "event" && ["progress", "chunk", "completed"].includes(frame.event)) return
        if (frame.type === "result") {
          this.#abandoned.delete(frame.id)
          return
        }
        if (frame.type === "error" && typeof frame.error?.code === "string" && typeof frame.error?.message === "string") {
          this.#abandoned.delete(frame.id)
          return
        }
      } else if (expiresAt) {
        this.#abandoned.delete(frame.id)
      }
      this.#protocolFailure("Python bridge sent an unknown response")
      return
    }
    if (frame.type === "event") {
      if (!["progress", "chunk", "completed"].includes(frame.event)) {
        this.#protocolFailure("Python bridge sent an unsupported event")
        return
      }
      pending.onEvent?.(String(frame.event), frame.data)
    } else if (frame.type === "result") {
      this.#pending.delete(frame.id)
      clearTimeout(pending.timer)
      pending.resolve(frame.result)
    } else if (frame.type === "error") {
      if (!frame.error || typeof frame.error.code !== "string" || typeof frame.error.message !== "string") {
        this.#protocolFailure("Python bridge sent a malformed error")
        return
      }
      this.#pending.delete(frame.id)
      clearTimeout(pending.timer)
      pending.reject(new BridgeError(frame.error.code, frame.error.message))
    } else {
      this.#protocolFailure("Python bridge sent an unsupported response")
    }
  }

  #protocolFailure(message: string): void {
    this.#socket?.destroy()
    this.#rejectAll(new BridgeError("protocol_error", message, true))
  }

  #rememberAbandoned(id: string): void {
    const now = Date.now()
    for (const [candidate, expiresAt] of this.#abandoned) {
      if (expiresAt <= now) this.#abandoned.delete(candidate)
    }
    this.#abandoned.set(id, now + Math.max(30_000, this.#requestTimeoutMs * 4))
    while (this.#abandoned.size > 256) {
      const oldest = this.#abandoned.keys().next().value
      if (typeof oldest !== "string") break
      this.#abandoned.delete(oldest)
    }
  }

  #disconnect(socket: Socket): void {
    if (this.#socket !== socket) return
    this.#socket = undefined
    this.#buffer = Buffer.alloc(0)
    this.#abandoned.clear()
    const error = new BridgeError("disconnected", "Python bridge disconnected", true)
    this.#rejectAll(error)
    this.onDisconnect?.(error)
  }

  #rejectAll(error: BridgeError): void {
    for (const pending of this.#pending.values()) {
      clearTimeout(pending.timer)
      pending.reject(error)
    }
    this.#pending.clear()
  }
}
