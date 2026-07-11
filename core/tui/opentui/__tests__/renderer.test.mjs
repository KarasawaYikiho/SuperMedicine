import { expect, test } from "bun:test"
import { TextRenderable } from "@opentui/core"
import { createTestRenderer } from "@opentui/core/testing"

test("OpenTUI 0.4.3 test renderer renders and is destroyed", async () => {
  const { renderer, renderOnce, captureCharFrame } = await createTestRenderer({
    width: 24,
    height: 4,
  })
  let destroyed = false
  renderer.once("destroy", () => {
    destroyed = true
  })

  try {
    renderer.root.add(
      new TextRenderable(renderer, {
        id: "phase-zero-smoke",
        content: "SuperMedicine OpenTUI",
      }),
    )
    await renderOnce()

    expect(captureCharFrame()).toContain("SuperMedicine OpenTUI")
  } finally {
    renderer.destroy()
  }

  expect(destroyed).toBe(true)
})
