# RAG Provider 实现规范

## 接口要求

实现 `RAGProvider` 抽象基类的三个方法：

### query(query: str, scope: str) -> dict
- query: 用户查询文本
- scope: 检索范围 (literature | knowledge_base | project_context)

### store_context(key: str, value: Any) -> None
- 存储项目上下文信息

### retrieve_context(key: str) -> Any | None
- 检索之前存储的项目上下文
