# SuperMedicine Installation Guide

This guide covers installation, initialization, provider configuration, optional
R support, platform adapter notes, troubleshooting, and uninstall behavior for
SuperMedicine **Beta0.4.1**. The Python package fallback version is **0.4.1b0**.

For a shorter overview, start with [README.md](README.md). For design and
security boundaries, see [ARCHITECTURE.md](ARCHITECTURE.md) and
[SECURITY.md](SECURITY.md). For release documentation hardening and maintainer
reading boundaries, see [SECURITY_HARDENING_CHECKLIST.md](SECURITY_HARDENING_CHECKLIST.md)
and [Architecture/MaintainerRepositoryReading.md](Architecture/MaintainerRepositoryReading.md).

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | >= 3.10 | Required |
| Git | Any | Required for cloning |
| pip | >= 21.0 | Required for installation |
| R | >= 4.3 | Optional, for R survival backend |

OpenCode, Claude Code, and other assistant platforms are optional add-ons, not
requirements for the standalone Python core.

## Quick Install

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
python install.py
python Cli.py status
```

`python install.py` starts a concise four-step installer wizard. The legacy
`python Install.py` command remains compatible for older scripts. Ordinary users
should not add complex `--` flags: run the command above and answer the prompts.
The wizard asks for the installation/project path, `.supermedicine` / LLM
initialization details, optional shortcut/PATH/Desktop Exe choices, and a final
confirmation summary. API key input is hidden. Defaults are shown in brackets,
blank required LLM values are rejected, Base URL is validated as an `http(s)`
address, and `.supermedicine/config.yaml` is written automatically.

普通用户推荐流程是：下载或克隆完整项目/发布包，进入包含 `Install.py` 的根目录，
直接运行 `python install.py`，按提示确认安装/项目路径并填写 LLM provider、BaseURL、
model 和 API key。不要只复制单个 `Install.py` 到其他目录；发布包内的 Python 包、
资源和可选 Exe 释放模块需要保持同一目录布局。

Release builds also publish **SuperMedicineInstaller.exe**, a standalone Windows
console installer Exe with the same streamlined prompts and help text. Ordinary
users can double-click it or run it with no flags. Because the Exe carries the
release payload, its first step defaults to extracting program files into the
chosen target directory; the later steps initialize `.supermedicine`, collect LLM
settings, show optional shortcut/PATH/Desktop Exe choices, and ask for final
confirmation. The installer Exe contains the same unified release layout as the
Zip: `install.py`, `Install.py`, the Python packages, documentation/config
templates, resources, and the application Exe at `dist/SuperMedicine.exe`.

For development tooling:

```bash
pip install -e ".[dev]"
```

Installation and initialization are intentionally LLM-complete. A provider must
have `provider`, `base_url`, `model`, and an API key source. The interactive wizard
asks for these values. Scripted/CI initialization may still pass flags,
environment variables, or `--llm-config` in the advanced automation section below.
If initialization fails, the installer restores the previous `.supermedicine/`
state or removes the partial directory.

## Step-by-Step Setup

### 1. Create a Virtual Environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### 2. Clone and Install

```bash
git clone https://github.com/KarasawaYikiho/SuperMedicine.git
cd SuperMedicine
pip install -e .
```

### 3. Initialize the Project

```bash
python install.py
```

This launches the installer wizard and creates local `.supermedicine/`
configuration when you confirm initialization. It does not require or create
OpenCode or Claude Code configuration.

If you launch `Install.py` from a release archive, keep the extracted directory
intact. The fixed Beta0.4.1 release layout places `Install.py` next to the
`installer/` package, including `installer/__init__.py` and
`installer/exe_release.py`, under the extracted root. CI release archives also
include the application executable at `dist/SuperMedicine.exe` and the standalone
installer executable `SuperMedicineInstaller.exe`. The installer searches the
requested path first, then `dist/SuperMedicine.exe`,
`Dist/SuperMedicine.exe`, and `SuperMedicine.exe` from the current/release root.
Copying only `Install.py` out of the archive can trigger `ModuleNotFoundError: No
module named 'installer'`; removing `dist/SuperMedicine.exe` causes a specific
missing-file error that lists every searched path and recommends regenerating the
release package. In either case, re-download the fixed complete package or run
the installer from a complete source/release directory.

### What the interactive questions mean

The no-flag installer asks these questions in order:

| Prompt | Meaning | Typical answer |
|--------|---------|----------------|
| `安装/项目路径` | Directory where local SuperMedicine state and, for the Exe installer, extracted files are placed. | Press Enter for the current directory, or enter a full path such as `C:\SuperMedicine`. |
| `释放完整程序文件到该目录` | Copy the bundled release payload into the target directory. | Source `python install.py` usually defaults to no; `SuperMedicineInstaller.exe` defaults to yes. |
| `初始化 .supermedicine 配置` | Create/update `.supermedicine/config.yaml`. | Choose the default yes for first install. |
| `Provider` | Provider name, such as `openai`, `anthropic`, `openrouter`, `deepseek`, or your gateway name. | Press Enter for `openai` if using OpenAI-compatible defaults. |
| `Base URL` | HTTP endpoint for the provider. It must start with `http://` or `https://`. | For OpenAI, `https://api.openai.com/v1`. |
| `Model` | Model name sent to the provider. | Example: `gpt-4o-mini`. |
| `API key` | Provider credential. Input is hidden in a real terminal and redacted in output. | Paste your key, or use a private environment/secret workflow. |
| `记录创建快捷方式意向` | Records that you want shortcut guidance; it does not create a platform shortcut automatically. | Usually no. |
| `显示 PATH 手动配置提示` | Prints PATH guidance for `supermedicine`. | Choose yes if the command is not found. |
| `复制 SuperMedicine.exe 到桌面` | Copies an existing app Exe to Desktop only when you choose yes and provide/accept an Exe path. | Usually no unless using a release package. |
| `开始安装` | Final confirmation after the summary. | Press Enter to install, or answer no to edit/cancel. |

