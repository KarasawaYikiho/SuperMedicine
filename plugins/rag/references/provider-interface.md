# RAG Provider 实现规范

本文档是 RAG Provider 的最小接口参考。更完整的插件行为、错误结构和安全边界以
`plugins/rag/interface.py`、`plugins/rag/local_provider.py` 以及项目架构文档为准。

## 接口要求

实现 `RAGProvider` 抽象基类的三个方法：

### query(query: str, scope: str) -> dict
- query: 用户查询文本
- scope: 检索范围 (literature | knowledge_base | project_context)

### store_context(key: str, value: Any) -> None
- 存储项目上下文信息

### retrieve_context(key: str) -> Any | None
- 检索之前存储的项目上下文
