import {
  BoxRenderable,
  InputRenderable,
  SyntaxStyle,
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
  const markdownSyntaxStyle = SyntaxStyle.fromStyles({
    default: { fg: THEME.text },
    "markup.heading": { fg: THEME.accent, bold: true },
  })
  renderer.once("destroy", () => markdownSyntaxStyle.destroy())
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
    currentPage = createPage(renderer, route, {
      markdownSyntaxStyle,
      pageFixtures: options.pageFixtures,
    })
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
    focusFirstPageControl()
    if (state.menuOpen) closeMenu()
  }

  function pageControls() {
    const controls = []
    const visit = (node) => {
      if (node.focusable && node.visible) controls.push(node)
      for (const child of node.getChildren()) visit(child)
    }
    if (currentPage) visit(currentPage)
    if (composer) visit(composer)
    return controls
  }

  function focusFirstPageControl() {
    focusPageControl(pageControls()[0])
  }

  function focusPageControl(control) {
    if (!control) return
    control.focus()
    let ancestor = control
    while (ancestor && ancestor !== currentPage) ancestor = ancestor.parent
    if (ancestor === currentPage) currentPage.scrollChildIntoView(control.id)
    renderer.requestRender()
  }

  function applyLayout(width = renderer.terminalWidth, height = renderer.terminalHeight) {
    const narrow = width < 80
    const compressed = height < 24
    header.border = !compressed
    footer.border = !compressed
    header.height = compressed ? 1 : 3
    footer.height = compressed ? 1 : 3
    sidebar.width = width >= 120 ? 26 : 20
    sidebar.position = narrow ? "absolute" : "relative"
    sidebar.left = 0
    sidebar.top = 0
    sidebar.zIndex = narrow ? 10 : 0
    sidebar.visible = narrow ? state.menuOpen : true
    pageColumn.width = narrow ? "100%" : "auto"
    pageColumn.flexGrow = 1
    renderer.requestRender()
  }

  function openMenu() {
    if (renderer.terminalWidth >= 80) return
    state.menuOpen = true
    applyLayout()
    navigation[0]?.item.focus()
  }

  function closeMenu() {
    if (!state.menuOpen) return
    state.menuOpen = false
    applyLayout()
    focusFirstPageControl()
  }

  function handleShellKey(event) {
    const name = String(event.name || "").toLowerCase()
    if (name === "escape" && state.menuOpen) {
      event.preventDefault()
      closeMenu()
      return
    }
    if (name === "m" && !renderer.currentFocusedEditor && renderer.terminalWidth < 80) {
      event.preventDefault()
      state.menuOpen ? closeMenu() : openMenu()
      return
    }
    if ((name === "pageup" || name === "pagedown") && !renderer.currentFocusedEditor) {
      event.preventDefault()
      currentPage?.scrollBy(name === "pageup" ? -0.5 : 0.5, "viewport")
      return
    }
    if (name !== "tab") return
    const controls = state.menuOpen ? navigation.map((nav) => nav.item) : pageControls()
    if (controls.length === 0) return
    event.preventDefault()
    const currentIndex = controls.indexOf(renderer.currentFocusedRenderable)
    const step = event.shift ? -1 : 1
    const targetIndex = currentIndex < 0
      ? (event.shift ? controls.length - 1 : 0)
      : (currentIndex + step + controls.length) % controls.length
    focusPageControl(controls[targetIndex])
  }

  for (const route of ROUTES) {
    const nav = createNavigationItem(renderer, route, state, activateRoute)
    navigation.push(nav)
    sidebar.add(nav.item)
  }

  renderer.root.add(root)
  renderer.on("resize", applyLayout)
  renderer.keyInput.on("keypress", handleShellKey)
  renderer.once("destroy", () => {
    renderer.off("resize", applyLayout)
    renderer.keyInput.off("keypress", handleShellKey)
  })
  applyLayout()
  activateRoute("chat")
  return { root, state, activateRoute, openMenu, closeMenu }
}

function assertAutomation(condition, message) {
  if (!condition) throw new Error(`OpenTUI automated verification failed: ${message}`)
}

