# SuperMedicine 用户要求执行清单与需求映射

本文件用于把本轮用户明确提出的所有要求拆分为可追踪、可验收的实现清单，并记录对应文档/界面提示覆盖情况。本轮文档更新只调整说明文字和帮助文案，不改变生产功能逻辑。

## 使用规则

- 每条需求使用稳定 ID：`REQ-EXP-*`、`REQ-TOOL-*`、`REQ-PERM-*`、`REQ-TUI-*`。
- 后续实现、测试、评审和变更记录应引用对应需求 ID，确保需求与代码改动保持映射。
- 任一需求实现前，应在对应实现任务中列出“关联需求 ID”。
- 任一需求验收时，应按本文“验收关注点”逐项确认，避免遗漏。

## 总览映射

| ID | 用户要求原意 | 领域 | 后续实现状态 | 验收关注点 |
| --- | --- | --- | --- | --- |
| REQ-EXP-001 | 实验指导器不再锁定 WB 实验 | 实验指导器 | 已实现 | 实验指导器可选择/加载非 WB 实验；WB 仅作为一种配置或示例存在。实现证据：`core/experiment_protocols.py` 从配置加载协议；`plugins/experiments/western_blot_basic.yaml` 保存 WB 配置；`Cli.py experiment start --protocol` 不再限制 choices=["wb"]。 |
| REQ-EXP-002 | 实验指导器可读取插件文件夹统一大目录内多个实验配置 | 实验指导器 | 已实现 | 可从统一插件实验目录发现多个配置；配置列表可被展示/选择。实现证据：`plugins/experiments/` 统一目录含 WB 与细胞培养配置；`core/experiment_protocols.py load_protocols()` 自动发现并校验；`Cli.py experiment list` 与 TUI 实验表展示可选配置；`tests/test_experiment_guide.py` 覆盖统一目录 YAML/JSON 扫描与 alias 切换。 |
| REQ-EXP-003 | 实验配置可与 LLM 接通 | 实验指导器/LLM | 已实现 | 实验配置可进入 LLM 上下文或调用流程；LLM 能理解当前实验配置。实现证据：`core/kernel.py` 在 LLM system messages 注入实验上下文；`core/experiment_protocols.py build_experiment_llm_context()` 提供当前/可用配置、步骤、参数、限制和编写规范；`Cli.py experiment context` 可查看注入内容；`tests/test_experiment_guide.py` 与 `tests/test_kernel.py` 覆盖选中协议切换后的 LLM 上下文注入。 |
| REQ-EXP-004 | LLM 可根据用户指令增加实验配置 | 实验指导器/LLM | 已实现 | 用户通过对话提出新增实验配置时，LLM 能生成并保存合规配置。实现证据：`core/experiment_protocols.py draft_experiment_config_from_instruction()`、`validate_experiment_config()`、`save_experiment_config()`、`create_experiment_config_from_instruction()` 实现草稿生成、格式校验、统一目录写入、命名冲突/覆盖保护；`Cli.py experiment add-config` 暴露规范化写入流程；`docs/experiment_config_authoring.md` 记录格式规范。 |
| REQ-TUI-001 | 当前对话框 Backspace 按键恢复正常 | TUI 输入 | 已实现 | 对话输入框中 Backspace 删除字符行为正常，不被全局快捷键或事件拦截破坏。实现证据：`core/tui/app.py` 中 `PromptInput` 将 Backspace/Ctrl+H/DEL 控制字节从终端控制序列过滤中豁免，交由 Textual 输入组件执行删除；`tests/test_regression_baseline.py` 覆盖 Unicode/中文、多行、文本中间、行首以及 Backspace 控制字节不被快捷键吞噬。 |
| REQ-TOOL-001 | Python/R 工具管理删除工具 ID 导入模式 | 工具管理 | 已实现 | 导入工具不再要求用户输入工具 ID 作为导入方式。实现证据：`Cli.py tool add` 改为展示扫描候选并通过 `--select` 选择编号或显示项；`core/tui/screens/tool_screen.py` 移除工具 ID 输入框并提示“无需输入或知道工具 ID”；`tests/test_workspace_tools.py` 覆盖 CLI 无选择时返回候选列表。 |
| REQ-TOOL-002 | Python/R 工具管理改为自动扫描对应目录并由用户选择导入 | 工具管理 | 已实现 | 系统自动扫描 Python/R 工具目录；用户从候选列表中选择导入。实现证据：`core/workspace_tools.py scan_import_candidates()` 自动扫描 `plugins/tools` 下 Python/R 工具目录、读取 `tool.yaml`/`plugin.yaml` 元数据并对缺失元数据降级显示；`import_scanned_tools()` 按候选选择导入并拒绝格式错误工具；`Cli.py tool scan/tool add --select` 与 TUI 扫描/添加按钮共用服务；`tests/test_workspace_tools.py` 覆盖 Python/R 扫描、缺失元数据降级、格式错误拒绝导入、CLI 选择导入和 runtime_state 记录。 |
| REQ-TOOL-003 | 向 LLM 注入工具编写规范，包括格式、存储位置等 | 工具管理/LLM | 已实现 | LLM 上下文包含工具格式、目录、命名、元数据和保存规范。实现证据：`core/workspace_tools.py` 定义与扫描/校验逻辑一致的 `TOOL_AUTHORING_SPEC` 与 `build_tool_authoring_llm_context()`；`core/kernel.py` 注入 Python/R workspace tool authoring rules；`docs/tool_authoring.md` 记录规范；`tests/test_kernel.py` 与 `tests/test_workspace_tools.py` 覆盖 LLM 上下文和规范/manifest/scanner 一致性。 |
| REQ-TOOL-004 | Python/R 工具目录补充主流数据分析算法 | 工具管理/数据分析 | 已实现 | Python/R 工具目录包含主流统计、建模、机器学习、生存分析等算法模板或工具。实现证据：`plugins/tools/python_data_analysis/tool.yaml` 与 `runner.py`、`plugins/tools/r_data_analysis/tool.yaml` 与 `runner.R` 提供描述性统计、缺失值分析、标准化/归一化、相关性、线性/逻辑回归、PCA、KMeans/层次聚类、可选随机森林/梯度提升封装、时间序列基础分析、t 检验/卡方检验/ANOVA；`docs/tool_authoring.md` 记录目录与可选重依赖策略。 |
| REQ-PERM-001 | 提供完全访问权限模式 | 权限 | 已实现 | 存在完整/全访问模式，按定义允许更高权限操作并保留必要审计。实现证据：`permission/access_mode.py` 定义 `AccessMode.FULL` 与 `AccessModePolicy.full()`，必须传入 `explicit_confirmation=True`/`full_mode_confirmed=True`；`insufficient_permission_helper()` 明确提示管理员/UAC 授权且不静默提权；`core/operation_guard.py` 可接入该策略层并继续调用权限引擎审计。 |
| REQ-PERM-002 | 提供保守/沙箱访问权限模式 | 权限 | 已实现 | 存在保守/沙箱模式，限制高风险文件、命令、网络或插件操作。实现证据：`permission/access_mode.py` 默认 `AccessMode.CONSERVATIVE`，项目内路径允许，项目外只读返回 `PROMPT_REQUIRED`，项目外写入/删除/执行默认拒绝，显式授权外部目录后才允许；`core/config_center.py` 的 `DEFAULT_FILE_ACCESS_CONFIG` 默认保守模式。 |
| REQ-PERM-003 | CLI 提供权限模式切换入口 | 权限/CLI | 已实现 | CLI 命令可查看并切换权限模式。实现证据：`Cli.py permission status/roots` 显示当前模式、风险提示和授权目录；`Cli.py permission mode conservative` 切回保守模式；`Cli.py permission mode full --confirm-full` 或交互输入 `FULL` 才能请求完全访问模式；`Cli.py permission authorize/revoke <path>` 添加/移除外部授权目录；`core/config_center.py` 持久化授权目录增删与模式切换，后续策略读取即时生效；风险提示明确不静默提权、不绕过系统权限，权限不足需管理员/UAC 显式授权；`tests/test_permission_modes.py` 覆盖 CLI 模式切换确认、授权/撤销与即时策略读取。 |
| REQ-PERM-004 | TUI 提供权限模式切换入口 | 权限/TUI | 已实现 | TUI 侧边栏和 `P` 快捷键提供“权限模式”入口，可查看/切换保守与完全访问模式；完全模式必须输入 `FULL` 显式确认；可添加/查看/移除外部授权目录；界面风险提示明确默认保守、完全模式仅使用当前进程/用户已有权限、权限不足需管理员/UAC 显式授权、不静默提权、不绕过 OS 权限。实现证据：`core/tui/app.py` 注册权限视图与状态栏模式展示；`core/tui/screens/permission_screen.py` 提供模式切换和外部授权目录管理；`core/config_center.py` 提供统一运行时 `get_file_access_policy()`，切换后后续策略读取即时生效；`tests/test_tui_permissions.py` 覆盖 TUI controller 的 FULL 确认与策略变化。 |
| REQ-PERM-005 | 程序运行过程中可随时切换权限模式 | 权限/运行时 | 已实现 | 核心运行时策略与 CLI/TUI 入口均支持无需重启切换，切换到 full 必须显式确认。实现证据：`permission/access_mode.py` 的 `AccessModePolicy.switch_mode()` 可在进程内即时切换；`core/config_center.py` 的 `set_file_access_mode()`、`get_file_access_policy()` 与 `authorize_external_file_access_directory()` 提供持久化/即时读取 API；`core/operation_guard.py` 通过 `access_policy` 参数使用当前策略；`tests/test_config_center.py`、`tests/test_permission_modes.py`、`tests/test_tui_permissions.py` 覆盖运行时即时切换、CLI/TUI 权限模式切换和外部目录授权。 |
| REQ-TUI-002 | LLM 对话窗口用户 #X、系统、状态与助手 #X 同步刷新显示 | TUI 对话显示 | 已实现 | 用户轮次编号、系统信息、状态信息、助手轮次编号在同一刷新周期内一致更新。实现证据：`core/tui/screens/chat_view.py` 使用同一 turn id 渲染用户 `#X` 与助手 `#X`，系统/状态消息不再推进轮次；`core/tui/app.py` 将提交时返回的 turn id 传入内核任务与助手输出；`tests/test_tui_chat_view.py` 覆盖用户/助手同号与运行中/完成状态事件。 |
| REQ-TUI-003 | 实时刷新并显示思考过程/合规处理状态 | TUI 对话显示/合规 | 已实现 | 对话期间实时展示思考过程摘要或状态，以及合规/权限处理状态。实现证据：`core/kernel.py` 为 LLM/插件路径提供 progress callback 和可选 `chat_stream` 增量事件；`core/tui/app.py` 使用后台线程执行内核并通过 `call_from_thread` 渲染状态、合规推理进度和助手增量内容，避免阻塞 UI 或修改输入框；`core/tui/screens/chat_view.py` 新增推理状态区与助手 delta 追加；不支持完整思考暴露时仅显示合规处理进度，不伪造内部思维；`tests/test_tui_chat_view.py` 覆盖增量渲染与推理状态文案。 |
| REQ-TUI-004 | 删除 1-0 快捷键直接切换视图 | TUI 快捷键 | 已实现 | 数字 1-0 不再直接切换视图，避免误触或影响输入。实现证据：`core/tui/app.py` 移除数字键 `switch_view` 绑定并让 `PromptInput` 保留数字普通输入；`core/tui/i18n.py`、`Cli.py`、`README.md` 删除 1-0 视图切换说明；`tests/test_regression_baseline.py` 与 `tests/test_tui_entrypoint.py` 覆盖数字键不切换视图、帮助文案不再展示 1-0 快捷键且 Q/F/? 等合法快捷键保留。 |
| REQ-TUI-005 | 改为一个按键呼出菜单 | TUI 快捷键/菜单 | 已实现 | 使用 `M` 单一快捷键打开主菜单，菜单可进入“选择视图”子菜单并切换视图；数字 `1-0` 不恢复直接切换。实现证据：`core/tui/app.py` 新增 `MainMenuScreen`/`ViewSelectMenuScreen` 与 `open_menu` 绑定；`core/tui/i18n.py`、`README.md` 更新快捷键提示；`tests/test_tui_entrypoint.py` 覆盖菜单呼出、子菜单视图列表和选择切换；`tests/test_regression_baseline.py` 覆盖数字键不打开菜单也不切换视图。 |
| REQ-TUI-006 | 在 TUI 左上角 Change Theme 同类菜单中增加视图选择子菜单 | TUI 菜单 | 已实现 | 主菜单左上角弹出，包含“选择视图”子菜单与 `Change Theme` 同类入口；进入子菜单可返回上级菜单，选择视图后关闭菜单并切换，主题切换仍调用 Textual `action_change_theme()`。实现证据：`core/tui/app.py` 的 `MainMenuScreen` 保留 `Change Theme` 项并推入 `ViewSelectMenuScreen`；`core/tui/app.tcss` 为左上角菜单面板和列表提供样式；`tests/test_tui_entrypoint.py` 覆盖菜单项、视图子菜单和切换行为。 |
| REQ-STATE-001 | 统一配置持久化与运行时状态同步 | 配置/CLI/TUI/LLM | 已实现 | CLI/TUI 读取同一 `ConfigCenter` 文件访问状态并展示同一权限模式标签；TUI 当前视图、当前实验协议、最近工具导入/工作区通过 `runtime_state` 持久化；Kernel LLM 消息读取统一运行时状态、当前实验协议和已导入工作区工具；配置损坏时 `ConfigCenter` 保守降级并在 CLI/TUI 状态/诊断中提示读取错误。实现证据：`core/config_center.py` runtime state API、`core/kernel.py` 统一运行时/实验/工具上下文注入、`Cli.py` 权限/实验/工具同步、`core/tui/app.py` 视图与权限状态同步、`core/tui/screens/experiment_screen.py` 实验选择同步、`core/tui/screens/tool_screen.py` 工具导入同步；`tests/test_kernel.py` 与 `tests/test_workspace_tools.py` 覆盖 LLM runtime_state 注入和工具导入状态记录。 |

