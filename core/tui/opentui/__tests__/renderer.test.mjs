import { expect, test } from "bun:test"
import { BoxRenderable, InputRenderable, MarkdownRenderable, ScrollBoxRenderable, TextRenderable } from "@opentui/core"
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

test("page shells use honest native markdown, form, empty state, and action controls", async () => {
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
    expect(renderer.root.findDescendantById("page-list-paper")).toBeUndefined()
    expect(renderer.root.findDescendantById("page-action-paper")?.focusable).toBe(true)
    const page = renderer.root.findDescendantById("page-paper")
    const focusableIds = []
    const visit = (node) => {
      if (node.focusable) focusableIds.push(node.id)
      for (const child of node.getChildren()) visit(child)
    }
    visit(page)
    expect(focusableIds).toEqual(["page-action-paper"])
    expect(captureCharFrame()).toContain("暂无论文")
    expect(captureCharFrame()).not.toMatch(/study-a|heatmap\.py|openai\s+ready|step 1/)
  } finally {
    renderer.destroy()
  }
})

test("chat page reuses one markdown style lifecycle across repeated route changes", async () => {
  const { renderer, renderOnce } = await createTestRenderer({ width: 100, height: 30 })
  const warnings = []
  const onWarning = (warning) => warnings.push(warning)
  process.on("warning", onWarning)
  try {
    const shell = mountShell(renderer)
    await renderOnce()
    const destroyListeners = renderer.listenerCount("destroy")
    for (let index = 0; index < 30; index += 1) {
      shell.activateRoute("workspace")
      shell.activateRoute("chat")
      await renderOnce()
      expect(renderer.listenerCount("destroy")).toBe(destroyListeners)
    }
    expect(warnings.filter((warning) => warning.name === "MaxListenersExceededWarning")).toHaveLength(0)
  } finally {
    process.off("warning", onWarning)
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
    expect(renderer.currentFocusedRenderable?.id).toBe("page-field-workspace")
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
  expect(fullResult.checkedLayouts).toBe(4)
})

test("responsive breakpoints resize the native shell without clipped chrome", async () => {
  for (const [width, height, sidebarWidth] of [[60, 20, 0], [80, 24, 20], [120, 30, 26], [160, 45, 26]]) {
    const setup = await createTestRenderer({ width, height, useMouse: true, enableMouseMovement: true })
    const { renderer, renderOnce, captureCharFrame } = setup
    try {
      mountShell(renderer)
      await renderOnce()
      const sidebar = renderer.root.findDescendantById("sidebar")
      const main = renderer.root.findDescendantById("main-area")
      const header = renderer.root.findDescendantById("top-bar")
      const footer = renderer.root.findDescendantById("status-bar")
      expect(sidebar.visible ? sidebar.width : 0).toBe(sidebarWidth)
      expect(main.width).toBe(width - sidebarWidth)
      expect(header.height).toBe(height < 24 ? 1 : 3)
      expect(footer.height).toBe(height < 24 ? 1 : 3)
      expect(main.x).toBe(sidebar.visible ? sidebar.x + sidebar.width : 0)
      expect(main.x + main.width).toBeLessThanOrEqual(width)
      expect(main.y + main.height).toBeLessThanOrEqual(height - footer.height)
      const rows = captureCharFrame().split("\n").slice(0, height)
      expect(rows.length).toBe(height)
      expect(rows.every((row) => [...row].length <= width)).toBe(true)
    } finally {
      renderer.destroy()
    }
  }
})

test("narrow menu is an escape-closed overlay and keeps the page full width", async () => {
  const { renderer, mockInput, renderOnce } = await createTestRenderer({ width: 60, height: 20 })
  try {
    const shell = mountShell(renderer)
    await renderOnce()
    expect(renderer.root.findDescendantById("sidebar").visible).toBe(false)
    expect(renderer.root.findDescendantById("main-area").width).toBe(60)
    shell.activateRoute("dashboard")
    mockInput.pressKey("m")
    await renderOnce()
    expect(shell.state.menuOpen).toBe(true)
    expect(renderer.root.findDescendantById("sidebar").visible).toBe(true)
    expect(renderer.root.findDescendantById("main-area").width).toBe(60)
    await mockInput.pressKeys(["ESCAPE"], 75)
    await renderOnce()
    expect(shell.state.menuOpen).toBe(false)
    expect(shell.state.currentRoute).toBe("dashboard")
  } finally {
    renderer.destroy()
  }
})

test("real wheel and PageDown scroll only the active long page without routing", async () => {
  const records = Array.from({ length: 40 }, (_, index) => `真实测试记录 ${String(index + 1).padStart(2, "0")}`)
  const { renderer, mockMouse, mockInput, renderOnce, captureCharFrame } = await createTestRenderer({ width: 80, height: 24 })
  try {
    const shell = mountShell(renderer, { pageFixtures: { paper: records } })
    shell.activateRoute("paper")
    await renderOnce()
    const page = renderer.root.findDescendantById("page-paper")
    const sidebar = renderer.root.findDescendantById("sidebar")
    const before = captureCharFrame()
    await mockMouse.scroll(page.x + 4, page.y + 4, "down")
    await renderOnce()
    expect(page.scrollTop).toBeGreaterThan(0)
    expect(shell.state.currentRoute).toBe("paper")
    expect(sidebar.y).toBe(3)
    expect(captureCharFrame()).not.toBe(before)
    const wheelTop = page.scrollTop
    mockInput.pressKey("\x1b[6~")
    await renderOnce()
    expect(page.scrollTop).toBeGreaterThan(wheelTop)
    mockInput.pressKey("\x1b[5~")
    await renderOnce()
    expect(page.scrollTop).toBeLessThan(wheelTop + page.viewport.height)
  } finally {
    renderer.destroy()
  }
})

test("route focus, Tab order, clicks, right click, and editor input follow the current page", async () => {
  const { renderer, mockMouse, mockInput, renderOnce } = await createTestRenderer({ width: 100, height: 30 })
  try {
    const shell = mountShell(renderer, { pageFixtures: { workspace: ["真实工作区 A", "真实工作区 B"] } })
    shell.activateRoute("workspace")
    await renderOnce()
    expect(renderer.currentFocusedRenderable?.id).toBe("page-field-workspace")
    mockInput.pressTab()
    expect(renderer.currentFocusedRenderable?.id).toBe("page-record-workspace-0")
    mockInput.pressTab()
    expect(renderer.currentFocusedRenderable?.id).toBe("page-record-workspace-1")
    mockInput.pressTab({ shift: true })
    expect(renderer.currentFocusedRenderable?.id).toBe("page-record-workspace-0")

    const button = renderer.root.findDescendantById("page-action-workspace")
    await mockMouse.click(button.x + 2, button.y + 1)
    expect(renderer.currentFocusedRenderable?.id).toBe("page-action-workspace")
    const feedback = renderer.root.findDescendantById("page-feedback-workspace").content
    const routeBeforeRightClick = shell.state.currentRoute
    await mockMouse.click(button.x + 2, button.y + 1, MouseButtons.RIGHT)
    expect(shell.state.currentRoute).toBe(routeBeforeRightClick)
    expect(renderer.root.findDescendantById("page-feedback-workspace").content).toBe(feedback)

    const record = renderer.root.findDescendantById("page-record-workspace-1")
    await mockMouse.click(record.x + 2, record.y)
    expect(renderer.currentFocusedRenderable?.id).toBe("page-record-workspace-1")

    const field = renderer.root.findDescendantById("page-field-workspace")
    await mockMouse.click(field.x + 2, field.y)
    await mockInput.typeText("中文123")
    await mockInput.pasteBracketedText("粘贴456")
    await renderOnce()
    expect(field.value).toContain("中文123粘贴456")
    expect(shell.state.currentRoute).toBe("workspace")
  } finally {
    renderer.destroy()
  }
})

test("destroy removes shell listeners and leaves no renderer work", async () => {
  const { renderer, renderOnce } = await createTestRenderer({ width: 80, height: 24 })
  mountShell(renderer)
  await renderOnce()
  expect(renderer.listenerCount("resize")).toBeGreaterThan(0)
  renderer.destroy()
  expect(renderer.isDestroyed).toBe(true)
  expect(renderer.listenerCount("resize")).toBe(0)
  expect(renderer.liveRequestCount).toBe(0)
})

test("all thirteen routes change route and captured frame through mockMouse.click", async () => {
  const { renderer, mockMouse, renderOnce, captureCharFrame } = await createTestRenderer({ width: 120, height: 30 })
  try {
    const shell = mountShell(renderer)
    await renderOnce()
    let previous = captureCharFrame()
    for (const route of ROUTES) {
      const nav = renderer.root.findDescendantById(`nav-${route.id}`)
      await mockMouse.click(nav.x + 2, nav.y)
      await renderOnce()
      const frame = captureCharFrame()
      expect(shell.state.currentRoute).toBe(route.id)
      expect(frame).toContain(route.label)
      if (route.id !== "chat") expect(frame).not.toBe(previous)
      previous = frame
    }
  } finally {
    renderer.destroy()
  }
})
