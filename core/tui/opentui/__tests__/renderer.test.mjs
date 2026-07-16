import { expect, test } from "bun:test"
import { InputRenderable, ScrollBoxRenderable, TextRenderable } from "@opentui/core"
import { createTestRenderer, MouseButtons } from "@opentui/core/testing"
import { ROUTES } from "../state.ts"
import { mountShell } from "../main.ts"

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

test("route metadata contains no demo page catalogue fields", () => {
  expect(ROUTES.length).toBeGreaterThan(10)
  for (const route of ROUTES) {
    expect(Object.keys(route).sort()).toEqual(["capability", "id", "label", "shortcut", "symbol"])
    expect(route.label).toMatch(/[\u3400-\u9fff]/)
    expect(route.symbol).toMatch(/^[●○›+×]$/)
  }
})

test("shell uses real page scroll boxes and chat-only input", async () => {
  const { renderer, renderOnce, captureCharFrame } = await createTestRenderer({ width: 100, height: 30 })
  try {
    const shell = mountShell(renderer)
    await renderOnce()

    expect(renderer.root.findDescendantById("page-chat")).toBeInstanceOf(ScrollBoxRenderable)
    expect(renderer.root.findDescendantById("prompt-input")).toBeInstanceOf(InputRenderable)
    expect(captureCharFrame()).not.toMatch(/Sections:|Records:|Actions:|intent|Project:|route=|focus=|menu=/)

    for (const route of ROUTES.filter((route) => route.id !== "chat")) {
      shell.activateRoute(route.id)
      await renderOnce()
      expect(renderer.root.findDescendantById(`page-${route.id}`)).toBeInstanceOf(ScrollBoxRenderable)
      expect(renderer.root.findDescendantById("prompt-input")).toBeUndefined()
    }
    shell.activateRoute("dashboard")
    await renderOnce()
    expect(captureCharFrame()).toContain("状态看板")
  } finally {
    renderer.destroy()
  }
})

test("left mouse activates a focusable navigation item", async () => {
  const { renderer, mockMouse, renderOnce, captureCharFrame } = await createTestRenderer({ width: 100, height: 30 })
  try {
    const shell = mountShell(renderer)
    await renderOnce()
    const nav = renderer.root.findDescendantById("nav-workspace")

    expect(nav?.focusable).toBe(true)
    await mockMouse.moveTo(nav.x + 2, nav.y)
    expect(shell.state.hoveredRoute).toBe("workspace")
    await mockMouse.click(nav.x + 2, nav.y, MouseButtons.RIGHT)
    expect(shell.state.currentRoute).toBe("chat")
    await mockMouse.click(nav.x + 2, nav.y)
    await renderOnce()

    expect(shell.state.currentRoute).toBe("workspace")
    expect(nav.focused).toBe(true)
    expect(captureCharFrame()).toContain("工作区")
  } finally {
    renderer.destroy()
  }
})
