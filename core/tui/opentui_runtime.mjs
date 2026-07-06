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
  const args = { mode: "interactive", projectRoot: process.cwd(), smokeMs: 350 }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === "--smoke") {
      args.mode = "smoke"
    } else if (arg === "--automated-nav") {
      args.mode = "automated-nav"
    } else if (arg === "--full-page-interactions") {
      args.mode = "full-page-interactions"
    } else if (arg === "--project-root") {
      args.projectRoot = argv[++i] || process.cwd()
    } else if (arg === "--smoke-ms") {
      args.smokeMs = Number(argv[++i] || args.smokeMs)
    }
  }
  return args
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
    records: ["User #1  直接输入科研任务或 /help", "System   工具执行经过权限、沙箱、审计", "Assistant Streaming area preserves redaction and turn IDs"],
    actions: ["Enter 提交 prompt", "/ 聚焦页面过滤", "[ ] 滚动 scrollback"],
  },
  dashboard: {
    key: "2",
    title: "状态看板",
    icon: "📊",
    intent: "TextTable-style runtime board for workspace/plugin/LLM/token status.",
    sections: ["Runtime Health", "Workspace Metrics", "LLM / Token Summary"],
    records: ["初始化     Python ConfigCenter", "工作区       WorkspaceManager", "LLM         redacted provider diagnostics"],
    actions: ["r 刷新 metrics", "Enter 打开当前指标", "Tab 切换焦点"],
  },
  workspace: {
    key: "3",
    title: "工作区",
    icon: "📁",
    intent: "OpenTUI selectable workspace list with bordered create/select/delete forms.",
    sections: ["Workspace Select", "Create Workspace", "Danger Zone"],
    records: ["study-a        最近选择", "new-workspace  输入 slug 创建", "delete:<id>    删除确认格式"],
    actions: ["j/k 选择工作区", "Enter 选择", "Ctrl+N 聚焦创建输入"],
  },
  paper: {
    key: "4",
    title: "论文",
    icon: "📄",
    intent: "OpenTUI import/list/enrich panels with permission-aware online enrichment.",
    sections: ["Import Form", "Paper List", "Online Enrichment"],
    records: ["PDF 路径       安全导入", "DOI/PMID       元数据", "enrich         网络请求需确认"],
    actions: ["Enter 导入/选择", "r 刷新论文", "/ 过滤标题"],
  },
  experience: {
    key: "5",
    title: "经验",
    icon: "💡",
    intent: "OpenTUI experience capture, suggestion and export workflow.",
    sections: ["Suggest", "Records", "Export"],
    records: ["全局经验       general scope", "工作区经验     workspace scope", "delete:<id>    删除确认"],
    actions: ["Enter 确认写入", "e 导出", "/ 过滤标签"],
  },
  tool: {
    key: "6",
    title: "工具",
    icon: "🔧",
    intent: "OpenTUI multi-panel tool scan/add/run workflow; permissions stay in Python service layer.",
    sections: ["Tool Registry", "Scan Candidates", "Sandbox Run"],
    records: ["heatmap.py      Python", "umap.R          R", "run            PermissionEngine + sandbox"],
    actions: ["s 扫描", "a 添加", "Enter 运行选中工具"],
  },
  dialog: {
    key: "7",
    title: "对话历史",
    icon: "📋",
    intent: "OpenTUI audit timeline; raw conversation fields remain rejected by Python store.",
    sections: ["Timeline", "Session Filter", "Privacy Guard"],
    records: ["screen_opened   摘要事件", "tool_run        审计摘要", "raw fields      blocked"],
    actions: ["/ 过滤 session", "Enter 查看摘要", "[ ] 滚动时间线"],
  },
  llm: {
    key: "8",
    title: "LLM 配置",
    icon: "🤖",
    intent: "OpenTUI settings panel for provider CRUD with hidden API Key display.",
    sections: ["Provider List", "Provider Form", "Validation"],
    records: ["openai          ready/redacted", "base_url        visible", "api_key         hidden input"],
    actions: ["Enter 切换 Provider", "d 删除", "Ctrl+S 保存"],
  },
  experiment: {
    key: "9",
    title: "实验",
    icon: "🧪",
    intent: "OpenTUI protocol stepper with JSON/key=value data input and calculation boundary.",
    sections: ["Protocol", "Step Data", "Reagent Calculation"],
    records: ["step 1          必填输入", "key=value       数据格式", "calculate       插件沙箱"],
    actions: ["Enter 保存步骤", "c 计算", "l 保存日志"],
  },
  log: {
    key: "0",
    title: "Log 报告",
    icon: "📝",
    intent: "OpenTUI log viewer/writer with redacted report details and list filtering.",
    sections: ["Report Writer", "Report List", "Detail Viewer"],
    records: ["session id      optional", "message        redacted before save", "detail         redacted display"],
    actions: ["Enter 保存/查看", "r 刷新", "/ 过滤报告"],
  },
  permission: {
    key: "p",
    title: "权限",
    icon: "🛡️",
    intent: "OpenTUI security panel for conservative/full access mode and root policy visibility.",
    sections: ["Access Mode", "Root Policy", "Confirmations"],
    records: ["conservative    默认", "FULL           高风险确认", "policy         PermissionEngine"],
    actions: ["Enter 查看策略", "f 完全访问确认", "Esc 返回"],
  },
  "self-evolution": {
    key: "e",
    title: "自进化",
    icon: "🧬",
    intent: "OpenTUI utility panel for preview/write audit without approval claims.",
    sections: ["Preview", "Audit", "Write Boundary"],
    records: ["artifact        preview only", "approval       not recorded", "write          explicit action"],
    actions: ["p 预览", "w 写入", "Esc 返回"],
  },
  diagnose: {
    key: "d",
    title: "诊断",
    icon: "🩺",
    intent: "OpenTUI diagnostics panel for runtime/config/service checks.",
    sections: ["Runtime", "Config", "Services"],
    records: ["Bun             @opentui/core@0.4.1", "ConfigCenter    load diagnostics", "Python layer    business services"],
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
  const state = {
    currentRoute: "chat",
    stack: ["chat"],
    focus: "input",
    menuOpen: false,
    navIndex: 0,
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
    state.lastAction = value ? `提交输入：${value}` : "空输入"
    log.content = value ? `收到输入：${value}` : "输入为空；请键入任务。"
    input.value = ""
    renderer.requestRender()
  })

  renderer.root.add(root)
  setFocus("input")
  renderNavigation()
  return { root, input, log, state, switchRoute, goBack, moveNav, setFocus, renderNavigation }
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
        shell.state.selection = (shell.state.selection + 2) % 3
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
        shell.state.selection = (shell.state.selection + 1) % 3
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
    shell.state.lastAction = `激活 ${routeById(shell.state.currentRoute).records[shell.state.selection % 3]}`
    shell.renderNavigation()
    return true
  }
  if (["escape", "b", "backspace"].includes(name) && shell.state.focus !== "input") {
    event.preventDefault()
    shell.goBack()
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
