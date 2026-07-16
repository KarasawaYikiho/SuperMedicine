import { InputRenderable, MarkdownRenderable, ScrollBoxRenderable } from "@opentui/core"
import { createActionButton, createListItem, createPanel, createText } from "./components.ts"
import { THEME } from "./theme.ts"

const PAGE_CONTENT = Object.freeze({
  chat: ["开始新的科研对话", "在下方输入问题。业务服务尚未连接。"],
  dashboard: ["暂无运行状态", "连接业务服务后可读取工作区、模型与插件状态。"],
  workspace: ["尚未载入工作区", "输入仅保留在当前界面；连接服务前不会创建工作区。"],
  paper: ["暂无论文", "连接业务服务后可导入论文并读取元数据。"],
  experience: ["暂无经验记录", "连接业务服务后可整理研究经验。"],
  tool: ["暂无工具", "连接业务服务后可扫描已授权工具。"],
  dialog: ["暂无对话历史", "连接业务服务后可读取脱敏会话摘要。"],
  llm: ["尚未载入模型配置", "密钥不会在此页面回显。连接服务前不会保存。"],
  experiment: ["暂无实验", "连接业务服务后可建立实验步骤。"],
  log: ["暂无日志报告", "连接业务服务后可生成脱敏报告。"],
  permission: ["尚未载入权限策略", "默认保持保守权限；高风险操作仍需明确确认。"],
  "self-evolution": ["暂无可预览变更", "连接业务服务前不会执行写入。"],
  diagnose: ["尚未开始诊断", "连接业务服务后可检查运行环境与配置。"],
})

const FORM_ROUTES = Object.freeze({
  workspace: ["工作区名称", "输入工作区名称"],
  llm: ["模型提供方", "输入提供方名称"],
  experiment: ["实验名称", "输入实验名称"],
  log: ["报告标题", "输入报告标题"],
})
const ACTION_LABELS = Object.freeze({
  dashboard: "刷新状态",
  workspace: "创建工作区",
  paper: "导入论文",
  experience: "记录经验",
  tool: "扫描工具",
  dialog: "刷新历史",
  llm: "保存配置",
  experiment: "建立实验",
  log: "生成报告",
  permission: "读取权限策略",
  "self-evolution": "预览变更",
  diagnose: "开始诊断",
})

function addEmptyState(renderer, page, route) {
  const [title, body] = PAGE_CONTENT[route.id]
  const empty = createPanel(renderer, {
    id: `page-empty-${route.id}`,
    width: "100%",
    height: 4,
    flexDirection: "column",
    paddingX: 1,
  })
  empty.add(createText(renderer, { content: title }))
  empty.add(createText(renderer, { content: body, fg: THEME.muted, height: 2 }))
  page.add(empty)
}

export function createPage(renderer, route, resources) {
  const page = new ScrollBoxRenderable(renderer, {
    id: `page-${route.id}`,
    width: "100%",
    height: "100%",
    flexGrow: 1,
    scrollY: true,
    scrollX: false,
    focusable: false,
    border: false,
    backgroundColor: THEME.background,
    contentOptions: { flexDirection: "column", gap: 1, padding: 1 },
    verticalScrollbarOptions: { trackOptions: { backgroundColor: THEME.surfaceRaised } },
  })
  page.focusable = false
  page.add(createText(renderer, { content: route.label, fg: THEME.accent }))

  if (route.id === "chat") {
    page.add(new MarkdownRenderable(renderer, {
      id: "page-markdown-chat",
      width: "100%",
      height: 5,
      content: "## 开始新的科研对话\n\n业务服务尚未连接。",
      syntaxStyle: resources.markdownSyntaxStyle,
      fg: THEME.text,
      renderNode(token) {
        if (token.type !== "heading" && token.type !== "paragraph") return undefined
        return createText(renderer, {
          content: token.text || token.raw,
          fg: token.type === "heading" ? THEME.accent : THEME.text,
        })
      },
    }))
  }

  const form = FORM_ROUTES[route.id]
  if (form) {
    page.add(createText(renderer, { content: form[0], fg: THEME.muted }))
    page.add(new InputRenderable(renderer, {
      id: `page-field-${route.id}`,
      width: "100%",
      placeholder: form[1],
      fg: THEME.text,
      backgroundColor: THEME.surface,
    }))
  }

  const records = resources.pageFixtures?.[route.id] || []
  for (const [index, record] of records.entries()) {
    page.add(createListItem(renderer, {
      id: `page-record-${route.id}-${index}`,
      label: String(record),
    }))
  }

  if (route.id !== "chat" && records.length === 0) addEmptyState(renderer, page, route)
  if (route.id !== "chat") {
    const feedback = createText(renderer, {
      id: `page-feedback-${route.id}`,
      content: "",
      fg: THEME.warning,
    })
    page.add(createActionButton(renderer, {
      id: `page-action-${route.id}`,
      label: ACTION_LABELS[route.id],
      onActivate() {
        feedback.content = "业务服务未连接，未执行。"
        renderer.requestRender()
      },
    }))
    page.add(feedback)
  }
  return page
}
