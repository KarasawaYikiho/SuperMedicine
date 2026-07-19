#!/usr/bin/env node
/**
 * SuperMedicine OpenTUI runtime bridge.
 *
 * This file is intentionally small and owns only the runtime shell: OpenTUI
 * initialization, render loop start, keyboard routing, layout mounting and
 * cleanup.  Python remains the product entrypoint, but the interactive TUI
 * main path now delegates to the real @opentui/core runtime instead of the
 * previous Textual runtime.  The page catalogue below is intentionally kept in
 * this OpenTUI bridge so the primary route, focus, selection, filtering and
 * status interactions are all handled by real @opentui/core renderables.  Python
 * modules remain the business-service layer and dry-run/compatibility surface.
 */

import {
  BoxRenderable,
  CliRenderEvents,
  InputRenderable,
  TextRenderable,
  createCliRenderer,
} from "@opentui/core"

const THEME = {
  background: "#0B0F14",
  panel: "#111827",
  panelAlt: "#0F172A",
  border: "#374151",
  text: "#E5E7EB",
  muted: "#9CA3AF",
  accent: "#A7F3D0",
  warning: "#FDE68A",
}

function parseArgs(argv) {
  const args = { mode: "interactive", projectRoot: process.cwd(), pythonExecutable: "python", smokeMs: 350 }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === "--smoke") {
      args.mode = "smoke"
    } else if (arg === "--automated-nav") {
      args.mode = "automated-nav"
    } else if (arg === "--full-page-interactions") {
      args.mode = "full-page-interactions"
    } else if (arg === "--interaction-matrix") {
      args.mode = "interaction-matrix"
    } else if (arg === "--project-root") {
      args.projectRoot = argv[++i] || process.cwd()
    } else if (arg === "--python-executable") {
      args.pythonExecutable = argv[++i] || "python"
    } else if (arg === "--smoke-ms") {
      args.smokeMs = Number(argv[++i] || args.smokeMs)
    }
  }
  return args
}

function serviceBridge(options, request) {
  const result = Bun.spawnSync({
    cmd: [
      options.pythonExecutable,
      "-m",
      "core.tui.service_bridge",
      "--jsonl",
      options.projectRoot,
    ],
    cwd: options.projectRoot,
    stdin: new TextEncoder().encode(`${JSON.stringify(request)}\n`),
    stdout: "pipe",
    stderr: "pipe",
  })
  const stdout = new TextDecoder().decode(result.stdout || new Uint8Array()).trim()
  if (result.exitCode !== 0 || !stdout) {
    return { ok: false, data: null }
  }
  try {
    return JSON.parse(stdout)
  } catch {
    return { ok: false, data: null }
  }
}

function multiAgentBridge(options, action) {
  return serviceBridge(options, { operation: "multi-agent", action })
}

function hydratePageCatalog(options) {
  const snapshot = serviceBridge(options, { operation: "catalog" })
  if (!snapshot.ok || !snapshot.data?.pages) {
    const diagnostic = JSON.stringify(snapshot.error || { code: "bridge_unavailable" })
    ALL_ROUTES.forEach((route) => { route.records = [`Service diagnostic: ${diagnostic}`] })
    return {}
  }
  for (const route of ALL_ROUTES) {
    const records = snapshot.data.pages[route.id] || []
    route.rawRecords = records
    route.records = records.map((record) => typeof record === "string" ? record : JSON.stringify(record))
  }
  return snapshot.data.runtime_state || {}
}

function addText(renderer, parent, id, content, layout = {}) {
  const text = new TextRenderable(renderer, {
    id,
    content,
    fg: layout.fg || THEME.text,
    width: layout.width || "100%",
    height: layout.height || 1,
    ...layout,
  })
  parent.add(text)
  return text
}

