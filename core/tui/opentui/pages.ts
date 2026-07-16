import { ScrollBoxRenderable } from "@opentui/core"
import { createText } from "./components.ts"
import { THEME } from "./theme.ts"

const EMPTY_STATES = Object.freeze({
  chat: ["开始新的科研对话", "在下方输入问题；业务服务将在下一阶段接入。"],
  dashboard: ["暂无运行状态", "连接业务服务后可查看工作区、模型与插件状态。"],
  workspace: ["尚未载入工作区", "连接业务服务后可创建、选择和管理工作区。"],
  paper: ["暂无论文", "连接业务服务后可导入论文并查看元数据。"],
  experience: ["暂无经验记录", "连接业务服务后可整理与导出研究经验。"],
  tool: ["暂无工具", "连接业务服务后可扫描并运行已授权工具。"],
  dialog: ["暂无对话历史", "连接业务服务后可查看经过脱敏的会话摘要。"],
  llm: ["尚未载入模型配置", "连接业务服务后可管理模型提供方。"],
  experiment: ["暂无实验", "连接业务服务后可建立实验步骤与记录。"],
  log: ["暂无日志报告", "连接业务服务后可查看脱敏报告。"],
  permission: ["尚未载入权限策略", "默认保持保守权限；高风险操作仍需明确确认。"],
  "self-evolution": ["暂无可预览变更", "写入操作必须经过明确授权。"],
  diagnose: ["尚未开始诊断", "连接业务服务后可检查运行环境与配置。"],
})

export function createPage(renderer, route) {
  const [emptyTitle, emptyBody] = EMPTY_STATES[route.id]
  const page = new ScrollBoxRenderable(renderer, {
    id: `page-${route.id}`,
    width: "100%",
    height: "100%",
    flexGrow: 1,
    scrollY: true,
    scrollX: false,
    focusable: true,
    border: false,
    backgroundColor: THEME.background,
    contentOptions: { flexDirection: "column", gap: 1, padding: 1 },
    verticalScrollbarOptions: { trackOptions: { backgroundColor: THEME.surfaceRaised } },
  })
  page.add(createText(renderer, { content: route.label, fg: THEME.accent }))
  page.add(createText(renderer, { content: emptyTitle }))
  page.add(createText(renderer, { content: emptyBody, fg: THEME.muted, height: 2 }))
  return page
}
