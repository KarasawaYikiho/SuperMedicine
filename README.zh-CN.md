<p align="center">
  <img src="assets/logo.jpg" alt="SuperMedicine" width="200">
</p>

# SuperMedicine

<p align="center"><img src="assets/logo.jpg" alt="SuperMedicine" width="400"></p>

![Version](https://img.shields.io/badge/version-Beta0.4.2-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**语言：** [English](README.md) | 简体中文

SuperMedicine 是一个面向医学科研辅助的独立 Python 框架。它提供独立 CLI、Kernel、
受权限控制的插件执行、工作区和论文管理、本地 RAG 工具、医学写作/引文辅助、LLM
Provider 管理、日志报告、多 Agent 编排组件，以及基于 Textual 的中文终端 TUI。OpenCode
和 Claude Code 集成属于可选适配层，不是默认 Python 运行时的必需条件。

当前公开/发布标签：**Beta0.4.2**。Python 包 fallback 版本：**0.4.2b0**。

核心参考文档：

- [INSTALL.md](INSTALL.md) — 安装、Provider 配置、发布包布局、可选 R 支持和卸载行为。
- [ARCHITECTURE.md](ARCHITECTURE.md) — 微内核、插件、权限、适配器和仓库边界设计。
- [SECURITY.md](SECURITY.md) — 安全模型、密钥处理、医学使用限制和披露建议。
- [FUNCTION_MAP.md](FUNCTION_MAP.md) — 静态 callable 清单及其限制。
- [CHANGELOG.md](CHANGELOG.md) — 版本变更历史。

## 项目定位

SuperMedicine 是科研辅助软件，不是临床决策系统。它面向本地医学科研流程，用户应自行
控制配置、凭据、生成物、论文导入和工作区数据。插件、RAG、引文工具、统计原型、实验
指导器和 LLM 调用输出都需要具备资质的人工复核。

默认产品边界是独立 Python CLI/Kernel/TUI。`adapters/` 下的平台适配器只是核心之外的
附加层；除非某项能力已经实现并经过测试，否则不得把它描述为原生 OpenCode 或 Claude
Code 运行时能力。

## 功能摘要

- **独立 Python 核心** — CLI、Kernel、配置中心、事件总线、插件发现、会话状态、工作区
  状态和运行时权限执行。
- **权限控制操作** — 高风险路径使用 `PermissionEngine.check()`、`.supermedicine/policies/`
  下的策略文件和 JSONL 审计记录。
- **LLM Provider 管理** — 根据 `api_format`、Base URL、模型和密钥来源配置 OpenAI、
  Anthropic、OpenRouter 和自定义兼容网关。
- **科研工作区** — 显式工作区 ID、复制式论文导入、用户确认后的经验记录、工作区本地
  工具资产；CLI 不会隐式复用 TUI 最近工作区。
- **插件生态** — RAG、harness 监控、Python/R 工具原型、实验计算、医学写作清单和
  AMA/Vancouver 引文格式化。
- **中文 TUI** — Textual 界面覆盖对话、仪表盘、工作区、论文、经验、工具、对话历史、
  LLM、实验指导器、权限模式和日志报告页面。
- **自进化预览** — 仅在预览、显式确认、路径检查、权限检查和覆盖控制后生成
  Markdown/Python/R 产物。
- **多 Agent 组件** — 仓库内存在 alpha/beta/gamma/delta 角色、状态机和 checkpoint
  编排组件；外部平台 subagent 运行时不会仅凭适配器自动启动。

## 安装

需求：

| 需求 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.10 | 必需 |
| Git | 任意 | 克隆源码时必需 |
| pip | >= 21.0 | 安装 Python 包时必需 |
| R | >= 4.3 | 可选，用于 R survival 后端 |

从源码快速安装：

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
python Install.py
supermedicine status
```

`python Install.py` 会启动普通交互式安装器。向导会询问目标项目路径、`.supermedicine`
初始化、LLM Provider 信息、可选快捷方式/PATH/桌面 Exe 指引，以及最终确认。如果检测到
已有安装，交互流程会先询问更新或卸载；更新默认保留 `.supermedicine/config.yaml` 和用户
数据。

Windows 发布包可能包含 **SuperMedicineInstaller.exe**。无参数运行即可进入同样的控制台
向导，并额外执行发布 payload 释放。完整发布布局应把 `SuperMedicineInstaller.exe`、
`dist/SuperMedicine.exe`、`Install.py`、`installer/`、运行时包、资源和文档放在一起。不要
只把 `Install.py` 单独复制到其他目录运行。

安装后常用检查：

```bash
python Cli.py status
supermedicine diagnose
supermedicine llm list
supermedicine log location
```

虚拟环境、开发依赖、可选 R 支持、高级自动化参数、发布包释放示例和卸载细节见
[INSTALL.md](INSTALL.md)。

## 快速开始

安装后可使用 `supermedicine <command>`；在仓库根目录也可用 `python Cli.py <command>`。

```bash
supermedicine status
supermedicine diagnose
supermedicine workspace init --workspace demo --name "Demo Workspace"
supermedicine paper import ./paper.pdf --workspace demo --title "Paper Title"
supermedicine experience suggest --workspace demo --summary "Keep prompts short"
supermedicine tool scan --language python
supermedicine tool add --workspace demo --select 1
supermedicine experiment list
supermedicine experiment start --protocol western_blot_basic --session-id wb-demo
supermedicine log follow --session-id wb-demo --interval 1 --max-entries 20
supermedicine tui
```

带工作区作用域的 CLI 命令需要显式传入 `--workspace`；它们不会静默复用 TUI 最近工作区。

## 配置

本地项目状态保存在 `.supermedicine/` 下。主要本地配置文件是 `.supermedicine/config.yaml`；
它可能作为运行时/私有状态被忽略，并可包含本地 Provider 设置。真实凭据应放在环境变量、
私有配置、密钥管理器或 CI secrets 中。

环境变量和配置注意事项：

- `SM_CONFIG` 可覆盖配置文件路径。
- `SM_<KEY>` 形式的变量可覆盖配置键。
- Provider 密钥应使用 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`OPENROUTER_API_KEY`，
  或由 `api_key_env` 引用的自定义密钥变量。
- 被跟踪的默认策略文件是 `.supermedicine/policies/default.yaml`；运行时审计日志写入
  `.supermedicine/policies/audit.jsonl`。

## 权限

文件访问模式保存在 `.supermedicine/config.yaml`，由 CLI、TUI 和后续策略读取共享。

| 模式 | 行为 | 风险和限制 |
|------|------|------------|
| `conservative` | 默认模式。允许项目内路径；项目外读取可能需要提示；项目外写入、删除和执行默认拒绝，除非显式授权。别名包括 `sandbox` 和 `safe`。 | 推荐日常使用。可降低误删、过宽读取和未授权执行风险。 |
| `full` | 在显式确认后放宽 SuperMedicine 自身文件访问限制。 | 高风险。它只使用当前 OS 用户/进程权限，不会静默提权，也不会绕过 UAC、管理员要求、ACL 或其他操作系统控制。 |

CLI 入口：

```bash
supermedicine permission status
supermedicine permission roots
supermedicine permission authorize C:\path\to\allowed-dir
supermedicine permission revoke C:\path\to\allowed-dir
supermedicine permission mode conservative
supermedicine permission mode full --confirm-full
```

在 TUI 中，可通过侧边栏 `P 🛡️ 权限模式` 或全局快捷键 `P` 打开权限页。切换到 full
访问需要输入确认文本 `FULL`。

## 安全与医学使用边界

- SuperMedicine 用于科研辅助，不用于诊断、治疗、监管批准或临床决策支持。
- 论文导入是复制式操作，默认不会上传源文件。
- 论文在线补全和外部资源操作在已实现位置需要显式确认和权限检查。
- 经验学习只保存用户确认后的摘要，不保存原始对话。
- 诊断、日志报告和 LLM/Provider 视图会脱敏常见密钥载体，但用户仍不得公开原始日志、
  私有路径、患者数据、私有端点或凭据。
- 普通对话框、日志文本、README、issue 和命令历史都不是存放 API Key 或患者标识的安全位置。

完整策略见 [SECURITY.md](SECURITY.md)。

## 插件与科研工具

插件通过 `plugins/` 下的清单发现，并在适用位置通过 Kernel 和权限模型执行。

| 领域 | 当前范围 |
|------|----------|
| RAG | 本地 TF-IDF Provider 和 Provider 接口契约，包含结构化错误与密钥安全配置边界。 |
| Harness | 监控、审计、checkpoint 和质量评估辅助。 |
| 医学写作 | CONSORT、STROBE、PRISMA 和 STARD 检查清单辅助。 |
| 医学引文 | AMA 和 Vancouver 引文格式化辅助。 |
| Python/R 工具 | 原型统计、生存分析接口和可导入工作区的数据分析工具模板。 |
| 实验 | `plugins/experiments/` 下基于配置的实验指导器协议；WB 只是一个普通配置示例。 |

Python/R 工具编写遵循可扫描目录格式：`plugins/tools/<tool-directory>/`，包含
`tool.yaml` 清单和 `runner.py` 或 `runner.R`。用户可以扫描并导入，无需记住工具 ID：

```bash
supermedicine tool scan --language python
supermedicine tool add --workspace demo --select 1
```

## TUI

启动中文 Textual 终端工作台：

```bash
supermedicine tui
supermedicine tui --dry-run
```

`--dry-run` 只输出就绪信息，不启动交互界面。TUI 读取项目本地 `.supermedicine/`、
`workspaces/` 和 `plugins/` 状态。

全局快捷键：

| 按键 | 动作 |
|------|------|
| `Tab` | 在交互控件之间向前移动焦点。 |
| `Shift+Tab` | 在交互控件之间向后移动焦点。 |
| `Enter` | 提交当前焦点输入或确认所选操作。 |
| `M` | 打开主菜单，其中包含 `选择视图`、`切换主题`、`帮助` 和 `最大化/还原`。 |
| `P` | 打开权限模式视图。 |
| `Esc` | 退出最大化模式。 |
| `Q` | 退出 TUI。 |

主菜单可通过大写 `M` 或左上侧边栏入口 `≡ 菜单 (M)` 打开。菜单中的 `选择视图` 用于
切换视图，`切换主题`、`帮助`、`最大化/还原` 等次要操作也从 `M` 菜单进入；状态栏继续
显示 `LLM 状态` 和 `任务运行状态` 等信息。
全局字母快捷键按大写策略记录为 `M`、`P`、`Q`；输入框获得焦点时，小写文本和输入法
组合内容按普通输入保留。数字键 `1-0` 不是直接视图切换快捷键；当输入框获得焦点时，它们作为普通输入保留。
`Backspace`、`Ctrl+H` 和常见删除控制字节会交给输入框处理，不会被全局快捷键吞掉。

对话执行期间，状态栏显示 `Chat Processing`。只有主输入框会在请求成功或失败前被锁定；
其他页面控件仍可通过焦点导航和 `M` 菜单访问。动态 TUI 刷新是有清单的 targeted refresh，
不是全局文件 watcher 或轮询。当前代码清单覆盖 workspace、log、dashboard、tool、dialog
这些刷新 surface；它们会在进入/切换、点击刷新，或相关操作更新数据后重新读取状态。其他
动态 surface 如果出现陈旧显示，应先补充清单和证据，再做局部修复。

TUI 字符串清单只把 `User`、`System`、`Assistant`、`Error`、`Status`、`Output` 等英文重点
标签约束为单个首字母大写词，同时保留 Chinese-first 导航和页面标题；这不是一次完整的
英文化标题替换。

如需 TUI 视觉改版，`scripts/tui_preview_artifact.py` 可默认在用户 Downloads 目录生成文本
预览 artifact。该流程只记录预览元数据；它本身不生成图片，也不声称已获得用户批准。任何
实质视觉改版仍需要先产出预览并获得用户明确确认。

主要页面包括对话、仪表盘、工作区管理、论文管理、经验学习、工具管理、对话历史、LLM
管理、实验指导器、权限模式和日志报告。

## LLM Provider

初始化和 LLM 支持任务需要完整 Provider 配置：`provider`、`base_url`、`model`，以及
`api_key` 或 `api_key_env`。缺失字段会作为设置/Provider 错误报告，不会被当成成功。

| API 格式 | 默认 Base URL | 默认密钥环境变量 | 默认模型 |
|----------|---------------|------------------|----------|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` |

自定义 Provider 示例：

```bash
supermedicine llm add deepseek \
  --api-format openai \
  --base-url https://api.deepseek.com/v1 \
  --api-key-env DEEPSEEK_API_KEY \
  --model deepseek-chat \
  --set-current

supermedicine llm list
supermedicine llm show deepseek
supermedicine llm switch deepseek
```

真实凭据优先使用 `--api-key-env`。共享示例只应使用占位符。

## 日志与诊断

使用 `supermedicine diagnose` 查看密钥安全的配置、Provider 就绪状态、审计日志路径检查、
日志存储位置和修复建议。

日志报告默认保存在项目本地 `.supermedicine/logs/`；权限审计记录保存在
`.supermedicine/policies/audit.jsonl`。

```bash
supermedicine log location
supermedicine log location --session-id wb-demo
supermedicine log follow --session-id wb-demo --interval 1 --max-entries 20
supermedicine log follow --file session-wb-demo.json --once
```

`log follow` 会打印脱敏后的存储路径、刷新信息、行数限制和脱敏日志行。除非使用
`--once` 或迭代次数限制，它会持续运行直到被中断。TUI 日志报告页提供等价的刷新和自动
跟随行为。

## 多 Agent 与可选适配器

仓库包含 alpha、beta、gamma、delta Agent 角色，以及 Python 架构内部使用的状态机和
checkpoint 组件。

| 能力 | 独立核心 | OpenCode 附加层 | Claude Code 附加层 |
|------|----------|-----------------|--------------------|
| CLI init/status/run | 支持 | 可包装元数据 | 最小适配路径 |
| 权限引擎 | 支持 | 用于适配器操作 | 工具执行前使用 |
| 插件发现/执行 | 支持 | 元数据集成 | 非原生 |
| 原生平台工具调用 | 不需要 | 声明 tool mappings | 仅 `claude.invoke` |
| 原生 subagent 运行时 | 不适用 | 仅凭适配器不会启动 | 未实现 |

适配器元数据和技能位于 `adapters/`。这些文件必须保持无凭据，并且不应声称未实现的
外部运行时能力。

## 测试与本地质量门

开发和发布检查应使用维护者记录的项目质量命令。典型本地质量门包含依赖安装、lint、
打包 smoke 检查和测试套件：

```bash
pip install -e ".[dev]"
ruff check --select=E,F,W --ignore=E501 .
python -m pip wheel . --no-deps --wheel-dir .pytest-tmp/wheel-smoke
pytest tests/ -v
```

CLI 中也存在旧的 `supermedicine test` 命令路径，但发布工作应遵循上述维护质量门和 CI
打包 smoke 检查。

## Release 与版本信息

- 公开/发布标签：**Beta0.4.2**。
- Python 包 fallback 版本：**0.4.2b0**。
- 包元数据定义在 [pyproject.toml](pyproject.toml)。
- 版本历史记录在 [CHANGELOG.md](CHANGELOG.md)。
- 当前 debug 文档落实 pass 的 GitHub Wiki 发布证据已在架构跟踪文档中记录为远程 commit
  `d6a1e11`；本地仓库测试不能证明未来远程 Wiki 仍可访问或内容未变。
- 修复后的 Beta0.4.2 发布布局会把安装器入口、`installer` 包、运行时包、文档/模板和
  `dist/SuperMedicine.exe` 放在一起。
- 生成的构建产物、运行时日志、缓存、本地工作区、本地配置和桌面 Exe 文件不应提交。

## 已计划或审查中

已记录在私有/debug 计划笔记中、但尚未由已实现代码、测试、可跟踪发布文档或已记录外部
证据证明的事项，应视为 **planned/under review（已计划或审查中）**，而不是已完成。仍
属于外部或审批门控的事项包括：TUI 预览的用户批准、如明确要求图片时的 image/screenshot
预览输出、OS 级 IME 验证、会替换 Chinese-first 本地化的完整英文标题 sweep、完整且合法
安全的外部 OpenCode 对比/对齐计划，以及任何全仓库大范围重构。未来原生平台运行时桥接、
更广泛的自主仓库维护、临床验证，以及任何会绕过当前权限或操作系统控制的能力，都必须
先实现、评审并测试，文档才可以描述为已支持。

## 故障排查

| 问题 | 处理方式 |
|------|----------|
| `No module named 'yaml'` | 使用 `pip install -e .` 安装依赖，或安装 `pyyaml`。 |
| 找不到 `supermedicine` 命令 | 将 Python Scripts 目录加入 PATH，或使用 `python Cli.py`。 |
| 初始化因 LLM 字段缺失失败 | 提供 provider、Base URL、model 和 API key 来源。 |
| `ModuleNotFoundError: No module named 'installer'` | 从完整源码/发布目录运行；不要只复制 `Install.py`。 |
| 发布包缺少 `SuperMedicine.exe` | 重新下载或重新生成包含 `dist/SuperMedicine.exe` 的完整发布包。 |
| TUI 启动异常 | 先运行 `supermedicine tui --dry-run`，必要时重启终端。 |
| 自进化没有写文件 | 默认是预览；写入需要 `--no-preview --confirm-write` 且输出路径位于允许根目录。 |
| 日志页没有跟随最新记录 | 在 TUI 日志报告页重新启用自动跟随，或刷新列表。 |

## 许可证

MIT License — 详见 [LICENSE](LICENSE)。