const PAGE_CATALOG = {
  chat: {
    key: "1",
    title: "对话",
    icon: "💬",
    intent: "OpenTUI scrollback + split-footer prompt; Python Kernel/service layer remains the execution boundary.",
    sections: ["Conversation Scrollback", "Prompt Footer", "Processing / Thinking Status"],
    records: [],
    actions: ["Enter 提交 prompt", "/ 聚焦页面过滤", "[ ] 滚动 scrollback"],
  },
  dashboard: {
    key: "2",
    title: "状态看板",
    icon: "📊",
    intent: "TextTable-style runtime board for workspace/plugin/LLM/token status.",
    sections: ["Runtime Health", "Workspace Metrics", "LLM / Token Summary"],
    records: [],
    actions: ["r 刷新 metrics", "Enter 打开当前指标", "Tab 切换焦点"],
  },
  workspace: {
    key: "3",
    title: "工作区",
    icon: "📁",
    intent: "OpenTUI selectable workspace list with bordered create/select/delete forms.",
    sections: ["Workspace Select", "Create Workspace", "Danger Zone"],
    records: [],
    actions: ["j/k 选择工作区", "Enter 选择", "Ctrl+N 聚焦创建输入"],
  },
  paper: {
    key: "4",
    title: "论文 / RAG",
    icon: "📄",
    intent: "OpenTUI import/list/enrich panels with permission-aware online enrichment.",
    sections: ["Import Form", "Paper List", "Online Enrichment"],
    records: [],
    actions: ["Enter 导入/选择", "r 刷新论文", "/ 过滤标题"],
  },
  experience: {
    key: "5",
    title: "经验",
    icon: "💡",
    intent: "OpenTUI experience capture, suggestion and export workflow.",
    sections: ["Suggest", "Records", "Export"],
    records: [],
    actions: ["Enter 确认写入", "e 导出", "/ 过滤标签"],
  },
  tool: {
    key: "6",
    title: "工具",
    icon: "🔧",
    intent: "OpenTUI multi-panel tool scan/add/run workflow; permissions stay in Python service layer.",
    sections: ["Tool Registry", "Scan Candidates", "Sandbox Run"],
    records: [],
    actions: ["s 扫描", "a 添加", "Enter 运行选中工具"],
  },
  dialog: {
    key: "7",
    title: "对话历史",
    icon: "📋",
    intent: "OpenTUI audit timeline; raw conversation fields remain rejected by Python store.",
    sections: ["Timeline", "Session Filter", "Privacy Guard"],
    records: [],
    actions: ["/ 过滤 session", "Enter 查看摘要", "[ ] 滚动时间线"],
  },
  llm: {
    key: "8",
    title: "LLM 配置",
    icon: "🤖",
    intent: "OpenTUI settings panel for provider CRUD with hidden API Key display.",
    sections: ["Provider List", "Provider Form", "Validation"],
    records: [],
    actions: ["Enter 切换 Provider", "d 删除", "Ctrl+S 保存"],
  },
  experiment: {
    key: "9",
    title: "实验",
    icon: "🧪",
    intent: "OpenTUI protocol stepper with JSON/key=value data input and calculation boundary.",
    sections: ["Protocol", "Step Data", "Reagent Calculation"],
    records: [],
    actions: ["Enter 保存步骤", "c 计算", "l 保存日志"],
  },
  log: {
    key: "0",
    title: "Log 报告",
    icon: "📝",
    intent: "OpenTUI log viewer/writer with redacted report details and list filtering.",
    sections: ["Report Writer", "Report List", "Detail Viewer"],
    records: [],
    actions: ["Enter 保存/查看", "r 刷新", "/ 过滤报告"],
  },
  permission: {
    key: "p",
    title: "权限",
    icon: "🛡️",
    intent: "OpenTUI security panel for conservative/full access mode and root policy visibility.",
    sections: ["Access Mode", "Root Policy", "Confirmations"],
    records: [],
    actions: ["Enter 查看策略", "f 完全访问确认", "a 切换 Multi-Agent", "Esc 返回"],
  },
  "self-evolution": {
    key: "e",
    title: "自进化",
    icon: "🧬",
    intent: "OpenTUI utility panel for preview/write audit without approval claims.",
    sections: ["Preview", "Audit", "Write Boundary"],
    records: [],
    actions: ["p 预览", "w 写入", "Esc 返回"],
  },
  diagnose: {
    key: "d",
    title: "诊断",
    icon: "🩺",
    intent: "OpenTUI diagnostics panel for runtime/config/service checks.",
    sections: ["Runtime", "Config", "Services"],
    records: [],
    actions: ["r 重新诊断", "Enter 查看详情", "Esc 返回"],
  },
}