### Advanced automation / CI initialization examples

The following examples are for non-interactive automation, CI, and packaging smoke
checks. They are not the recommended ordinary user path.

```bash
# CI/scripted core initialization without wizard
export OPENAI_API_KEY=<OPENAI_API_KEY>
python install.py --init --provider openai --base-url https://api.openai.com/v1 --model gpt-4o-mini

# Anthropic format
export ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY>
python install.py --init --provider anthropic \
  --base-url https://api.anthropic.com/v1 \
  --model claude-3-5-sonnet-latest

# Custom OpenAI-compatible provider
export DEEPSEEK_API_KEY=<DEEPSEEK_API_KEY>
python install.py --init --provider deepseek \
  --base-url https://api.deepseek.com/v1 \
  --model deepseek-chat

# OpenRouter gateway
export OPENROUTER_API_KEY=<OPENROUTER_API_KEY>
python install.py --init --provider openrouter

# LLM-only prompt for --init; API key input is hidden
python install.py --init --interactive
```

Automated environments should avoid the full wizard and pass deterministic flags
or environment variables instead. Use `--exe-dry-run` and temporary directories
for release actions so CI does not modify a real user Desktop:

```bash
python install.py --init \
  --provider openai \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --api-key-env OPENAI_API_KEY

python install.py --release-exe dist/SuperMedicine.exe \
  --desktop-dir .pytest-tmp/Desktop \
  --exe-dry-run
```

### Standalone Windows Installer Exe

Download the CI/GitHub Release Zip and run `SuperMedicineInstaller.exe` on
Windows. With no flags, it presents the same simple four-step console wizard. This
is the normal Exe path; do not add automation flags unless you are scripting a CI
or unattended install.

1. Choose the target directory and whether to extract program files.
2. Initialize `.supermedicine` and enter LLM provider, Base URL, model, and API key.
3. Choose optional shortcut/PATH guidance and Desktop Exe copy.
4. Review the summary and start installation.

It extracts the complete program payload into the directory you choose:

