# SuperMedicine

SuperMedicine 是模块化医学科研助手，包含独立 Python 运行时、CLI、OpenTUI、
Web、Desktop、可选平台适配器与科研插件，覆盖证据检索、论文、统计、规范核查、
绘图、权限和可审计执行。

<!-- BEGIN GENERATED: release-metadata -->
当前版本：**0.4.2b0**
<!-- END GENERATED: release-metadata -->

发布系列：**Beta0.4.2**

English: [README.md](README.md)

<a id="product"></a>
## 产品

独立核心是默认产品；OpenCode 与 Claude Code 适配器是可选层，不会重新定义核心
行为。

稳定能力包括：

- workspace、paper、experiment、experience 与日志工作流；
- 本地检索与已配置 LLM Provider；
- 强制启用的本地 RAG 与 Harness 生命周期；
- 可选 Alpha/Beta/Gamma/Delta Multi-Agent 与 checkpoint resume；
- 权限策略、审计、脱敏和路径安全；
- CLI、OpenTUI、Web、Desktop、Standalone 与平台适配器；
- Wheel、sdist、三个 Windows EXE 与版本化 Release ZIP。

机器可读能力清单见 [`feature_manifest.json`](feature_manifest.json)。

<a id="safety"></a>
## 安全边界

本项目仅辅助科研工作，不提供临床建议、诊断或治疗决策。使用前必须人工审查生成
的论断、引用、统计、图表与代码。

Harness 与 RAG 是必选能力，默认启用；所需存储或运行状态缺失、损坏、不可写时
必须 fail closed。Multi-Agent 可选：关闭时走 single-agent，开启时保留四角色
与断点恢复。

禁止提交 API key、患者数据、私有端点、权限审计日志或用户 workspace。

<a id="install"></a>
## 安装

要求：

- Python 3.10–3.13；
- OpenTUI 依赖需要 Node.js/npm；
- 真实 OpenTUI 运行时需要 Bun。

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
python -m pip install -e .
python install.py
```

普通用户直接运行无参数 `python install.py` 并使用交互向导。自动化、Release
归档、三个 EXE、payload、失败恢复与卸载说明统一见
[安装指南](docs/guides/INSTALL.md)。

OpenTUI 使用 `@opentui/core@0.4.3`：

```bash
npm ci
npm run opentui:smoke
```

默认 JavaScript 运行时是 Bun；高级诊断可通过
`SUPERMEDICINE_OPENTUI_JS_RUNTIME` 指向受支持的运行时可执行文件。

<a id="quickstart"></a>
## 快速开始

```bash
supermedicine --help
supermedicine init --provider openai --base-url https://api.openai.com/v1 \
  --api-key "$OPENAI_API_KEY" --model gpt-4o-mini
supermedicine workspace create demo
supermedicine run "总结证据" --workspace demo
supermedicine tui
supermedicine web
```

Provider 也可通过 `SM_LLM_PROVIDER`、`SM_LLM_BASE_URL`、
`SM_LLM_API_KEY`、`SM_LLM_MODEL` 或 `.supermedicine/config.yaml`
配置。诊断和日志必须脱敏密钥。

权限模式为 `strict`、`balanced` 和 `permissive`；所有模式仍执行 hard
limits 与显式 deny。使用 `permission`、`authorize`、`revoke` 查看或修改。

<a id="documentation"></a>
## 文档

- [文档总入口](docs/README.md)
- [安装](docs/guides/INSTALL.md)
- [入门](docs/guides/getting-started.md)
- [Web 与桌面界面](docs/guides/WEB.md)
- [架构](docs/architecture/ARCHITECTURE.md)
- [运行管线](docs/architecture/runtime-pipeline.md)
- [发布架构](docs/architecture/release-architecture.md)
- [质量门](docs/maintainers/quality-gates.md)
- [CI Workflow](docs/maintainers/ci-workflows.md)
- [安全政策](SECURITY.md)
- [贡献指南](CONTRIBUTING.md)
- [更新日志](CHANGELOG.md)

本地验证：

```bash
python scripts/maintainers/check_docs.py
python scripts/maintainers/sync_release_metadata.py --check
python -m ruff check .
python -m mypy core permission cli plugins agents adapters installer
python -m pytest tests -q --tb=short
```

<a id="license"></a>
## 许可证

SuperMedicine 使用 MIT License。捆绑依赖声明见
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