const ROUTES = ["chat", "dashboard", "workspace", "paper", "experience", "tool", "dialog", "llm", "experiment", "log"].map((id) => ({
  id,
  ...PAGE_CATALOG[id],
}))

const UTILITY_ROUTES = ["permission", "self-evolution", "diagnose"].map((id) => ({ id, ...PAGE_CATALOG[id] }))
const ALL_ROUTES = [...ROUTES, ...UTILITY_ROUTES]

function routeById(routeId) {
  return ALL_ROUTES.find((route) => route.id === routeId) || ROUTES[0]
}

function routeIndex(routeId) {
  return Math.max(0, ROUTES.findIndex((route) => route.id === routeId))
}

function renderPageLines(route, state) {
  const selectedRecord = route.records[state.selection % route.records.length]
  const filterText = state.filter ? `filter=/${state.filter}/` : "filter=<none>"
  return [
    `${route.intent}`,
    "",
    `Sections: ${route.sections.join("  │  ")}`,
    `Selected: ${selectedRecord}`,
    `Records: ${route.records.map((record, index) => `${index === state.selection ? "▶" : " "}${record}`).join("  ·  ")}`,
    `Actions: ${route.actions.join("  ·  ")}`,
    `Interaction state: ${filterText}; pageOffset=${state.pageOffset}; lastAction=${state.lastAction || "<none>"}`,
  ].join("\n")
}

function parsedKey(name, options = {}) {
  return {
    name,
    ctrl: false,
    meta: false,
    shift: false,
    option: false,
    sequence: name,
    number: false,
    raw: name,
    eventType: "press",
    source: "automated",
    ...options,
  }
}