## 分领域执行清单

### A. 实验指导器与实验配置

- [x] `REQ-EXP-001` 将实验指导器从 WB 固定实验中解耦，保留 WB 作为普通实验配置。
- [x] `REQ-EXP-002` 设计并实现统一实验配置大目录扫描机制，支持多个实验配置。
- [x] `REQ-EXP-003` 将被选中的实验配置接入 LLM 上下文/调用链。
- [x] `REQ-EXP-004` 支持 LLM 根据用户自然语言指令新增实验配置，并写入约定位置。

### B. Python/R 工具管理与 LLM 工具规范

- [x] `REQ-TOOL-001` 移除 Python/R 工具导入流程中的“按工具 ID 导入”模式。证据：`Cli.py`、`core/tui/screens/tool_screen.py`、`tests/test_workspace_tools.py`。
- [x] `REQ-TOOL-002` 改为扫描 Python/R 对应工具目录并让用户选择候选工具导入。证据：`core/workspace_tools.py`、`Cli.py`、`core/tui/screens/tool_screen.py`、`tests/test_workspace_tools.py`。
- [x] `REQ-TOOL-003` 向 LLM 注入工具编写规范，至少覆盖工具格式、文件/目录存储位置、命名规则、元数据和示例。证据：`core/workspace_tools.py`、`core/kernel.py`、`docs/tool_authoring.md`、`tests/test_kernel.py`、`tests/test_workspace_tools.py`。
- [x] `REQ-TOOL-004` 补充 Python/R 主流数据分析算法工具或模板，覆盖常见医学科研数据分析场景。证据：`plugins/tools/python_data_analysis/`、`plugins/tools/r_data_analysis/`、`docs/tool_authoring.md`。