export async function runAutomatedMode(mode, options = {}) {
  const { createTestRenderer, MouseButtons } = await import("@opentui/core/testing")
  const { renderer, mockInput, mockMouse, renderOnce, captureCharFrame, resize } = await createTestRenderer({
    width: 100,
    height: 30,
    useMouse: true,
    enableMouseMovement: true,
  })
  let checkedRoutes = 0
  let checkedActions = 0
  let checkedLayouts = 0
  try {
    const shell = mountShell(renderer, mode === "full-page-interactions" ? {
      ...options,
      pageFixtures: {
        ...options.pageFixtures,
        paper: Array.from({ length: 40 }, (_, index) => `交互验证记录 ${index + 1}`),
        workspace: Array.from({ length: 40 }, (_, index) => `焦点验证记录 ${index + 1}`),
      },
    } : options)
    await renderOnce()

    const workspaceNav = renderer.root.findDescendantById("nav-workspace")
    await mockMouse.moveTo(workspaceNav.x + 2, workspaceNav.y)
    assertAutomation(shell.state.hoveredRoute === "workspace", "mouse hover did not reach workspace navigation")
    await mockMouse.click(workspaceNav.x + 2, workspaceNav.y, MouseButtons.RIGHT)
    assertAutomation(shell.state.currentRoute === "chat", "right click activated navigation")
    await mockMouse.click(workspaceNav.x + 2, workspaceNav.y)
    await renderOnce()
    assertAutomation(shell.state.currentRoute === "workspace" && renderer.currentFocusedRenderable?.id === "page-field-workspace", "left click did not activate and focus the page")

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

      shell.activateRoute("paper")
      await renderOnce()
      const paperPage = renderer.root.findDescendantById("page-paper")
      const paperSidebar = renderer.root.findDescendantById("sidebar")
      const paperNav = renderer.root.findDescendantById("nav-paper")
      const sidebarSnapshot = { y: paperSidebar.y, navY: paperNav.y }
      const routeBeforeScroll = shell.state.currentRoute
      await mockMouse.scroll(paperPage.x + 3, paperPage.y + 3, "down")
      await renderOnce()
      assertAutomation(paperPage.scrollTop > 0, "mouse wheel did not scroll the pointed page")
      assertAutomation(shell.state.currentRoute === routeBeforeScroll, "mouse wheel changed route")
      assertAutomation(paperSidebar.y === sidebarSnapshot.y && paperNav.y === sidebarSnapshot.navY, "main wheel moved the sidebar")
      const wheelTop = paperPage.scrollTop
      await mockMouse.scroll(paperSidebar.x + 3, paperSidebar.y + 4, "down")
      await renderOnce()
      assertAutomation(paperPage.scrollTop === wheelTop, "sidebar wheel changed the main page scroll")
      assertAutomation(paperSidebar.y === sidebarSnapshot.y && paperNav.y === sidebarSnapshot.navY && shell.state.currentRoute === routeBeforeScroll, "sidebar wheel changed shell state")
      mockInput.pressKey("\x1b[6~")
      await renderOnce()
      assertAutomation(paperPage.scrollTop > wheelTop, "PageDown did not scroll the current page")

      shell.activateRoute("workspace")
      await renderOnce()
      const field = renderer.root.findDescendantById("page-field-workspace")
      await mockMouse.click(field.x + 2, field.y)
      await mockInput.typeText("中文123")
      await mockInput.pasteBracketedText("粘贴456")
      await renderOnce()
      assertAutomation(field.value.includes("中文123粘贴456"), "editor lost typed or pasted text")
      assertAutomation(shell.state.currentRoute === "workspace", "editor input triggered a route")

      const workspacePage = renderer.root.findDescendantById("page-workspace")
      for (let index = 0; index < 28; index += 1) {
        mockInput.pressTab()
        await renderOnce()
        const focused = renderer.currentFocusedRenderable
        assertAutomation(focused.y >= workspacePage.viewport.y && focused.y + focused.height <= workspacePage.viewport.y + workspacePage.viewport.height, `Tab focus ${focused.id} left the viewport`)
      }
      const forwardScrollTop = workspacePage.scrollTop
      assertAutomation(forwardScrollTop > 0, "long Tab traversal did not scroll")
      for (let index = 0; index < 20; index += 1) {
        mockInput.pressTab({ shift: true })
        await renderOnce()
        const focused = renderer.currentFocusedRenderable
        assertAutomation(focused.y >= workspacePage.viewport.y && focused.y + focused.height <= workspacePage.viewport.y + workspacePage.viewport.height, `ShiftTab focus ${focused.id} left the viewport`)
      }
      assertAutomation(workspacePage.scrollTop < forwardScrollTop, "long ShiftTab traversal did not reverse scroll")

      for (const [width, height, expectedSidebar] of [[60, 20, 0], [80, 24, 20], [120, 30, 26], [160, 45, 26]]) {
        resize(width, height)
        shell.activateRoute("dashboard")
        await renderOnce()
        const sidebar = renderer.root.findDescendantById("sidebar")
        const main = renderer.root.findDescendantById("main-area")
        const header = renderer.root.findDescendantById("top-bar")
        const footer = renderer.root.findDescendantById("status-bar")
        const frame = captureCharFrame()
        const rows = frame.split("\n").slice(0, height)
        const focused = renderer.currentFocusedRenderable
        assertAutomation((sidebar.visible ? sidebar.width : 0) === expectedSidebar, `${width}x${height} sidebar breakpoint failed`)
        assertAutomation(header.y === 0 && main.y === header.height && main.y + main.height === footer.y && footer.y + footer.height === height, `${width}x${height} chrome overlapped`)
        assertAutomation(main.x + main.width <= width && main.y + main.height <= height && focused.y >= main.y && focused.y + focused.height <= footer.y, `${width}x${height} layout or focus overflowed`)
        assertAutomation(rows.every((row) => [...row].length <= width) && frame.includes("SuperMedicine") && frame.includes("状态看板") && frame.includes("刷新状态"), `${width}x${height} frame clipped key content`)
        if (height >= 24) {
          assertAutomation(/^┌─+┐$/.test(rows[0]) && /^└─+┘$/.test(rows[header.height - 1]) && /^┌─+┐$/.test(rows[footer.y]) && /^└─+┘$/.test(rows[height - 1]), `${width}x${height} chrome border incomplete`)
          assertAutomation(/^┌─.*┐/.test(rows[main.y]) && /^└─+┘/.test(rows[footer.y - 1]), `${width}x${height} sidebar border incomplete`)
        } else {
          assertAutomation(!/[┌┐└┘]/.test(rows[0]) && !/[┌┐└┘]/.test(rows[height - 1]), `${width}x${height} compact chrome left half borders`)
        }
        checkedLayouts += 1
      }

      resize(60, 20)
      await renderOnce()
      shell.activateRoute("dashboard")
      mockInput.pressKey("m")
      await renderOnce()
      assertAutomation(shell.state.menuOpen, "M did not open the narrow overlay menu")
      await mockInput.pressKeys(["ESCAPE"], 75)
      await renderOnce()
      assertAutomation(!shell.state.menuOpen && shell.state.currentRoute === "dashboard", "Esc did not only close the top menu")
    }
    return { route: shell.state.currentRoute, frame: captureCharFrame(), checkedRoutes, checkedActions, checkedLayouts }
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
