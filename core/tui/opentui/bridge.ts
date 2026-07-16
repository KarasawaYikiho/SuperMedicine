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
}

export class BridgeClient {
  readonly host: string
  readonly port: number
  readonly maxFrameBytes: number
  #token: string
  #socket?: Socket
  #buffer = Buffer.alloc(0)
  #pending = new Map<string, Pending>()
  onDisconnect?: (error: BridgeError) => void

  constructor(host: string, port: number, token: string, maxFrameBytes = DEFAULT_MAX_FRAME_BYTES) {
    if (host !== "127.0.0.1" || !Number.isInteger(port) || port < 1 || !token) {
      throw new BridgeError("invalid_configuration", "Invalid local bridge configuration")
    }
    this.host = host
    this.port = port
    this.#token = token
    this.maxFrameBytes = maxFrameBytes
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

  connect(): Promise<void> {
    if (this.#socket && !this.#socket.destroyed) return Promise.resolve()
    return new Promise((resolve, reject) => {
      const socket = connect({ host: this.host, port: this.port })
      const fail = () => reject(new BridgeError("disconnected", "Python bridge is unavailable", true))
      socket.once("connect", () => {
        socket.off("error", fail)
        this.#socket = socket
        resolve()
      })
      socket.once("error", fail)
      socket.on("data", (chunk) => this.#receive(chunk))
      socket.on("close", () => this.#disconnect(socket))
      socket.on("error", () => this.#disconnect(socket))
    })
  }

  request(method: string, params: Record<string, unknown> = {}, onEvent?: Pending["onEvent"]): Promise<any> {
    return this.startRequest(method, params, onEvent).promise
  }

  startRequest(method: string, params: Record<string, unknown> = {}, onEvent?: Pending["onEvent"]): {
    id: string
    promise: Promise<any>
    cancel: () => void
  } {
    const id = randomUUID()
    const promise = new Promise((resolve, reject) => {
      if (!this.#socket || this.#socket.destroyed) {
        reject(new BridgeError("disconnected", "Python bridge is disconnected", true))
        return
      }
      this.#pending.set(id, { resolve, reject, onEvent })
      this.#write({ version: VERSION, id, type: "request", method, params, token: this.#token })
    })
    return { id, promise, cancel: () => this.cancel(id, method) }
  }

  cancel(id: string, method = "cancel"): void {
    this.#write({ version: VERSION, id, type: "cancel", method, params: {}, token: this.#token })
  }

  close(): void {
    const socket = this.#socket
    this.#socket = undefined
    socket?.destroy()
    this.#buffer = Buffer.alloc(0)
    this.#rejectAll(new BridgeError("disconnected", "Python bridge closed", true))
    this.#token = ""
  }

  #write(frame: object): void {
    if (!this.#socket || this.#socket.destroyed) return
    this.#socket.write(`${JSON.stringify(frame)}\n`)
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
    if (frame?.version !== VERSION || typeof frame.id !== "string") return
    const pending = this.#pending.get(frame.id)
    if (!pending) return
    if (frame.type === "event") {
      pending.onEvent?.(String(frame.event), frame.data)
    } else if (frame.type === "result") {
      this.#pending.delete(frame.id)
      pending.resolve(frame.result)
    } else if (frame.type === "error") {
      this.#pending.delete(frame.id)
      pending.reject(new BridgeError(frame.error?.code || "bridge_error", frame.error?.message || "Bridge request failed"))
    }
  }

  #protocolFailure(message: string): void {
    this.#socket?.destroy()
    this.#rejectAll(new BridgeError("protocol_error", message, true))
  }

  #disconnect(socket: Socket): void {
    if (this.#socket !== socket) return
    this.#socket = undefined
    this.#buffer = Buffer.alloc(0)
    const error = new BridgeError("disconnected", "Python bridge disconnected", true)
    this.#rejectAll(error)
    this.onDisconnect?.(error)
  }

  #rejectAll(error: BridgeError): void {
    for (const pending of this.#pending.values()) pending.reject(error)
    this.#pending.clear()
  }
}
