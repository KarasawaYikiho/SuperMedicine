# RAG Provider 实现规范

本文档是 RAG Provider 的最小接口参考。更完整的插件行为、错误结构、权限边界和
密钥处理以 `plugins/rag/interface.py`、`plugins/rag/local_provider.py`、
`plugins/rag/pubmed_provider.py` 以及项目架构/安全文档为准。

RAG 输出仅供医学科研辅助和检索上下文整理使用，不构成临床、监管或证据质量结论。
外部 Provider 必须通过环境变量或私有配置引用密钥，不能把 API key、私有端点或原始
请求日志写入 Markdown、清单或可提交配置。

## 接口要求

实现 `RAGProvider` 抽象基类的三个方法：

### query(query: str, scope: str) -> dict
- query: 用户查询文本
- scope: 检索范围 (literature | knowledge_base | project_context)

### store_context(key: str, value: Any) -> None
- 存储项目上下文信息

### retrieve_context(key: str) -> Any | None
- 检索之前存储的项目上下文

## 安全要求

- 本地 Provider 应明确标记本地资源来源；外部 Provider 应明确标记外部资源来源。
- 网络/API 访问必须由调用路径进行权限检查、超时控制和错误脱敏。
- 返回结构应保留 `status`、`provider`、`items`、`errors` 等稳定字段，便于上层在不暴露敏感信息的情况下诊断。
