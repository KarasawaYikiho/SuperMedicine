import {
  BoxRenderable,
  CliRenderEvents,
  InputRenderable,
  createCliRenderer,
} from "@opentui/core"
import { createNavigationItem, createPanel, createText } from "./components.ts"
import { createPage } from "./pages.ts"
import { ROUTES, createShellState, findRoute } from "./state.ts"
import { THEME } from "./theme.ts"

export function mountShell(renderer, options = {}) {
  const state = createShellState()
  state.workspaceName = options.workspaceName || state.workspaceName
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
  const appName = createText(renderer, { content: "SuperMedicine", width: "34%", fg: THEME.accent })
  const workspace = createText(renderer, { content: state.workspaceName, width: "33%", fg: THEME.muted })
  const connection = createText(renderer, { content: state.connectionStatus, width: "33%", fg: THEME.muted })
  header.add(appName)
  header.add(workspace)
  header.add(connection)
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
      const input = new InputRenderable(renderer, {
        id: "prompt-input",
        width: "100%",
        placeholder: "输入科研问题",
        fg: THEME.text,
        backgroundColor: THEME.surface,
      })
      composer.add(input)
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

function parseMode(argv) {
  if (argv.includes("--smoke")) return "smoke"
  if (argv.includes("--automated-nav")) return "automated-nav"
  if (argv.includes("--full-page-interactions")) return "full-page-interactions"
  return "interactive"
}

function runAutomation(renderer, shell, mode) {
  if (mode === "interactive") return
  const routeIds = mode === "full-page-interactions" ? ROUTES.map((route) => route.id) : ["workspace", "dashboard"]
  routeIds.forEach((routeId, index) => {
    setTimeout(() => shell.activateRoute(routeId), 35 * (index + 1))
  })
  setTimeout(() => renderer.destroy(), 35 * (routeIds.length + 2))
}

export async function runCli(argv = process.argv.slice(2)) {
  const mode = parseMode(argv)
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
    const shell = mountShell(renderer)
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
    renderer.on(CliRenderEvents.DESTROY, () => {
      if (mode !== "interactive") process.stdout.write(`SUPERMEDICINE_OPENTUI_${mode.toUpperCase().replaceAll("-", "_")}_OK\n`)
    })
    renderer.start()
    renderer.requestRender()
    runAutomation(renderer, shell, mode)
  } catch (error) {
    if (renderer && !renderer.isDestroyed) renderer.destroy()
    const message = error instanceof Error ? error.message : String(error)
    process.stderr.write(`SuperMedicine OpenTUI runtime failed: ${message}\n`)
    process.exitCode = 1
  }
}
