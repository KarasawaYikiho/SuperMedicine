const CONTROL_OR_ESCAPE = /\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))|[\x00-\x1f\x7f]/g
const SENSITIVE_ASSIGNMENT = /\b(api[_-]?key|token|password|secret|authorization)\b\s*[:=]\s*[^\s,;]+/gi

function looksLikeInternalSerialization(text) {
  if (/^(?:BridgeError|[A-Z][A-Za-z]+Error):/.test(text) || /\bat\s+.*\.[cm]?[jt]s:\d+(?::\d+)?\b/.test(text)) {
    return true
  }
  if (!text.startsWith("{") && !text.startsWith("[")) return false
  try {
    const parsed = JSON.parse(text)
    return parsed !== null && typeof parsed === "object"
  } catch {
    return false
  }
}

export function safeUiText(value, fallback = "记录") {
  if (typeof value !== "string" && typeof value !== "number" && typeof value !== "boolean") {
    return fallback
  }
  const text = String(value).replace(CONTROL_OR_ESCAPE, " ").replace(/\s+/g, " ").trim()
  if (!text || looksLikeInternalSerialization(text)) return fallback
  return text.replace(SENSITIVE_ASSIGNMENT, "$1=[已隐藏]").slice(0, 160)
}

export function userFacingError(error) {
  const code = typeof error?.code === "string" ? error.code : ""
  if (code === "disconnected") return "服务连接已中断，请退出后重新启动。"
  if (code === "client_timeout" || code === "timeout") return "服务响应超时，请重试。"
  if (code === "permission_denied") return "权限不足，操作未执行。"
  if (code === "cancelled") return "操作已取消。"
  if (code === "workspace_not_selected") return "请先选择工作区。"
  return "操作未完成，请重试。"
}

export function presentationRecord(record) {
  if (typeof record === "string") return { label: safeUiText(record), activation: record }
  if (!record || typeof record !== "object") return { label: "记录", activation: null }
  return {
    label: safeUiText(record.label),
    activation: record.activation && typeof record.activation === "object" ? record.activation : null,
  }
}
