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
})
