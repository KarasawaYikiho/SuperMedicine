import {
  BoxRenderable,
  InputRenderable,
  createCliRenderer,
} from "@opentui/core"
import { createNavigationItem, createPanel, createText } from "./components.ts"
import { createPage } from "./pages.ts"
import { ROUTES, createShellState, findRoute } from "./state.ts"
import { THEME } from "./theme.ts"

function safeWorkspaceLabel(projectRoot) {
  if (!projectRoot) return "未选择"
  const parts = String(projectRoot).replace(/[\u0000-\u001f]/g, "").split(/[\\/]/).filter(Boolean)
  return (parts.at(-1) || "工作区").slice(0, 24)
}

export function mountShell(renderer, options = {}) {
  const state = createShellState()
  state.workspaceName = options.workspaceName || safeWorkspaceLabel(options.projectRoot)
  const root = new BoxRenderable(renderer, {
    id: "supermedicine-root",
    width: "100%",
    height: "100%",
    flexDirection: "column",
    backgroundColor: THEME.background,
  })

  const header = createPanel(renderer, {
    id: "top-bar",
    width: "100%",
    height: 3,
    flexDirection: "row",
    paddingX: 1,
  })
  header.add(createText(renderer, { content: "SuperMedicine", width: "25%", fg: THEME.accent }))
  header.add(createText(renderer, { content: `工作区: ${state.workspaceName}`, width: "30%", fg: THEME.muted }))
  header.add(createText(renderer, { content: `LLM: ${state.llmStatus}`, width: "20%", fg: THEME.muted }))
  header.add(createText(renderer, { content: `服务: ${state.connectionStatus}`, width: "25%", fg: THEME.muted }))
  root.add(header)

  const body = new BoxRenderable(renderer, {
    id: "body",
    width: "100%",
    flexGrow: 1,
    flexDirection: "row",
    backgroundColor: THEME.background,
  })
  root.add(body)

  const sidebar = createPanel(renderer, {
    id: "sidebar",
    width: 22,
    height: "100%",
    flexDirection: "column",
    paddingX: 1,
    title: " 导航 ",
    titleColor: THEME.accent,
  })
  body.add(sidebar)

  const pageColumn = new BoxRenderable(renderer, {
    id: "main-area",
    width: "auto",
    height: "100%",
    flexGrow: 1,
    flexDirection: "column",
    backgroundColor: THEME.background,
  })
  body.add(pageColumn)

  const footer = createPanel(renderer, {
    id: "status-bar",
    width: "100%",
    height: 3,
    paddingX: 1,
  })
  footer.add(createText(renderer, {
    content: "Tab 聚焦  Enter 打开  PageUp/PageDown 滚动  Q 退出",
    fg: THEME.muted,
  }))
  root.add(footer)

  let currentPage = null
  let composer = null
  const navigation = []

  function renderPage(route) {
    if (currentPage) {
      pageColumn.remove(currentPage)
      currentPage.destroyRecursively()
    }
    if (composer) {
      pageColumn.remove(composer)
      composer.destroyRecursively()
      composer = null
    }
    currentPage = createPage(renderer, route)
    pageColumn.add(currentPage)
    if (route.id === "chat") {
      composer = createPanel(renderer, {
        id: "chat-composer",
        width: "100%",
        height: 3,
        paddingX: 1,
        focusedBorderColor: THEME.accent,
      })
      composer.add(new InputRenderable(renderer, {
        id: "prompt-input",
        width: "100%",
        placeholder: "输入科研问题",
        fg: THEME.text,
        backgroundColor: THEME.surface,
      }))
      pageColumn.add(composer)
    }
  }

  function activateRoute(routeId) {
    const route = findRoute(routeId)
    state.currentRoute = route.id
    renderPage(route)
    for (const nav of navigation) nav.update()
    renderer.requestRender()
  }

  for (const route of ROUTES) {
    const nav = createNavigationItem(renderer, route, state, activateRoute)
    navigation.push(nav)
    sidebar.add(nav.item)
  }

  renderer.root.add(root)
  activateRoute("chat")
  renderer.root.findDescendantById("prompt-input")?.focus()
  return { root, state, activateRoute }
}

function assertAutomation(condition, message) {
  if (!condition) throw new Error(`OpenTUI automated verification failed: ${message}`)
}