- `dist/SuperMedicine.exe` — main application Exe.
- `install.py` — canonical Python interactive/configuration installer.
- `Install.py` — legacy-compatible Python installer entrypoint.
- `core/`, `permission/`, `installer/`, `agents/`, `plugins/`, `adapters/` —
  runtime packages and resources.
- `README.md`, `INSTALL.md`, `install.json`, and other documentation/templates.

The two installer entry points share the same interactive question flow but have
different packaging responsibilities:

- **SuperMedicineInstaller.exe** carries the release payload and therefore defaults
  the first-step extraction question to yes.
- **python install.py** is the canonical Python entrypoint and usually runs from an
  already extracted source/release directory, so extraction defaults to no unless
  requested.
- Both can initialize `.supermedicine`, configure LLM provider settings, and offer
  optional Desktop Exe copy during the no-flag wizard.

CI/GitHub Release artifacts should preserve this structure when uploaded or
unzipped: `SuperMedicineInstaller.exe` at the release root, the application Exe at
`dist/SuperMedicine.exe`, and the shared payload (`install.py`, `Install.py`, `installer/`,
`core/`, `permission/`, docs/templates/resources). `install.py --release-exe`
uses the packaged `dist/SuperMedicine.exe` path by default when the flag is passed
without a value; `SuperMedicineInstaller.exe` and `install.py --extract-release-to`
use the same payload extraction contract.

Executable build/run verification is CI-backed: the Windows packaging smoke job
installs PyInstaller, builds `dist/SuperMedicine.exe` and
`dist/SuperMedicineInstaller.exe`, runs `SuperMedicineInstaller.exe --help`, and
dry-runs installer payload extraction. Local checks can use the CI/package smoke
result as the fallback when PyInstaller is not installed on the developer machine.

#### Advanced Exe automation

The commands below are for automated release smoke checks and unattended installs,
not for ordinary users.

Automation can exercise the same extraction logic without writing files. Point
`--release-payload-root` at a staged release payload that includes the generated
`dist/SuperMedicine.exe`; do not point it at the source tree root before the Exe
artifact has been staged:

```bash
python install.py --extract-release-to .pytest-tmp/Installed \
  --release-payload-root .installer-payload-stage/release_payload \
  --exe-dry-run
```

To perform extraction and project configuration in one non-interactive command,
target the same directory for both stages:

```bash
SuperMedicineInstaller.exe --extract-release-to C:\SuperMedicine \
  --init --project-dir C:\SuperMedicine \
  --provider openai \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --api-key-env OPENAI_API_KEY
```

Use `--extract-overwrite` only when you intentionally want to replace existing
files in the target directory. The extraction path and the `--release-exe` desktop
copy path share `installer/exe_release.py`, so CI, the Python installer, and the
standalone installer Exe use one release-layout contract.

Use placeholders in shared examples. Replace them only in private shells, secret
managers, CI secrets, or untracked local files.

## LLM Provider Management

Provider names are flexible. The `api_format` decides which HTTP protocol is used:

| API Format | Default Base URL | Default Key Env | Default Model |
|------------|------------------|-----------------|---------------|
| `openai` | `https://api.openai.com/v1` | `OPENAI_API_KEY` | `gpt-4o-mini` |
| `anthropic` | `https://api.anthropic.com/v1` | `ANTHROPIC_API_KEY` | `claude-3-5-sonnet-latest` |
| `openrouter` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` | `anthropic/claude-3.5-sonnet` |

Add, inspect, and switch providers through the CLI:

```bash
supermedicine llm add openai \
  --api-format openai \
  --base-url https://api.openai.com/v1 \
  --api-key-env OPENAI_API_KEY \
  --model gpt-4o-mini \
  --set-current

supermedicine llm add anthropic \
  --api-format anthropic \
  --base-url https://api.anthropic.com/v1 \
  --api-key-env ANTHROPIC_API_KEY \
  --model claude-3-5-sonnet-latest