function mountShell(renderer, options) {
  const runtimeState = hydratePageCatalog(options)
  const initialMultiAgent = multiAgentBridge(options, "status")
  let multiAgentEnabled = Boolean(initialMultiAgent.ok && initialMultiAgent.data?.enabled)
  PAGE_CATALOG.permission.records.unshift(`multi-agent     ${multiAgentEnabled ? "enabled" : "disabled"}`)
  const initialRoute = ALL_ROUTES.some((route) => route.id === runtimeState.current_view)
    ? runtimeState.current_view
    : "chat"
  const state = {
    currentRoute: initialRoute,
    stack: [initialRoute],
    focus: "input",
    menuOpen: false,
    navIndex: routeIndex(initialRoute),
    lastInput: "",
    filter: "",
    selection: 0,
    pageOffset: 0,
    lastAction: "",
  }

  const root = new BoxRenderable(renderer, {
    id: "supermedicine-root",
    width: "100%",
    height: "100%",
    flexDirection: "column",
    backgroundColor: THEME.background,
    border: false,
  })

  const topNav = new BoxRenderable(renderer, {
    id: "top-navigation",
    width: "100%",
    height: 3,
    flexDirection: "row",
    paddingX: 1,
    border: true,
    borderColor: THEME.border,
    backgroundColor: THEME.panel,
    title: " OpenTUI Navigation ",
    titleColor: THEME.accent,
  })
  root.add(topNav)
  const topLeft = addText(renderer, topNav, "top-nav-left", "", { width: "55%", fg: THEME.accent })
  const topRight = addText(renderer, topNav, "top-nav-right", "", { width: "45%", fg: THEME.muted })

  const body = new BoxRenderable(renderer, {
    id: "app-body",
    width: "100%",
    flexGrow: 1,
    flexDirection: "row",
    backgroundColor: THEME.background,
    border: false,
  })
  root.add(body)

  const sidebar = new BoxRenderable(renderer, {
    id: "sidebar",
    width: 28,
    height: "100%",
    flexDirection: "column",
    padding: 1,
    border: true,
    borderColor: THEME.border,
    backgroundColor: THEME.panel,
    title: " SuperMedicine ",
    titleColor: THEME.accent,
  })
  body.add(sidebar)

  const menuHint = addText(renderer, sidebar, "menu-hint", "", { fg: THEME.accent })
  const navText = new Map()
  for (const route of ROUTES) {
    navText.set(route.id, addText(renderer, sidebar, `nav-${route.id}`, ""))
  }

  const main = new BoxRenderable(renderer, {
    id: "main-area",
    width: "auto",
    height: "100%",
    flexGrow: 1,
    flexDirection: "column",
    padding: 1,
    border: true,
    borderColor: THEME.border,
    backgroundColor: THEME.panelAlt,
    title: " OpenTUI Runtime ",
    titleColor: THEME.accent,
  })
  body.add(main)

  const viewTitle = addText(renderer, main, "view-title", "", { fg: THEME.accent })
  addText(
    renderer,
    main,
    "runtime-banner",
    "真实 @opentui/core runtime 已加载；当前步骤提供统一导航框架与最小 route shell。",
    { fg: THEME.text, height: 2 },
  )
  addText(renderer, main, "project-root", `Project: ${options.projectRoot}`, {
    fg: THEME.muted,
    height: 1,
  })
  const routeContent = addText(renderer, main, "route-content", "", {
    fg: THEME.text,
    height: 8,
  })
  const log = addText(renderer, main, "event-log", "", {
    fg: THEME.warning,
    height: 3,
    flexGrow: 1,
  })
  const input = new InputRenderable(renderer, {
    id: "prompt-input",
    width: "100%",
    placeholder: "输入任务或命令…",
    border: true,
    borderColor: THEME.border,
    focusedBorderColor: THEME.accent,
    fg: THEME.text,
    backgroundColor: THEME.background,
  })
  main.add(input)

  const status = new BoxRenderable(renderer, {
    id: "status-bar",
    width: "100%",
    height: 3,
    paddingX: 1,
    flexDirection: "row",
    border: true,
    borderColor: THEME.border,
    backgroundColor: THEME.panel,
  })
  root.add(status)
  const statusLeft = addText(renderer, status, "status-left", "", { width: "33%", fg: THEME.accent })
  const statusCenter = addText(renderer, status, "status-center", "", { width: "33%" })
  const statusRight = addText(renderer, status, "status-right", "", { width: "34%" })

  sidebar.onMouseScroll = (event) => {
    moveNav(event.scroll?.direction === "up" ? -1 : 1)
    event.preventDefault()
  }
  main.onMouseScroll = (event) => {
    const records = routeById(state.currentRoute).records
    const count = Math.max(1, records.length)
    const delta = event.scroll?.direction === "up" ? -1 : 1
    state.selection = (state.selection + delta + count) % count
    state.lastAction = delta > 0 ? "鼠标向下滚动" : "鼠标向上滚动"
    renderNavigation()
    event.preventDefault()
  }

  function focusLabel() {
    if (state.focus === "nav") return "导航列表"
    if (state.focus === "content") return "内容区"
    return "输入框"
  }

  function setFocus(nextFocus) {
    state.focus = nextFocus
    if (nextFocus === "input") {
      input.focus()
    } else if (typeof input.blur === "function") {
      input.blur()
    }
    renderNavigation()
  }

  function switchRoute(routeId, { push = true } = {}) {
    const route = routeById(routeId)
    if (push && state.currentRoute !== route.id) {
      state.stack.push(route.id)
    }
    state.currentRoute = route.id
    serviceBridge(options, { operation: "state", action: "set", key: "current_view", value: route.id })
    state.navIndex = routeIndex(route.id)
    state.selection = 0
    state.pageOffset = 0
    state.filter = ""
    state.lastAction = `打开 ${route.title}`
    state.menuOpen = false
    renderNavigation()
  }

  function goBack() {
    if (state.menuOpen) {
      state.menuOpen = false
      renderNavigation()
      return
    }
    if (state.stack.length > 1) {
      state.stack.pop()
      state.currentRoute = state.stack[state.stack.length - 1]
      state.navIndex = routeIndex(state.currentRoute)
      renderNavigation()
    }
  }

  function moveNav(delta) {
    state.navIndex = (state.navIndex + delta + ROUTES.length) % ROUTES.length
    setFocus("nav")
  }

  function toggleMultiAgent() {
    const action = multiAgentEnabled ? "disable" : "enable"
    const result = multiAgentBridge(options, action)
    if (result.ok) {
      multiAgentEnabled = Boolean(result.data?.enabled)
      PAGE_CATALOG.permission.records[0] = `multi-agent     ${multiAgentEnabled ? "enabled" : "disabled"}`
      state.lastAction = multiAgentEnabled ? "启用 Multi-Agent" : "关闭 Multi-Agent"
    } else {
      state.lastAction = "Multi-Agent 切换失败"
    }
    renderNavigation()
  }

  function renderNavigation() {
    const route = routeById(state.currentRoute)
    topLeft.content = `${route.icon} ${route.title}  ·  Stack: ${state.stack.join(" › ")}`
    topRight.content = "Tab/Shift+Tab 焦点 · M 菜单 · ↑↓/j/k 选择 · Enter 激活 · Esc/B 返回 · Q 退出"
    menuHint.content = `${state.menuOpen ? "▼" : "≡"} 菜单 (M) · 焦点：${focusLabel()}`
    for (let i = 0; i < ROUTES.length; i += 1) {
      const item = ROUTES[i]
      const selected = item.id === state.currentRoute ? "●" : " "
      const focused = state.focus === "nav" && i === state.navIndex ? "▶" : " "
      const menu = state.menuOpen ? "│" : " "
      const text = `${focused}${selected}${menu} ${item.key} ${item.icon} ${item.title}`
      const node = navText.get(item.id)
      node.content = text
      node.fg = item.id === state.currentRoute ? THEME.accent : THEME.text
    }
    viewTitle.content = `${route.icon} ${route.title} · OpenTUI page`
    routeContent.content = renderPageLines(route, state)
    log.content = `导航状态一致：route=${state.currentRoute}; focus=${state.focus}; menu=${state.menuOpen ? "open" : "closed"}`
    statusLeft.content = `运行时：OpenTUI ${options.mode === "automated-nav" ? "(automated)" : ""}`
    statusCenter.content = `当前视图：${route.title} | 焦点：${focusLabel()}`
    statusRight.content = "Q 退出 | M 菜单 | Esc/B 返回 | / 过滤 | [ ] 滚动 | Ctrl+数字跳转"
    renderer.requestRender()
  }

  input.on("enter", () => {
    const value = input.value.trim()
    state.lastInput = value
    const result = value
      ? serviceBridge(options, { operation: "submit", route: state.currentRoute, value })
      : { ok: false, error: { message: "输入为空" } }
    if (result.ok) {
      hydratePageCatalog(options)
      state.lastAction = `已提交：${value}`
      log.content = `应用服务已处理：${value}`
    } else {
      const message = result.error?.message || "应用服务未处理输入"
      state.lastAction = `提交失败：${message}`
      log.content = state.lastAction
    }
    input.value = ""
    renderNavigation()
  })

  renderer.root.add(root)
  setFocus("input")
  renderNavigation()
  return { root, input, log, state, options, switchRoute, goBack, moveNav, setFocus, renderNavigation, toggleMultiAgent }
}