### C. 权限模式与运行时切换

- [x] `REQ-PERM-001` 定义并实现完全访问权限模式。证据：`permission/access_mode.py`、`core/operation_guard.py`。
- [x] `REQ-PERM-002` 定义并实现保守/沙箱访问权限模式。证据：`permission/access_mode.py`、`core/config_center.py`。
- [x] `REQ-PERM-003` 在 CLI 中提供权限模式查看/切换入口。证据：`Cli.py permission status/roots/mode/authorize/revoke`、`core/config_center.py`。
- [x] `REQ-PERM-004` 在 TUI 中提供权限模式查看/切换入口。证据：`core/tui/app.py`、`core/tui/screens/permission_screen.py`、`core/config_center.py`。
- [x] `REQ-PERM-005` 支持程序运行过程中随时切换权限模式，并同步到当前运行状态。核心策略、CLI 入口和 TUI 入口均已接入统一配置；证据：`permission/access_mode.py`、`core/config_center.py`、`core/operation_guard.py`、`Cli.py`、`core/tui/screens/permission_screen.py`。

### D. TUI 输入、对话刷新与视图导航

- [x] `REQ-TUI-001` 修复当前对话框 Backspace 按键行为，使其恢复正常文本编辑功能。证据：`core/tui/app.py`、`tests/test_regression_baseline.py`。
- [x] `REQ-TUI-002` 同步刷新 LLM 对话窗口中的用户 `#X`、系统、状态与助手 `#X` 显示。证据：`core/tui/screens/chat_view.py`、`core/tui/app.py`、`tests/test_tui_chat_view.py`。
- [x] `REQ-TUI-003` 实时刷新并显示思考过程/合规处理状态。证据：`core/kernel.py`、`core/tui/app.py`、`core/tui/screens/chat_view.py`、`tests/test_tui_chat_view.py`。
- [x] `REQ-TUI-004` 删除数字 `1-0` 快捷键直接切换视图的行为。证据：`core/tui/app.py`、`core/tui/i18n.py`、`Cli.py`、`README.md`、`tests/test_regression_baseline.py`、`tests/test_tui_entrypoint.py`。
- [x] `REQ-TUI-005` 改为通过一个按键呼出视图选择菜单。证据：`core/tui/app.py`、`core/tui/i18n.py`、`README.md`、`tests/test_tui_entrypoint.py`、`tests/test_regression_baseline.py`。
- [x] `REQ-TUI-006` 在 TUI 左上角与 `Change Theme` 同类的菜单中增加视图选择子菜单。证据：`core/tui/app.py`、`core/tui/app.tcss`、`tests/test_tui_entrypoint.py`。