export async function runAutomatedMode(mode, options = {}) {
  const { createTestRenderer, MouseButtons } = await import("@opentui/core/testing")
  const { renderer, mockInput, mockMouse, renderOnce, captureCharFrame } = await createTestRenderer({
    width: 100,
    height: 30,
    useMouse: true,
    enableMouseMovement: true,
  })
  let checkedRoutes = 0
  let checkedActions = 0
  try {
    const shell = mountShell(renderer, options)
    await renderOnce()

    const workspaceNav = renderer.root.findDescendantById("nav-workspace")
    await mockMouse.moveTo(workspaceNav.x + 2, workspaceNav.y)
    assertAutomation(shell.state.hoveredRoute === "workspace", "mouse hover did not reach workspace navigation")
    await mockMouse.click(workspaceNav.x + 2, workspaceNav.y, MouseButtons.RIGHT)
    assertAutomation(shell.state.currentRoute === "chat", "right click activated navigation")
    await mockMouse.click(workspaceNav.x + 2, workspaceNav.y)
    await renderOnce()
    assertAutomation(shell.state.currentRoute === "workspace" && workspaceNav.focused, "left click did not focus and activate")

    const dashboardNav = renderer.root.findDescendantById("nav-dashboard")
    dashboardNav.focus()
    mockInput.pressEnter()
    await renderOnce()
    assertAutomation(shell.state.currentRoute === "dashboard", "Enter did not match mouse activation")

    if (mode === "full-page-interactions") {
      for (const route of ROUTES) {
        const nav = renderer.root.findDescendantById(`nav-${route.id}`)
        await mockMouse.click(nav.x + 2, nav.y)
        await renderOnce()
        const frame = captureCharFrame()
        assertAutomation(shell.state.currentRoute === route.id, `route ${route.id} did not activate`)
        assertAutomation(renderer.root.findDescendantById(`page-${route.id}`), `route ${route.id} has no page`)
        assertAutomation(frame.includes(route.label), `route ${route.id} frame lacks its label`)
        checkedRoutes += 1
        if (route.id !== "chat") {
          const action = renderer.root.findDescendantById(`page-action-${route.id}`)
          action.focus()
          mockInput.pressEnter()
          await renderOnce()
          const feedback = renderer.root.findDescendantById(`page-feedback-${route.id}`)
          assertAutomation(feedback.chunks.some((chunk) => chunk.text.includes("未执行")), `route ${route.id} action had no honest feedback`)
          checkedActions += 1
        }
      }
    }
    return { route: shell.state.currentRoute, frame: captureCharFrame(), checkedRoutes, checkedActions }
  } finally {
    renderer.destroy()
  }
}

function parseArgs(argv) {
  const parsed = { mode: "interactive", projectRoot: undefined }
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index]
    if (value === "--smoke") parsed.mode = "smoke"
    else if (value === "--automated-nav") parsed.mode = "automated-nav"
    else if (value === "--full-page-interactions") parsed.mode = "full-page-interactions"
    else if (value === "--project-root") parsed.projectRoot = argv[++index]
  }
  return parsed
}

export async function runCli(argv = process.argv.slice(2)) {
  const args = parseArgs(argv)
  if (args.mode === "automated-nav" || args.mode === "full-page-interactions") {
    try {
      const result = await runAutomatedMode(args.mode, { projectRoot: args.projectRoot })
      const signal = args.mode === "automated-nav" ? "NAV" : "FULL_PAGE"
      process.stdout.write(`SUPERMEDICINE_OPENTUI_${signal}_OK route=${result.route}\n`)
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      process.stderr.write(`${message}\n`)
      process.exitCode = 1
    }
    return
  }

  let renderer
  try {
    renderer = await createCliRenderer({
      exitOnCtrlC: true,
      clearOnShutdown: true,
      useMouse: true,
      enableMouseMovement: true,
      targetFps: 30,
      consoleMode: "disabled",
      screenMode: "alternate-screen",
    })
    const shell = mountShell(renderer, { projectRoot: args.projectRoot })
    renderer.keyInput.on("keypress", (event) => {
      const name = String(event.name || "").toLowerCase()
      if (name === "q" && !renderer.currentFocusedEditor) {
        event.preventDefault()
        renderer.destroy()
        return
      }
      const route = ROUTES.find((candidate) => candidate.shortcut.toLowerCase() === name)
      if (route && !renderer.currentFocusedEditor) {
        event.preventDefault()
        shell.activateRoute(route.id)
      }
    })
    renderer.once("destroy", () => {
      if (args.mode === "smoke") process.stdout.write("SUPERMEDICINE_OPENTUI_SMOKE_OK\n")
    })
    renderer.start()
    renderer.requestRender()
    if (args.mode === "smoke") setTimeout(() => renderer.destroy(), 175)
  } catch (error) {
    if (renderer && !renderer.isDestroyed) renderer.destroy()
    const message = error instanceof Error ? error.message : String(error)
    process.stderr.write(`SuperMedicine OpenTUI runtime failed: ${message}\n`)
    process.exitCode = 1
  }
}