function routeKey(renderer, shell, event) {
  const name = String(event.name || "").toLowerCase()
  const route = ROUTES.find((item) => item.key === name)
  if (route && (event.ctrl || shell.state.focus !== "input" || shell.state.menuOpen)) {
    event.preventDefault()
    shell.switchRoute(route.id)
    return true
  }
  if (name === "p" && (event.ctrl || shell.state.menuOpen || shell.state.focus !== "input")) {
    event.preventDefault()
    shell.switchRoute("permission")
    return true
  }
  if (name === "tab") {
    event.preventDefault()
    const order = ["input", "nav", "content"]
    const current = order.indexOf(shell.state.focus)
    const offset = event.shift ? -1 : 1
    shell.setFocus(order[(current + offset + order.length) % order.length])
    return true
  }
  if (name === "a" && shell.state.currentRoute === "permission" && shell.state.focus !== "input") {
    event.preventDefault()
    shell.toggleMultiAgent()
    return true
  }
  if (name === "m") {
    event.preventDefault()
    shell.state.menuOpen = !shell.state.menuOpen
    shell.setFocus(shell.state.menuOpen ? "nav" : shell.state.focus)
    return true
  }
  if (["up", "k"].includes(name)) {
    if (shell.state.focus !== "input" || shell.state.menuOpen) {
      event.preventDefault()
      if (shell.state.focus === "content" && !shell.state.menuOpen) {
        const count = Math.max(1, routeById(shell.state.currentRoute).records.length)
        shell.state.selection = (shell.state.selection - 1 + count) % count
        shell.state.lastAction = "上一项"
        shell.renderNavigation()
      } else {
        shell.moveNav(-1)
      }
      return true
    }
  }
  if (["down", "j"].includes(name)) {
    if (shell.state.focus !== "input" || shell.state.menuOpen) {
      event.preventDefault()
      if (shell.state.focus === "content" && !shell.state.menuOpen) {
        const count = Math.max(1, routeById(shell.state.currentRoute).records.length)
        shell.state.selection = (shell.state.selection + 1) % count
        shell.state.lastAction = "下一项"
        shell.renderNavigation()
      } else {
        shell.moveNav(1)
      }
      return true
    }
  }
  if (name === "/" && shell.state.focus !== "input") {
    event.preventDefault()
    shell.state.filter = shell.state.filter ? "" : "open"
    shell.state.lastAction = shell.state.filter ? "启用页面过滤" : "清除页面过滤"
    shell.renderNavigation()
    return true
  }
  if (["[", "]"].includes(name) && shell.state.focus !== "input") {
    event.preventDefault()
    shell.state.pageOffset = Math.max(0, shell.state.pageOffset + (name === "]" ? 1 : -1))
    shell.state.lastAction = name === "]" ? "向下滚动" : "向上滚动"
    shell.renderNavigation()
    return true
  }
  if (name === "enter" && shell.state.focus === "nav") {
    event.preventDefault()
    shell.switchRoute(ROUTES[shell.state.navIndex].id)
    shell.setFocus("content")
    return true
  }
  if (name === "enter" && shell.state.focus === "content") {
    event.preventDefault()
    const route = routeById(shell.state.currentRoute)
    const rawRecords = route.rawRecords || []
    const record = rawRecords[shell.state.selection % Math.max(1, rawRecords.length)]
    const result = record
      ? serviceBridge(shell.options, { operation: "activate", route: route.id, record })
      : { ok: false, error: { message: "没有可激活记录" } }
    shell.state.lastAction = result.ok
      ? `已激活 ${route.records[shell.state.selection % Math.max(1, route.records.length)]}`
      : `激活失败：${result.error?.message || "未知错误"}`
    shell.renderNavigation()
    return true
  }
  if (["escape", "b", "backspace"].includes(name) && shell.state.focus !== "input") {
    event.preventDefault()
    shell.goBack()
    return true
  }
  if (name === "escape" && shell.state.focus === "input") {
    event.preventDefault()
    shell.input.value = ""
    shell.state.lastAction = "取消当前流式任务"
    shell.renderNavigation()
    return true
  }
  if (name === "q" && !event.ctrl && !event.meta) {
    event.preventDefault()
    renderer.destroy()
    return true
  }
  return false
}

