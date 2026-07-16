import { afterEach, describe, expect, test } from "bun:test"
import { createServer, type Server } from "node:net"
import { BridgeClient, BridgeError } from "../bridge.ts"

let server: Server | undefined

afterEach(() => new Promise<void>((resolve) => server?.close(() => resolve()) || resolve()))

describe("BridgeClient", () => {
  test("turns a disconnect into a recoverable error and reconnects without leaking its token", async () => {
    let connection = 0
    server = createServer((socket) => {
      connection += 1
      socket.once("data", (raw) => {
        const frame = JSON.parse(raw.toString("utf8"))
        if (connection === 1) {
          socket.destroy()
          return
        }
        socket.write(`${JSON.stringify({ version: 1, id: frame.id, type: "result", result: { ok: true } })}\n`)
      })
    })
    await new Promise<void>((resolve) => server!.listen(0, "127.0.0.1", resolve))
    const address = server.address()
    if (!address || typeof address === "string") throw new Error("test server did not bind")
    const token = "high-entropy-test-token-that-must-stay-private"
    const client = new BridgeClient("127.0.0.1", address.port, token)

    await client.connect()
    const first = client.startRequest("status")
    expect(first.id).toBeString()
    expect(first.cancel).toBeFunction()
    const failure = await first.promise.catch((error) => error)
    expect(failure).toBeInstanceOf(BridgeError)
    expect(failure.recoverable).toBe(true)
    expect(String(failure)).not.toContain(token)

    await client.connect()
    expect(await client.request("status")).toEqual({ ok: true })
    client.close()
  })

  test("bounds pending requests with a client timeout", async () => {
    server = createServer(() => {})
    await new Promise<void>((resolve) => server!.listen(0, "127.0.0.1", resolve))
    const address = server.address()
    if (!address || typeof address === "string") throw new Error("test server did not bind")
    const client = new BridgeClient("127.0.0.1", address.port, "token", 256, 40)
    await client.connect()
    const oversized = await client.request("status", { value: "x".repeat(1000) }).catch((reason) => reason)
    expect(oversized.code).toBe("frame_too_large")
    const error = await client.request("status").catch((reason) => reason)
    expect(error).toBeInstanceOf(BridgeError)
    expect(error.code).toBe("client_timeout")
    expect(error.recoverable).toBe(true)
    client.close()
  })

  test("ignores late events through the abandoned terminal and keeps the socket healthy", async () => {
    let request = 0
    server = createServer((socket) => {
      socket.on("data", (raw) => {
        for (const line of raw.toString("utf8").trim().split("\n")) {
          const frame = JSON.parse(line)
          if (frame.type !== "request") continue
          request += 1
          if (request === 1) {
            setTimeout(() => socket.write(`${JSON.stringify({ version: 1, id: frame.id, type: "event", event: "chunk", data: "late" })}\n`), 45)
            setTimeout(() => socket.write(`${JSON.stringify({ version: 1, id: frame.id, type: "error", error: { code: "cancelled", message: "cancelled" } })}\n`), 55)
          } else {
            socket.write(`${JSON.stringify({ version: 1, id: frame.id, type: "result", result: { ok: true } })}\n`)
          }
        }
      })
    })
    await new Promise<void>((resolve) => server!.listen(0, "127.0.0.1", resolve))
    const address = server.address()
    if (!address || typeof address === "string") throw new Error("test server did not bind")
    const client = new BridgeClient("127.0.0.1", address.port, "token", 1024, 25)
    let disconnected = false
    client.onDisconnect = () => { disconnected = true }
    await client.connect()
    expect((await client.request("slow").catch((error) => error)).code).toBe("client_timeout")
    await Bun.sleep(80)
    expect(await client.request("status")).toEqual({ ok: true })
    expect(disconnected).toBe(false)
    client.close()
  })

  test("ignores a lone late terminal response", async () => {
    let request = 0
    server = createServer((socket) => {
      socket.on("data", (raw) => {
        for (const line of raw.toString("utf8").trim().split("\n")) {
          const frame = JSON.parse(line)
          if (frame.type !== "request") continue
          request += 1
          if (request === 1) {
            setTimeout(() => socket.write(`${JSON.stringify({ version: 1, id: frame.id, type: "result", result: "late" })}\n`), 45)
          } else {
            socket.write(`${JSON.stringify({ version: 1, id: frame.id, type: "result", result: { ok: true } })}\n`)
          }
        }
      })
    })
    await new Promise<void>((resolve) => server!.listen(0, "127.0.0.1", resolve))
    const address = server.address()
    if (!address || typeof address === "string") throw new Error("test server did not bind")
    const client = new BridgeClient("127.0.0.1", address.port, "token", 1024, 25)
    await client.connect()
    expect((await client.request("slow").catch((error) => error)).code).toBe("client_timeout")
    await Bun.sleep(60)
    expect(await client.request("status")).toEqual({ ok: true })
    client.disconnect()
    client.close()
  })

  test("drops abandoned ids when a connection generation ends", async () => {
    let connection = 0
    let abandonedId = ""
    server = createServer((socket) => {
      connection += 1
      socket.once("data", (raw) => {
        const frame = JSON.parse(raw.toString("utf8").trim().split("\n")[0])
        if (connection === 1) {
          abandonedId = frame.id
          return
        }
        socket.write(`${JSON.stringify({ version: 1, id: abandonedId, type: "result", result: "stale generation" })}\n`)
      })
    })
    await new Promise<void>((resolve) => server!.listen(0, "127.0.0.1", resolve))
    const address = server.address()
    if (!address || typeof address === "string") throw new Error("test server did not bind")
    const client = new BridgeClient("127.0.0.1", address.port, "token", 1024, 25)
    await client.connect()
    expect((await client.request("slow").catch((error) => error)).code).toBe("client_timeout")
    client.disconnect()
    await Bun.sleep(5)
    await client.connect()
    expect((await client.request("status").catch((error) => error)).code).toBe("protocol_error")
    client.close()
  })

  test("rejects mismatched correlated responses and shares an in-flight connection", async () => {
    let connections = 0
    server = createServer((socket) => {
      connections += 1
      socket.once("data", (raw) => {
        const frame = JSON.parse(raw.toString("utf8"))
        socket.write(`${JSON.stringify({ version: 2, id: frame.id, type: "result", result: null })}\n`)
      })
    })
    await new Promise<void>((resolve) => server!.listen(0, "127.0.0.1", resolve))
    const address = server.address()
    if (!address || typeof address === "string") throw new Error("test server did not bind")
    const client = new BridgeClient("127.0.0.1", address.port, "token")
    await Promise.all([client.connect(), client.connect()])
    expect(connections).toBe(1)
    const error = await client.request("status").catch((reason) => reason)
    expect(error.code).toBe("protocol_error")
    expect(error.recoverable).toBe(true)
    client.close()
  })

  test("rejects a response for an unknown request id", async () => {
    server = createServer((socket) => {
      socket.once("data", () => {
        socket.write(`${JSON.stringify({ version: 1, id: "unknown", type: "result", result: null })}\n`)
      })
    })
    await new Promise<void>((resolve) => server!.listen(0, "127.0.0.1", resolve))
    const address = server.address()
    if (!address || typeof address === "string") throw new Error("test server did not bind")
    const client = new BridgeClient("127.0.0.1", address.port, "token")
    await client.connect()
    const error = await client.request("status").catch((reason) => reason)
    expect(error.code).toBe("protocol_error")
    client.close()
  })
})
