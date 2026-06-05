# SuperMedicine

![Version](https://img.shields.io/badge/version-Beta0.4.1-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

SuperMedicine is an independent Python framework for medical research assistance.
It combines a microkernel, permission-gated plugin execution, RAG utilities,
medical writing/citation helpers, workspace management, paper import, experience
learning, and a Chinese terminal UI. OpenCode and Claude Code integrations are
optional add-ons; the Python CLI and Kernel are the default supported runtime.

Public/release label: **Beta0.4.1**. Python package fallback version:
**0.4.1b0**.

For detailed setup, see [INSTALL.md](INSTALL.md). For design boundaries, see
[ARCHITECTURE.md](ARCHITECTURE.md). For security and medical-use limits, see
[SECURITY.md](SECURITY.md). Repository-callable inventory is kept in
[FUNCTION_MAP.md](FUNCTION_MAP.md) because `docs/` is ignored in this repository.

## 中文简介

SuperMedicine 是一个面向医学科研辅助的独立 Python 框架，默认通过本项目的
CLI、Kernel、插件系统和中文 TUI 运行，不依赖 OpenCode、Claude Code 或其他
助手平台。平台适配器仅作为可选扩展。

主要能力：

- 工作区管理、论文导入、经验学习和工具管理。
- RAG 检索、实验指导/日志、Python/R 统计原型接口。
- CONSORT、STROBE、PRISMA、STARD 检查表，以及 AMA/Vancouver 引文格式化。
- P0 权限引擎、审计日志、日志/诊断脱敏和密钥过滤。
- LLM Provider 管理，支持 OpenAI 格式、Anthropic 格式、OpenRouter 以及兼容网关。

使用前请配置至少一个完整 LLM Provider（provider、base URL、model 和 API key
来源）。真实密钥应放在环境变量、私有配置或密钥管理器中，不要提交到仓库。

## Feature Summary

- **Standalone Python Core** — CLI, Kernel, configuration, plugin discovery, and
  runtime execution work without platform-specific assistant runtimes.
- **Permission-Gated Execution** — high-risk actions pass through
  `PermissionEngine.check()` and are written to audit logs.
- **LLM Provider Management** — built-in defaults for OpenAI, Anthropic, and
  OpenRouter plus custom compatible providers by API format.
- **Research Workspaces** — explicit workspace ids, copy-only paper import,
  user-confirmed experience records, and local tool templates.
- **Chinese TUI** — Textual-based terminal interface for chat, dashboard,
  workspace, paper, experience, tool, dialog history, LLM, experiment guide, and
  log report screens.
- **Medical Research Helpers** — RAG, harness monitoring, prototype statistics,
  reporting checklists, and citation formatting.

## Installation

Requirements:

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | >= 3.10 | Required |
| Git | Any | Required for cloning |
| pip | >= 21.0 | Required for package install |
| R | >= 4.3 | Optional, for R survival backend |

Quick install:

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
python install.py
supermedicine status
```

`python install.py` opens a concise four-step installer wizard. The legacy
`python Install.py` command remains compatible for older scripts. Ordinary users
should run the command with no flags and answer the questions on screen:

1. **安装/项目路径** — where `.supermedicine` and local project state are written;
   press Enter to use the current directory.
2. **初始化 .supermedicine 配置** — usually choose the default **yes**, then enter
   Provider, Base URL, Model, and API key. Provider defaults to `openai`; Base URL
   must be an `http(s)` URL; API key input is hidden in a real terminal.
3. **可选快捷入口** — shortcut/PATH prompts only record or display guidance. The
   Desktop Exe copy is optional and asks for an existing `SuperMedicine.exe` path
   only if you choose yes.
4. **确认安装** — review the summary, start installation, or return to edit answers.

Windows release artifacts also include **SuperMedicineInstaller.exe**. Double-click
it or run it from a terminal with no flags for the same console wizard. In the Exe
build, the first step defaults to releasing the full bundled program payload into
the target directory you choose. The extracted payload includes the main app Exe at
`dist/SuperMedicine.exe`, `install.py`, `Install.py`, configuration/documentation
templates, Python packages, and required resources. Keep the release archive/layout
intact; do not copy only `Install.py` or `install.py` elsewhere.

After installation, verify with:

```bash
python Cli.py status
supermedicine diagnose
```

The release package must be kept as a complete extracted directory. CI publishes
the installer-usable application executable at `dist/SuperMedicine.exe` inside
the archive and the standalone installer at `SuperMedicineInstaller.exe`. The
Windows packaging smoke installs PyInstaller in CI, builds both executables, runs
`SuperMedicineInstaller.exe --help`, and dry-runs payload extraction. Local
verification may rely on that CI/package smoke when PyInstaller is not installed.
The installer also supports local `Dist/SuperMedicine.exe` and a root-level
`SuperMedicine.exe` for compatibility. Run `Install.py` from the extracted root
that also contains `installer/__init__.py`, `installer/exe_release.py`, and the
executable/resources. Do not copy only `Install.py` out of the archive.
If you see `ModuleNotFoundError: No module named 'installer'` at a path like
`C:\Users\<you>\Downloads\SuperMedicine.Beta0.4.1\SuperMedicine Beta0.4.1\Install.py`,
the archive is likely incomplete or from an older broken release; re-download the
fixed Beta0.4.1 package or run from a complete source/release directory.
If `SuperMedicine.exe` is missing, the installer reports the requested file,
every searched path, and instructs you to regenerate the CI/local package.

### Advanced automation / CI flags

The following flags are for scripted installs, packaging smoke checks, and CI. They
are not required for normal interactive use. `python install.py --init` keeps its
existing core initialization behavior and does not copy a desktop executable unless
`--release-exe` is explicitly supplied. Use `python install.py --init
--interactive` only when you specifically want the LLM-only prompt in init mode.
For automation, CI, or dry runs, provide the LLM settings explicitly and use a
temporary desktop directory or dry-run mode so the real user Desktop is not
modified:

```bash
python install.py --unified-install --release-exe dist/SuperMedicine.exe \
  --desktop-dir .pytest-tmp/Desktop \
  --exe-dry-run \
  --provider openai \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini
```

Use `python Cli.py status` if the `supermedicine` console script is not on PATH.
For virtual environments, development dependencies, optional R support, and
platform-specific notes, see [INSTALL.md](INSTALL.md).

## LLM Provider Configuration

Initialization and LLM-backed tasks require a complete provider configuration:
`provider`, `base_url`, `model`, and either `api_key` or `api_key_env`.
SuperMedicine reports explicit setup or provider errors instead of pretending a
missing provider succeeded.

Supported API formats:

| API Format | Default Base URL | Default Key Env | Default Model |
|------------|------------------|-----------------|---------------|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` |

Custom providers such as DeepSeek, 智谱 GLM, local Ollama-compatible endpoints,
or private gateways can be configured in the `python install.py` wizard by entering
their provider name, Base URL, and model when prompted. The installer infers
OpenAI-compatible request format for custom providers; use `supermedicine llm add
--api-format ...` later if you need to override the format explicitly.

Example:

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

Prefer `--api-key-env` for real credentials. Documentation examples use
placeholders only.

## CLI Reference

All commands can be run as `supermedicine <command>` or `python Cli.py <command>`.

```bash
supermedicine status
supermedicine diagnose
supermedicine run "summarize local context" [--workspace <slug>]
supermedicine tui
```

Workspace, paper, experience, tool, experiment, log, and LLM management commands
use explicit flags and redacted output where appropriate:

```bash
supermedicine workspace init --workspace demo --name "Demo Workspace"
supermedicine paper import ./paper.pdf --workspace demo --title "Paper Title"
supermedicine experience suggest --workspace demo --summary "Keep prompts short"
supermedicine tool init --workspace demo
supermedicine experiment start --protocol wb --session-id wb-demo
supermedicine log list
supermedicine llm list
```

Workspace-scoped CLI commands do not silently reuse the TUI's recent workspace.
CLI commands always require explicit `--workspace`.

### 实验配置与 LLM 新增流程

实验指导器配置统一保存在项目插件目录 `plugins/experiments/`，文件格式可为
`.yaml`、`.yml` 或 `.json`。每个配置至少包含 `protocol_id`、`title`、
`description` 和非空 `steps`；每个步骤至少包含唯一 `step_id` 与 `title`。
可选字段包括 `version`、`metadata.aliases`、步骤 `instructions`、
`input_fields`、`calculation_requests` 和 `expected_outputs`。启动或列出实验时，
系统会扫描该目录内的 YAML/JSON 配置并按协议 ID/别名选择。

让 LLM 新增实验配置时，不需要手写完整文件路径。先用
`supermedicine experiment context --protocol <id-or-alias>` 查看当前会注入 LLM 的实验
上下文和编写规则，然后把自然语言需求交给规范化写入入口：

```bash
supermedicine experiment add-config --instruction "细胞迁移实验：记录划痕、培养条件、拍照时间点和复核结果"
```

如果 LLM 已生成 JSON 对象，也可使用 `--config-json` 保存。保存前会校验 schema、
协议 ID/别名冲突、安全文件名和目录可写性；默认不会覆盖同名配置，只有显式使用
`--overwrite` 才允许覆盖。新增成功后，该实验会同步为后续 LLM 上下文的当前实验。
详细格式以本节说明和仓库内实验配置文件为准；若本地开发副本包含被 `.gitignore`
忽略的 `docs/experiment_config_authoring.md`，该文件仅作为本地扩展说明，不作为发布包
必需文件。

### Python/R 工具编写、扫描与导入

可被自动扫描的 Python/R 工具源码统一放在 `plugins/tools/<tool-directory>/`。
每个工具目录需要 `tool.yaml` 清单和匹配语言的入口脚本 `runner.py` 或 `runner.R`
（也可在 `tool.yaml` 的 `entrypoint` 指向同目录内其他相对脚本）。清单字段包括：
`id`、`language`（`python` 或 `r`）、`name`、`description`、`entrypoint`、
`dependencies`、`inputs`、`outputs` 和 `version`。导入到某个工作区后，工具会复制到
`workspaces/<id>/tools/python/<tool-id>/` 或 `workspaces/<id>/tools/r/<tool-id>/`，并写入
规范化后的 `tool.yaml`。

让 LLM 编写工具时，请直接要求它“在 `plugins/tools/<tool-directory>/` 下生成
`tool.yaml` 与 `runner.py`/`runner.R`，输入输出路径保持在工作区内，依赖写入
`dependencies`，不要嵌入密钥或未授权网络访问”。Kernel 会向 LLM 注入与扫描器一致的
工具编写规范。更完整的字段、错误处理和安全边界见
本节说明和 `tool.yaml` 清单是发布包内的稳定参考；若本地开发副本包含被 `.gitignore`
忽略的 `docs/tool_authoring.md`，该文件仅作为本地扩展说明，不作为发布包必需文件。

用户导入工具不需要事先知道工具 ID：

```bash
supermedicine tool scan --language python
supermedicine tool add --workspace demo --select 1
```

`tool scan` 会自动扫描 `plugins/tools/*`，读取 `tool.yaml`（仅在缺失时回退读取
`plugin.yaml` 并给出警告），校验语言、入口脚本、依赖/输入/输出列表等格式，然后显示
带编号的候选列表。`tool add` 可用候选编号或扫描结果显示的 `language/id` 选择导入；
不提供 `--select` 时会返回可选候选列表。TUI“工具管理”页同样先点“扫描候选”，在表格中
选择候选行后点“添加工具”，无需输入或记忆工具 ID。真实工具运行仍只准备受保护调用，
并受权限策略、沙箱与审计约束。

### 权限模式、风险与切换入口

文件访问权限模式保存在 `.supermedicine/config.yaml` 的统一配置中，CLI、TUI 与后续
权限策略读取同一状态；切换后后续策略读取即时生效。

| 模式 | 行为 | 风险/限制 |
|------|------|-----------|
| 保守模式（`conservative`，也接受 `sandbox`/`safe` 别名） | 默认模式。允许项目内路径；项目外只读通常需要提示；项目外写入、删除、执行默认拒绝。可用外部授权目录放行特定目录。 | 最适合日常使用，能降低误删、越界读取和未授权执行风险。 |
| 完全访问（`full`） | 放宽 SuperMedicine 自身的文件访问限制，但仍只使用当前进程/当前用户已经拥有的系统权限。 | 高风险：可能访问或修改更大范围文件。它不会静默提权、不会绕过操作系统权限；系统权限不足时仍需管理员身份、UAC 或操作系统安全提示显式授权。切换必须显式确认。 |

CLI 入口：

```bash
supermedicine permission status
supermedicine permission roots
supermedicine permission authorize C:\path\to\allowed-dir
supermedicine permission revoke C:\path\to\allowed-dir
supermedicine permission mode conservative
supermedicine permission mode full --confirm-full
```

交互终端中未提供 `--confirm-full` 时，切换到 full 会要求输入 `FULL`；自动化场景可加
`--no-interactive`，此时切换 full 必须同时提供 `--confirm-full`。TUI 入口为侧边栏
“P 🛡️ 权限模式”或全局快捷键 `p`：可查看当前模式、风险提示、外部授权目录，切换 full
同样必须在确认输入框输入 `FULL`。

## TUI（中文终端工作台）

启动方式：

```bash
supermedicine tui
supermedicine tui --dry-run
```

`supermedicine tui` 会打开 Textual 交互界面；`--dry-run` 只输出
`TUI 基础组件已就绪（未启动交互界面）` 等就绪信息，适合安装后自检或终端兼容性排查。
TUI 读取当前项目目录下的 `.supermedicine`、`workspaces/`、`plugins/` 等本地状态；CLI
仍然不会隐式复用 TUI 最近工作区，脚本命令需要显式传入 `--workspace`。

按 `m` 可呼出左上角主菜单，在“选择视图”子菜单中列出并切换可用视图；同一菜单保留 `Change Theme` 主题切换入口。视图也可在侧边栏通过方向键选择并按 `Enter` 激活。数字键 `1-0` 不作为直接切换视图快捷键，焦点在输入栏时会作为普通输入处理。按 `p` 可直接进入“权限模式”视图。

对话输入栏中 `Backspace`、`Ctrl+H` 和常见 DEL/退格控制字节会交给输入组件执行删除，不再被终端控制序列过滤或全局快捷键吞掉；数字、普通文本和中文输入也会保留为普通输入。按 `m` 时仍会打开菜单，不会插入到输入框。

全局快捷键：

| Key | Action |
|-----|--------|
| `m` | 打开主菜单，可进入“选择视图”子菜单或 `Change Theme` |
| `p` | 打开权限模式视图，查看/切换访问模式与外部授权目录 |
| `f` | 最大化/还原当前焦点组件 |
| `Esc` | 退出最大化 |
| `?` | 打开快捷键帮助 |
| `q` | 退出 TUI |

使用 `Tab`/`Shift+Tab` 在输入框、按钮和列表之间移动焦点，`Enter` 提交输入或激活当前项。
工作区页支持 `Ctrl+N` 聚焦“工作区 ID”输入框。API Key 输入框会隐藏内容；普通对话输入框不是密钥输入控件，请不要粘贴真实密钥。

主要功能模块：

| 模块 | 用途 | 关键注意事项 |
|------|------|--------------|
| 对话 | 在输入栏提交任务，由 Kernel 调用插件/LLM 执行 | 长任务期间状态栏显示 `任务执行中`。 |
| 仪表盘 | 查看初始化、工作区、插件、LLM 与 Token 统计概览 | 会给出“请先运行初始化流程”等操作建议。 |
| 工作区管理 | 创建、选择、删除 `workspaces/<id>` | 删除需输入完全一致的工作区 ID 并经过权限策略确认。 |
| 论文管理 | 复制导入 PDF/TeX/BibTeX/RIS/TXT/MD，查看和补全元数据 | 在线补全会发起网络请求，需显式确认。 |
| 经验学习 | 建议分类、确认写入、查看/删除经验摘要 | 建议分类不会自动写入；不保存原始对话。 |
| 工具管理 | 初始化工作区 Python/R 工具目录，添加或查看工具模板 | 真实工具运行仍受权限、沙箱与审计边界约束。 |
| 对话历史 | 查看审计友好的对话事件摘要 | 展示前会隐藏敏感内容。 |
| LLM 管理 | 添加/更新、切换、查看 Provider | 状态栏和通知不会显示 API Key。 |
| 实验指导器 | 按已选择的实验配置逐步记录实验辅助信息；WB 只是普通配置示例之一，支持切换到其他实验配置 | 仅供科研记录与实验辅助，保存日志前会脱敏。 |
| Log 报告 | 保存、列出和查看脱敏日志报告 | 敏感信息会在保存和展示前自动脱敏。 |

Status Cues include workspace count and current focus on the left, plugin count,
LLM status, and task running state in the center, and current view/version on the
right. **LLM 状态** shows provider readiness without exposing API keys, and
**任务运行状态** appears as `任务空闲` or `任务执行中` for long-running work.

安装后的 Desktop Exe 释放行为：

- `python install.py --init` 和 `supermedicine init` 默认只初始化核心配置，不会复制桌面 Exe。
- 只有显式传入 `--release-exe <path-to-SuperMedicine.exe>` 时才会释放桌面 Exe。
- `python install.py --unified-install --release-exe <path>` 会先初始化 `.supermedicine`，再执行桌面 Exe 释放；缺少 `--release-exe` 会报错。
- 默认目标位置是用户 Desktop，目标文件名默认使用源 Exe 文件名；可用 `--desktop-dir` 指定目录，用 `--exe-target-name` 指定目标文件名（会规范为 `.exe`）。
- 如果目标文件已存在，默认跳过；使用 `--exe-overwrite` 才会覆盖；使用 `--exe-dry-run` 只报告动作不复制文件。
- 测试、CI 或文档演示应使用 `--desktop-dir <tmp>` 或 `--exe-dry-run`，避免修改真实桌面。

安装 Exe 程序文件释放行为：

- CI 产物包含独立 `SuperMedicineInstaller.exe`，用于把完整发布 payload 释放到用户选择目录。
- 安装 Exe 与 `python install.py --extract-release-to <dir>` 共用 `installer/exe_release.py` 的发布布局解析/释放逻辑。
- 释放后的目录应包含 `dist/SuperMedicine.exe`、`install.py`、`Install.py`、`installer/`、`core/`、`permission/`、配置/文档模板和必要资源。
- `Install.py` 的交互式流程继续负责 `.supermedicine` 初始化、LLM 配置和可选桌面 Exe 复制；如果需要在一次自动化调用中完成释放和配置，可把 `--extract-release-to <dir>` 与 `--init --project-dir <dir>` 组合使用。
- 自动化或 smoke 检查必须指向 staged release payload，而不是缺少生成产物的源码根目录；该 payload 需包含 `dist/SuperMedicine.exe`。例如：`python install.py --extract-release-to .pytest-tmp/Installed --release-payload-root .installer-payload-stage/release_payload --exe-dry-run`。

## Platform Adapters

Platform adapters live under `adapters/` and are optional:

| Capability | Standalone Core | OpenCode Add-on | Claude Code Add-on |
|------------|----------------|-----------------|-------------------|
| CLI init/status/run | Supported | Can wrap metadata | Minimal adapter path |
| Permission engine | Supported | Used for adapter operations | Used before tool execution |
| Plugin discovery/execution | Supported | Metadata integration | Not native |
| Native platform tool calls | Not required | Declared tool mappings | `claude.invoke` only |
| Native subagent runtime | Not applicable | Not launched by adapter alone | Not implemented |

## Architecture Overview

```text
CLI / TUI / Optional Adapters
        |
        v
Kernel: ConfigCenter + EventBus + PluginRegistry + SessionManager + PermissionEngine
        |
        +--> Agents and orchestration state machine
        +--> Plugins: RAG, harness, tools, standards
        +--> Workspace layer: papers, experience, local tool assets
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the root architecture reference.

## Function Map and External Reference Fusion

- [FUNCTION_MAP.md](FUNCTION_MAP.md) is the visible, trackable callable inventory.
  It is generated from static Python AST analysis and documents limitations around
  dynamic dispatch, decorators, CLI callbacks, Textual callbacks, plugin registries,
  and tests. It must not contain credentials, environment values, private
  endpoints, or raw logs.
- External project ideas, including OpenCode-style TUI/CLI experience patterns,
  are treated as design references only. SuperMedicine does not copy external
  source code, does not require external assistant runtimes for the standalone
  core, and documents any optional adapter boundary before claiming support.
- Additional release-scope safety notes are in
  [SECURITY_HARDENING_CHECKLIST.md](SECURITY_HARDENING_CHECKLIST.md) and external
  reference boundaries are in [EXTERNAL_PROJECT_ANALYSIS.md](EXTERNAL_PROJECT_ANALYSIS.md).

## Diagnostics and Troubleshooting

Use `supermedicine diagnose` for secret-safe status, provider readiness, audit log
path checks, and repair suggestions.

Common Fixes:

| Issue | Fix |
|-------|-----|
| `No module named 'yaml'` | Install package dependencies with `pip install -e .` or install `pyyaml`. |
| `supermedicine` command not found | Add the Python Scripts directory to PATH or use `python Cli.py`. |
| Initialization fails with missing LLM fields | Provide provider, base URL, model, and API key source. |
| `python install.py` 问答不知道怎么填 | 路径可直接回车；初始化配置通常选 yes；Provider 可用 `openai` 或你的网关名称；Base URL 必须以 `http://` 或 `https://` 开头；Model 填服务商模型名；API key 粘贴后可能不显示，这是正常隐藏输入。 |
| LLM call fails | Treat it as a real provider/configuration error; run diagnostics and inspect redacted fields. |
| TUI launch issue | Run `supermedicine tui --dry-run`, then restart the terminal if needed. |
| TUI 操作无响应 | 确认焦点位置，先用 `Tab`/`Shift+Tab` 移动焦点；管理页按钮和列表需要 `Enter` 激活。 |
| 论文在线补全失败 | 检查是否选择工作区、输入论文 ID 并显式确认；该操作可能受网络/API/权限策略限制。 |
| 桌面 Exe 未出现 | 确认已提供 `--release-exe`，源 Exe 存在，目标未因已存在而跳过；必要时加 `--exe-overwrite` 或先用 `--exe-dry-run` 查看目标路径。 |
| Exe 释放失败 | 检查发布包是否包含 `dist/SuperMedicine.exe`（或本地 `Dist/SuperMedicine.exe`/根目录 `SuperMedicine.exe`）、`--desktop-dir` 是否可写、`--exe-target-name` 是否为安全文件名，以及杀毒/权限策略是否阻止复制。 |

## Local Quality Gate

For development and release checks, use the project Quality commands documented
by the maintainers. A typical Local Gate includes linting, packaging smoke checks,
and the test suite, for example:

```bash
pip install -e ".[dev]"
ruff check --select=E,F,W --ignore=E501 .
python -m pip wheel . --no-deps --wheel-dir .pytest-tmp/wheel-smoke
pytest tests/ -v
```

## Safety and Medical-Use Boundaries

- SuperMedicine is research-support software, not a clinical decision system.
- Plugin outputs, citations, RAG results, metadata enrichment, and prototype
  statistics require qualified human review.
- Paper import is copy-only and does not upload source files by default.
- Experience learning stores user-confirmed summaries, not raw conversations.
- Real credentials belong in environment variables, private local config, secret
  managers, or CI secrets, not committed files.
- 不要在普通对话输入、日志、经验摘要、README、issue 或命令历史中粘贴真实 API Key；优先使用 `--api-key-env` 或环境变量。
- 桌面 Exe 是外部发布产物，不应提交到源码仓库；安装器只在显式请求时复制用户提供的 Exe。

See [SECURITY.md](SECURITY.md) for the full policy.

## License

MIT License — see [LICENSE](LICENSE) for details.