function runAutomatedNav(renderer) {
  const keys = [
    parsedKey("tab"),
    parsedKey("down"),
    parsedKey("enter"),
    parsedKey("tab"),
    parsedKey("m"),
    parsedKey("down"),
    parsedKey("enter"),
    parsedKey("b"),
    parsedKey("8", { ctrl: true, raw: "ctrl+8" }),
    parsedKey("q"),
  ]
  keys.forEach((key, index) => {
    setTimeout(() => renderer.keyInput.processParsedKey(key), 80 * (index + 1))
  })
}

function runFullPageInteractions(renderer) {
  const keys = []
  ROUTES.forEach((route, index) => {
    keys.push(parsedKey(route.key, { ctrl: true, raw: `ctrl+${route.key}` }))
    if (index === 0) {
      keys.push(parsedKey("tab"))
      keys.push(parsedKey("tab"))
    }
    keys.push(parsedKey("down"))
    keys.push(parsedKey("/"))
    keys.push(parsedKey("]"))
    keys.push(parsedKey("enter"))
  })
  keys.push(parsedKey("p", { ctrl: true, raw: "ctrl+p" }))
  keys.push(parsedKey("tab"))
  keys.push(parsedKey("tab"))
  keys.push(parsedKey("enter"))
  keys.push(parsedKey("q"))
  keys.forEach((key, index) => {
    setTimeout(() => renderer.keyInput.processParsedKey(key), 45 * (index + 1))
  })
}

