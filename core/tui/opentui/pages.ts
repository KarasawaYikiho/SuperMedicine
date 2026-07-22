import { InputRenderable, MarkdownRenderable, ScrollBoxRenderable } from "@opentui/core"
import { createActionButton, createListItem, createPanel, createText } from "./components.ts"
import { THEME } from "./theme.ts"

const PAGE_CONTENT = Object.freeze({
  chat: ["开始新的科研对话", "选择工作区后在下方输入问题。"],
  dashboard: ["暂无运行状态", "刷新以读取工作区、模型与插件状态。"],
  workspace: ["暂无工作区", "输入名称后可创建工作区。"],
  paper: ["暂无论文", "选择工作区后可读取论文元数据。"],
  experience: ["暂无经验记录", "选择工作区后可读取研究经验。"],
  tool: ["暂无工具", "选择工作区后可扫描已授权工具。"],
  dialog: ["暂无对话历史", "这里只显示脱敏会话摘要。"],
  llm: ["暂无模型配置", "密钥不会在此页面回显。"],
  experiment: ["暂无实验", "刷新以读取实验步骤。"],
  log: ["暂无日志报告", "输入标题可写入脱敏日志。"],
  permission: ["暂无权限状态", "高风险操作仍需明确确认。"],
  "self-evolution": ["暂无可预览变更", "写入操作需要单独明确确认。"],
  diagnose: ["暂无诊断记录", "刷新以检查运行环境与配置。"],
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
  paper: "刷新论文",
  experience: "刷新经验",
  tool: "刷新工具",
  dialog: "刷新历史",
  llm: "刷新配置",
  experiment: "刷新实验",
  log: "写入日志",
  permission: "读取权限策略",
  "self-evolution": "刷新预览",
  diagnose: "开始诊断",
})

function recordLabel(record) {
  if (typeof record === "string") return record
  if (record === null || record === undefined) return "空记录"
  if (typeof record !== "object") return String(record)
  return JSON.stringify(record)
}

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
      content: "## 开始新的科研对话\n\n选择工作区后在下方输入问题。",
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
  let field = null
  if (form) {
    page.add(createText(renderer, { content: form[0], fg: THEME.muted }))
    field = new InputRenderable(renderer, {
      id: `page-field-${route.id}`,
      width: "100%",
      placeholder: form[1],
      fg: THEME.text,
      backgroundColor: THEME.surface,
    })
    page.add(field)
  }

  const records = resources.pageFixtures?.[route.id] || []
  for (const [index, record] of records.entries()) {
    page.add(createListItem(renderer, {
      id: `page-record-${route.id}-${index}`,
      label: recordLabel(record),
      onActivate: () => resources.onActivate?.(route.id, record),
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
      async onActivate() {
        feedback.content = "处理中…"
        renderer.requestRender()
        try {
          feedback.content = await resources.onAction?.(route.id, field?.value || "") || "已刷新"
        } catch (error) {
          feedback.content = error instanceof Error ? error.message : String(error)
        }
        renderer.requestRender()
      },
    }))
    page.add(feedback)
  }
  return page
}