### E. 配置持久化与运行时同步

- [x] `REQ-STATE-001` 统一 CLI/TUI/LLM 运行时状态同步，覆盖权限模式、实验协议、工具导入、当前视图、重启恢复与损坏配置安全降级。证据：`core/config_center.py`、`core/kernel.py`、`Cli.py`、`core/tui/app.py`、`core/tui/screens/experiment_screen.py`、`core/tui/screens/tool_screen.py`。

### F. 文档与用户提示覆盖

- [x] 实验配置存储位置/格式、LLM 新增实验配置流程：`README.md`、`docs/experiment_config_authoring.md`。
- [x] Python/R 工具存储位置/格式、LLM 编写工具规则、自动扫描导入流程且用户无需知道工具 ID：`README.md`、`docs/tool_authoring.md`、`core/tui/i18n.py`。
- [x] 权限模式区别、风险、CLI/TUI 切换入口和 FULL 确认要求：`README.md`、`Cli.py`、`core/tui/i18n.py`。
- [x] 新视图切换菜单方式、`p` 权限入口、数字键不直接切换视图、Backspace 修复后的输入行为：`README.md`、`Cli.py`、`core/tui/i18n.py`。

## 后续实现映射建议

后续每个实现任务应在变更说明中填写以下字段：

| 字段 | 填写要求 |
| --- | --- |
| 关联需求 ID | 例如 `REQ-TUI-001`，可多个 |
| 改动文件 | 只列出该任务实际改动文件 |
| 行为变化 | 描述用户可观察到的变化 |
| 验收方式 | 对应本文验收关注点和后续 Tester 验证方式 |
| 风险/回退 | 说明权限、LLM 写入、TUI 快捷键等高风险点的保护和回退策略 |

## 覆盖性确认

本清单已覆盖用户列出的 19 条明确要求：

- 实验指导器/实验配置/LLM：4 条（`REQ-EXP-001` 至 `REQ-EXP-004`）。
- Python/R 工具管理和算法目录：4 条（`REQ-TOOL-001` 至 `REQ-TOOL-004`）。
- 权限模式、CLI/TUI 入口与运行时切换：5 条（`REQ-PERM-001` 至 `REQ-PERM-005`）。
- TUI 输入、刷新状态、快捷键和菜单：6 条（`REQ-TUI-001` 至 `REQ-TUI-006`）。

当前清单已同步实现证据与用户文档覆盖；后续实现不得把任何需求合并到不可单独验证的隐含项中。
