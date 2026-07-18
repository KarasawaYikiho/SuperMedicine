# SuperMedicine

<p align="center"><img src="assets/logo.jpg" alt="SuperMedicine" width="360"></p>

![Version](https://img.shields.io/badge/version-Beta0.4.2-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**语言：** [English](README.md) | 简体中文

SuperMedicine 是一个本地优先的 Python 医学科研辅助框架。它提供 CLI、
Kernel、权限引擎、插件运行、工作区和论文管理、LLM Provider 配置、本地
RAG、医学写作和引用辅助、实验/日志流程，以及中文 OpenTUI 终端界面。

SuperMedicine 不是临床决策系统。所有生成内容都只应作为科研辅助材料，并
由具备资质的人类使用者复核。

当前发布标签：**Beta0.4.2**。Python 包 fallback 版本：**0.4.2b0**。

## 强制 Harness 与 RAG 运行时

所有正式 CLI、TUI、Web、插件、LLM 与可选多 Agent 任务都进入同一 Kernel
管线。Harness 与 local-first RAG 是不可关闭的必需能力；配置、环境变量或插件
参数都不能绕过。必需组件缺失、损坏或存储不可写时以结构化错误 fail closed。

知识生成任务在生成前检索证据；空索引明确报告 `rag.status=empty`，不得伪造
来源。确定性和控制动作记录枚举化 `skipped` 原因。PubMed 始终经过权限检查，
被拒绝时降级使用本地证据。多 Agent 默认 `agents.mode: single`，启用后仍使用
同一 Harness、RAG、权限、审计与结果封装。

## 先读这些

- [安装指南](docs/guides/INSTALL.md)
- [架构概览](docs/architecture/ARCHITECTURE.md)
- [安全策略](SECURITY.md)
- [贡献指南](CONTRIBUTING.md)
- [变更记录](CHANGELOG.md)

## 功能范围

| 模块 | 范围 |
| --- | --- |
| CLI 和 Kernel | 命令分发、配置、事件总线、插件路由、会话和权限检查。 |
| 权限 | 默认保守模式，完整访问需要明确确认，并写入审计记录。 |
| 工作区 | 工作区、论文、工具、经验命令都使用显式 `--workspace`。 |
| LLM Provider | 支持 OpenAI、Anthropic、OpenRouter 和 OpenAI-compatible 自定义端点。 |
| 插件 | RAG、harness、医学写作、引用格式、实验辅助、Python/R 工具模板和图表工具。 |
| TUI | 基于 Bun 和 `@opentui/core@0.4.1` 的中文 OpenTUI 终端界面。 |
| 可选适配器 | `adapters/` 下包含 OpenCode 和 Claude Code 的元数据/适配器文件；独立 Python 运行时不依赖它们。 |

## 从源码安装

需求：

- Python 3.10 或更高版本
- Git
- pip
- Bun 和 npm，用于 OpenTUI
- R 4.3 或更高版本，仅在使用可选 R survival 后端时需要

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
python -m pip install -e .
npm ci
python install.py
supermedicine status
```

开发依赖：

```bash
python -m pip install -e ".[dev]"
```

OpenTUI smoke 检查：

```bash
npm run opentui:smoke
```

## 发布包布局

Windows 发布包应保持完整目录结构，不能只复制单个安装脚本。关键文件包括：

- `SuperMedicineInstaller.exe`
- `dist/SuperMedicine.exe`
- `install.py`
- `install_entry.py`
- `uninstall_entry.py`
- `installer/`
- `package.json`
- `package-lock.json`
- `THIRD_PARTY_NOTICES.md`
- `docs/guides/INSTALL.md`

这些入口会导入同级 Python 包和资源，因此 release archive 应整体解压运行。

## 快速命令

```bash
supermedicine status
supermedicine diagnose
supermedicine workspace init --workspace demo --name "Demo Workspace"
supermedicine paper import ./paper.pdf --workspace demo --title "Paper Title"
supermedicine experience suggest --workspace demo --summary "Keep useful prompts short"
supermedicine tool scan --language python
supermedicine tool add --workspace demo --select 1
supermedicine experiment list
supermedicine experiment start --protocol western_blot_basic --session-id wb-demo
supermedicine log follow --session-id wb-demo --interval 1 --max-entries 20
supermedicine tui
```

涉及工作区的 CLI 命令必须显式传入 `--workspace`，不会自动复用 TUI 最近工作区。

## 配置和密钥

本地运行状态位于 `.supermedicine/`。

| 文件或变量 | 用途 |
| --- | --- |
| `.supermedicine/config.yaml` | 本地运行配置，应保持私有。 |
| `.supermedicine/policies/default.yaml` | 仓库跟踪的默认权限策略。 |
| `.supermedicine/policies/audit.jsonl` | 本地权限审计日志。 |
| `SM_CONFIG` | 覆盖配置文件路径。 |
| `SM_<KEY>` | 通过环境变量覆盖配置项。 |
| `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`OPENROUTER_API_KEY` | 常用 Provider 的推荐密钥来源。 |

真实密钥应放在环境变量、私有配置、密钥管理器或 CI secrets 中。公开示例只使用
`<OPENAI_API_KEY>` 这类占位符。

## 权限模式

| 模式 | 行为 |
| --- | --- |
| `conservative` | 默认模式。允许项目内访问；项目外写入、删除和执行需要显式授权或被拒绝。 |
| `full` | 在确认后放宽 SuperMedicine 自身检查。它只使用当前 OS 用户/进程已有权限，不绕过 UAC、ACL 或管理员要求。 |

```bash
supermedicine permission status
supermedicine permission roots
supermedicine permission authorize C:\path\to\allowed-dir
supermedicine permission revoke C:\path\to\allowed-dir
supermedicine permission mode conservative
supermedicine permission mode full --confirm-full
```

## TUI

启动中文 OpenTUI：

```bash
supermedicine tui
supermedicine tui --dry-run
npm run opentui:smoke
```

非 dry-run 路径通过 Bun 启动 `core/tui/opentui_runtime.mjs`，并使用固定依赖
`@opentui/core@0.4.1`。

常用快捷键：

| 按键 | 动作 |
| --- | --- |
| `Tab` | 焦点前移。 |
| `Shift+Tab` | 焦点后移。 |
| `Enter` | 提交当前输入或确认当前操作。 |
| `M` | 打开或关闭菜单。 |
| `P` / `Ctrl+P` | 打开权限视图。 |
| `Esc` / `B` | 从当前页面或菜单返回。 |
| `Q` | 退出 TUI。 |

数字键 `1-0` 不是直接视图切换快捷键；输入框获得焦点时它们仍是普通输入。

对话请求运行时，状态栏显示 `Chat Processing`。只会锁定主输入框，直到请求成功
或失败；其他屏幕控件仍可通过焦点导航和 `M` 菜单访问。动态刷新按页面和动作
定向触发，不是全局文件 watcher 或轮询。

当前测试仍保留部分历史编码兼容标记：`鏁板瓧閿?`1-0` 涓嶆槸鐩存帴瑙嗗浘鍒囨崲蹇嵎閿?`、
`鍙湁涓昏緭鍏ユ`、`watcher 鎴栬疆璇?`。

## LLM Provider

Provider 记录需要名称、API 格式、Base URL、模型，以及密钥或 `api_key_env`。

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

真实凭据优先使用 `--api-key-env`。

## 本地质量门

```bash
python -m pip install -e ".[dev]"
ruff check --select=E,F,W --ignore=E501 .
python -m pytest tests/test_repo_hygiene.py tests/test_release.py tests/test_maintainer_markdown_links.py
```

发布前运行更完整的测试：

```bash
python -m pytest tests/ -v
```

## 仓库卫生

Git 中应保留源码、测试、CI、包元数据、文档、默认策略和小型资源。不要提交构建
产物、缓存、本地工作区、日志、凭据、生成的 exe 或本地归档。历史归档材料应保留
在被忽略的 `Temp/`，不要放回 `docs/archive/`。

## 故障排查

| 现象 | 处理 |
| --- | --- |
| `No module named 'yaml'` | 运行 `python -m pip install -e .`。 |
| 找不到 `supermedicine` | 将 Python Scripts 目录加入 `PATH`，或运行 `python -m cli_entry`。 |
| TUI 无法启动 | 运行 `npm ci`，确认 Bun 在 `PATH`，再运行 `supermedicine tui --dry-run`。 |
| 发布包缺少 exe | 使用包含 `dist/SuperMedicine.exe` 的完整发布包。 |
| LLM 初始化失败 | 提供 provider、API format、Base URL、model 和 key source。 |

## 许可证

MIT。详见 [LICENSE](LICENSE)。

<!-- TUI compatibility markers: 只有主输入框 | watcher 或轮询 -->