async function runInteractionMatrix(renderer, shell, options) {
  const { createMockMouse } = await import("@opentui/core/testing")
  renderer.resize(80, 24)
  shell.renderNavigation()
  const mouse = createMockMouse(renderer)
  const beforeMouse = shell.state.navIndex
  await mouse.scroll(5, 10, "down")
  const mouseHandled = shell.state.navIndex !== beforeMouse
  shell.setFocus("input")
  shell.input.value = "中文宽字符与长文本".repeat(40)
  renderer.keyInput.processParsedKey(parsedKey("escape"))
  const cancellationHandled = shell.state.lastAction === "取消当前流式任务"
  renderer.resize(120, 30)
  shell.switchRoute("diagnose")
  const rejected = serviceBridge(options, { operation: "unsupported-test" })
  const recovered = serviceBridge(options, { operation: "catalog" })
  setTimeout(() => {
    process.stdout.write(
      `SUPERMEDICINE_OPENTUI_MATRIX_OK viewport=80x24>120x30 mouse=${mouseHandled} cancel=${cancellationHandled} recovered=${!rejected.ok && recovered.ok}\n`,
    )
    renderer.destroy()
  }, 100)
}

async function run() {
  const args = parseArgs(process.argv.slice(2))
  let renderer
  try {
    renderer = await createCliRenderer({
      exitOnCtrlC: true,
      clearOnShutdown: true,
      useMouse: true,
      targetFps: 30,
      consoleMode: "disabled",
      screenMode: "alternate-screen",
    })
    const shell = mountShell(renderer, args)
    renderer.keyInput.on("keypress", (event) => {
      routeKey(renderer, shell, event)
    })
    renderer.on(CliRenderEvents.DESTROY, () => {
      if (args.mode === "smoke") {
        process.stdout.write("SUPERMEDICINE_OPENTUI_SMOKE_OK\n")
      } else if (args.mode === "automated-nav") {
        process.stdout.write(`SUPERMEDICINE_OPENTUI_NAV_OK route=${shell.state.currentRoute} stack=${shell.state.stack.join(">")} focus=${shell.state.focus}\n`)
      } else if (args.mode === "full-page-interactions") {
        process.stdout.write(`SUPERMEDICINE_OPENTUI_FULL_PAGE_OK route=${shell.state.currentRoute} stack=${shell.state.stack.join(">")} focus=${shell.state.focus} action=${shell.state.lastAction}\n`)
      }
    })
    renderer.start()
    renderer.requestRender()
    if (args.mode === "smoke") {
      setTimeout(() => {
        renderer.keyInput.processParsedKey(parsedKey("q", { source: "raw" }))
        if (!renderer.isDestroyed) {
          renderer.destroy()
        }
      }, args.smokeMs)
    } else if (args.mode === "automated-nav") {
      runAutomatedNav(renderer)
    } else if (args.mode === "full-page-interactions") {
      runFullPageInteractions(renderer)
    } else if (args.mode === "interaction-matrix") {
      await runInteractionMatrix(renderer, shell, args)
    }
  } catch (error) {
    if (renderer && !renderer.isDestroyed) {
      renderer.destroy()
    }
    const message = error instanceof Error ? error.message : String(error)
    process.stderr.write(`SuperMedicine OpenTUI runtime failed: ${message}\n`)
    process.exitCode = 1
  }
}

await run()