supermedicine llm list
supermedicine llm show openai
supermedicine llm switch anthropic
```

`supermedicine llm switch <provider>` validates required fields, persists the
current provider, and records `last_provider` for startup restore.

### Manual YAML Configuration

You may edit `.supermedicine/config.yaml` directly. Prefer environment variable
references over plaintext keys:

```yaml
llm:
  provider: openai
  last_provider: openai
  providers:
    openai:
      provider: openai
      api_format: openai
      base_url: https://api.openai.com/v1
      api_key_env: OPENAI_API_KEY
      model: gpt-4o-mini
```

Then set the environment variable outside the repository:

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>
```

### TUI Configuration

Run `supermedicine tui`, open **LLM 管理**, enter provider name, BaseURL, model,
API Key, and optional API format, then add or switch the provider. Key fields are
password-style and cleared after submission.

## Optional R Support

```bash
pip install -e ".[r]"
R -e "install.packages('survival', repos='https://cran.r-project.org')"
```

The R survival backend requires local R, rpy2, and the R `survival` package. If
requested R dependencies are unavailable, SuperMedicine returns a structured
`plugin_unavailable` result instead of silently using R. Without `backend="r"`,
the deterministic pure-Python fallback remains available.

## Verify Basic Installation

Use the status and diagnostic commands:

```bash
python Cli.py status
supermedicine diagnose
supermedicine llm list
supermedicine log location
```

Expected status output includes the SuperMedicine version, configuration state,
plugin discovery status, and test-module count. Diagnostic output redacts API
keys, authorization headers, key-like URL tokens, and secret-looking fields while
preserving information needed for repair.
`supermedicine diagnose` also reports redacted log storage locations. By default,
log reports are under `.supermedicine/logs/` and permission audit records are under
`.supermedicine/policies/audit.jsonl`.

Do not paste unredacted diagnostics, installer tracebacks, private BaseURLs,
absolute local paths, or audit JSONL records into public documentation or issues.
When sharing a failure, summarize the command, platform, redacted error category,
and next repair step.

