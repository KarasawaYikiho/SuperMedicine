import { expect, test } from "bun:test"
import { BoxRenderable, InputRenderable, MarkdownRenderable, ScrollBoxRenderable, SelectRenderable, TextRenderable } from "@opentui/core"
import { createTestRenderer, MouseButtons } from "@opentui/core/testing"
import { ROUTES } from "../state.ts"
import { mountShell, runAutomatedMode } from "../main.ts"

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

test("page shells use honest native list, form, and action controls", async () => {
  const { renderer, renderOnce, captureCharFrame } = await createTestRenderer({ width: 100, height: 30 })
  try {
    const shell = mountShell(renderer)
    expect(renderer.root.findDescendantById("page-markdown-chat")).toBeInstanceOf(MarkdownRenderable)
    shell.activateRoute("workspace")
    await renderOnce()
    expect(renderer.root.findDescendantById("page-field-workspace")).toBeInstanceOf(InputRenderable)
    expect(renderer.root.findDescendantById("page-action-workspace")).toBeInstanceOf(BoxRenderable)

    shell.activateRoute("paper")
    await renderOnce()
    expect(renderer.root.findDescendantById("page-list-paper")).toBeInstanceOf(SelectRenderable)
    expect(renderer.root.findDescendantById("page-action-paper")?.focusable).toBe(true)
    expect(captureCharFrame()).toContain("暂无论文")
    expect(captureCharFrame()).not.toMatch(/study-a|heatmap\.py|openai\s+ready|step 1/)
  } finally {
    renderer.destroy()
  }
})

test("header shows only a safe workspace label and explicit service states", async () => {
  const { renderer, renderOnce, captureCharFrame } = await createTestRenderer({ width: 100, height: 30 })
  try {
    mountShell(renderer, { projectRoot: "C:\\Users\\secret\\Research Alpha" })
    await renderOnce()
    const frame = captureCharFrame()
    expect(frame).toContain("工作区: Research Alpha")
    expect(frame).toContain("LLM: 未连接")
    expect(frame).toContain("服务: 未连接")
    expect(frame).not.toContain("C:\\Users\\secret")
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
    const initialColor = nav.backgroundColor.toString()
    const pointers = []
    const setMousePointer = renderer.setMousePointer.bind(renderer)
    renderer.setMousePointer = (value) => {
      pointers.push(value)
      setMousePointer(value)
    }

    expect(nav?.focusable).toBe(true)
    await mockMouse.moveTo(nav.x + 2, nav.y)
    expect(shell.state.hoveredRoute).toBe("workspace")
    expect(nav.backgroundColor.toString()).not.toBe(initialColor)
    expect(pointers).toContain("pointer")
    await mockMouse.moveTo(50, 20)
    expect(shell.state.hoveredRoute).toBeNull()
    expect(nav.backgroundColor.toString()).toBe(initialColor)
    expect(pointers).toContain("default")
    await mockMouse.moveTo(nav.x + 2, nav.y)
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

test("Enter provides the same navigation activation as the left mouse button", async () => {
  const { renderer, mockInput, renderOnce } = await createTestRenderer({ width: 100, height: 30 })
  try {
    const shell = mountShell(renderer)
    await renderOnce()
    renderer.root.findDescendantById("nav-workspace").focus()
    mockInput.pressEnter()
    await renderOnce()
    expect(shell.state.currentRoute).toBe("workspace")
  } finally {
    renderer.destroy()
  }
})

test("automated modes validate real renderer input paths", async () => {
  const navResult = await runAutomatedMode("automated-nav", { projectRoot: "C:\\safe\\Lab" })
  expect(navResult.route).toBe("dashboard")
  expect(navResult.frame).toContain("状态看板")

  const fullResult = await runAutomatedMode("full-page-interactions", { projectRoot: "C:\\safe\\Lab" })
  expect(fullResult.checkedRoutes).toBe(ROUTES.length)
  expect(fullResult.checkedActions).toBeGreaterThan(0)
})
