export const ROUTES = Object.freeze([
  { id: "chat", label: "对话", symbol: "●", shortcut: "1", capability: "chat" },
  { id: "dashboard", label: "状态看板", symbol: "○", shortcut: "2", capability: "status" },
  { id: "workspace", label: "工作区", symbol: "›", shortcut: "3", capability: "workspace" },
  { id: "paper", label: "论文", symbol: "›", shortcut: "4", capability: "paper" },
  { id: "experience", label: "经验", symbol: "›", shortcut: "5", capability: "experience" },
  { id: "tool", label: "工具", symbol: "+", shortcut: "6", capability: "tool" },
  { id: "dialog", label: "对话历史", symbol: "›", shortcut: "7", capability: "history" },
  { id: "llm", label: "LLM 配置", symbol: "○", shortcut: "8", capability: "llm" },
  { id: "experiment", label: "实验", symbol: "+", shortcut: "9", capability: "experiment" },
  { id: "log", label: "日志报告", symbol: "›", shortcut: "0", capability: "log" },
  { id: "permission", label: "权限", symbol: "○", shortcut: "P", capability: "permission" },
  { id: "self-evolution", label: "自进化", symbol: "+", shortcut: "E", capability: "evolution" },
  { id: "diagnose", label: "诊断", symbol: "×", shortcut: "D", capability: "diagnose" },
])

export function createShellState() {
  return {
    currentRoute: "chat",
    hoveredRoute: null,
    workspaceName: "未选择工作区",
    connectionStatus: "本地界面",
  }
}

export function findRoute(routeId: string) {
  return ROUTES.find((route) => route.id === routeId) || ROUTES[0]
}