For development environments, run the Local Quality Gate described in
[README.md](README.md#local-quality-gate).

## First CLI/TUI Usage After Install

All CLI commands can be run as `supermedicine <command>` or `python Cli.py <command>`.
Useful first checks and user-facing feature entry points are:

```bash
supermedicine permission status
supermedicine permission mode conservative
supermedicine tui
supermedicine self-evolve \
  --instruction "生成一个数据清洗工具说明" \
  --target-type markdown \
  --output generated/self-evolution.md
```

The self-evolution command above is preview-only by default and does not write
files. To write a generated artifact, add `--no-preview --confirm-write` and keep
the target inside an allowed generated directory such as `generated/`,
`self_evolution/`, or `tools/generated/`. The `full` access mode is intentionally
high risk and requires both `--confirm-full-access` and `--acknowledge-risk`; it
still uses only the current OS user/process privileges and does not silently
elevate.

In the Chinese TUI, use the sidebar or menu to open “工具管理” for the self-evolution
preview/confirm workflow, “P 🛡️ 权限模式” for access-mode changes, and “Log 报告” for
log storage display, manual refresh, and auto-follow of newly written log records.

## Global CLI Access

After `pip install -e .`, the `supermedicine` command is installed as a console
script. If it is not recognized, add the Python Scripts directory to PATH:

- Windows: `%APPDATA%\Python\Python<版本>\Scripts`
- Linux/macOS: `~/.local/bin`

You can always use `python Cli.py` as a direct substitute.

## Platform Adapters

Adapters are optional add-ons around the standalone Python framework.

| Area | Core Install Required? | Status |
|------|------------------------|--------|
| Standalone Python CLI/Kernel | Yes | Default supported path |
| OpenCode Add-on | No | Metadata, skills, agents, and tool mapping; no native external subagent runtime bridge by itself |
| Claude Code Add-on | No | Minimal capabilities/runtime/local CLI invocation adapter; no native Claude Code skill or subagent support |

OpenCode add-on content lives under `adapters/opencode/`. Claude Code add-on
content lives under `adapters/claude_code/`. These files contain metadata and
must not contain real API keys.

## Troubleshooting

### `No module named 'yaml'`

Install project dependencies:

```bash
pip install -e .
```

### `ModuleNotFoundError: No module named 'installer'`

This usually means `Install.py` was copied out of the release archive instead of
being run from the full extracted directory. The Beta0.4.1 release must keep the
complete layout with `Install.py` and the `installer/` package together at the
extracted root, including `installer/__init__.py` and `installer/exe_release.py`.
Re-download the fixed complete package or run from a complete source/release
directory. Do not try to repair this by manually copying single files out of the
archive.

### `Exe source does not exist` or missing `SuperMedicine.exe`

The release archive should contain `dist/SuperMedicine.exe` next to `Install.py`
and the source packages. Local builds may also use `Dist/SuperMedicine.exe` or a
root-level `SuperMedicine.exe`. Re-run the CI packaging workflow or rebuild the
local executable into `dist/`/`Dist/`, then run:

```bash
python install.py --release-exe dist/SuperMedicine.exe --exe-dry-run
```

The error message lists the exact missing file and every path searched so you can
repair the archive without guessing.

### Interactive prompt rejects my answer

- Blank Provider, Base URL, Model, or API key values are rejected because first-run
  LLM configuration must be complete.
- Base URL must include `http://` or `https://` and a host, for example
  `https://api.openai.com/v1`.
- Yes/no prompts accept `y`, `yes`, `n`, `no`, `1`, `0`, `true`, `false`, `是`, and
  `否`; pressing Enter chooses the displayed default.
- API key input may appear invisible. That is normal hidden input, not a freeze.
- If installation fails, answer yes to retry the wizard, or rerun `python install.py`
  after fixing the path/provider values.

### Permission denied on Windows

Run PowerShell as Administrator, or create a virtual environment with:

```bash
python -m venv .venv --without-pip
```

### CLI command not found

Use `python Cli.py` or add the Python Scripts directory to PATH, then restart the
terminal and run:

```bash
supermedicine --help
```

### Missing LLM key, endpoint, or model

Set provider-specific variables for real credentials:

```bash
export OPENAI_API_KEY=<OPENAI_API_KEY>
export ANTHROPIC_API_KEY=<ANTHROPIC_API_KEY>
export OPENROUTER_API_KEY=<OPENROUTER_API_KEY>
```

If switching fails, inspect redacted state with `supermedicine llm list` and add
missing `base_url`, `api_key_env`/`api_key`, or `model` values with
`supermedicine llm add ... --set-current`.

### Initialization fails and no `.supermedicine/` remains

This is expected when first-run LLM configuration is incomplete. Re-run init with
all required fields. If a previous config existed, failed initialization restores
it; otherwise the partial directory is removed.

### TUI launch or terminal recovery

```bash
supermedicine tui --dry-run
supermedicine tui
```

Use dry-run before launching on new terminals or after a crash. Normal exit is
`q`; if the terminal is interrupted, reopen the shell before relaunching.

### Log storage or realtime log follow

Use `log location` to show redacted storage paths and `log follow` for a terminal
tail-style view:

```bash
supermedicine log location
supermedicine log location --session-id wb-demo
supermedicine log follow --session-id wb-demo --interval 1 --max-entries 20
supermedicine log follow --file session-wb-demo.json --once
```

`log follow` refreshes repeatedly until `Ctrl+C` unless `--once` or an iteration
limit is supplied. The TUI Log page refreshes on a timer, has a manual “刷新”
button, and defaults to auto-following the newest row; selecting an older row turns
auto-follow off until you enable it again.

## Uninstall

```bash
python Uninstall.py --dry-run
python Uninstall.py --force
python Uninstall.py --force --preserve-user-data
python Uninstall.py --target .opencode/skills/supermedicine --dry-run
```

The uninstaller removes SuperMedicine-owned local artifacts in the current
project, including `.supermedicine/`, repository-scoped adapter copies, recorded
installer targets, and explicit `--target` paths. It does not delete the source
repository or unrecorded user-owned global OpenCode/Claude Code configuration.
Use `pip uninstall supermedicine` separately if you installed the package and
want to remove it from the Python environment.

Uninstall logs redact secret-looking fields. Manually remove shell/profile
variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, or
`SM_LLM_API_KEY` if you no longer need them.
