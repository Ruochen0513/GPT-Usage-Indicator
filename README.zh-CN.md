# GPT Usage Indicator

[English](README.md) | **简体中文**

直接安装 GNOME 插件，或双击 Windows / macOS 应用，在设置中登录 ChatGPT 账号，显示 **Codex 的 5 小时与 7 天订阅额度**。普通用户不需要克隆仓库或编译代码。

支持百分比、双环、进度条、环图 + 数字四种呈现，剩余／已用切换、多账号、自动刷新、重置时间。架构参考 [Agent Status Indicator](https://github.com/Ruochen0513/agent-status-indicator)，本项目重新实现额度查询与界面。

![功能示意，示例数值，并非实机截图](docs/preview.svg)

## 下载与安装

发行仓库：[Ruochen0513/GPT-Usage-Indicator](https://github.com/Ruochen0513/GPT-Usage-Indicator)。在 [Releases](https://github.com/Ruochen0513/GPT-Usage-Indicator/releases) 中选择对应平台的安装文件；当前 `v0.3.0` 五平台构建已通过并生成发行草稿：仓库所有者可下载草稿附件，公开发布后其他用户也可下载。也可从[本次构建的 Artifacts](https://github.com/Ruochen0513/GPT-Usage-Indicator/actions/runs/39578055603) 下载。

| 平台 | 下载文件 | 是否需要 Python / Codex |
| --- | --- | --- |
| GNOME，Intel/AMD 64 位 | `gpt-usage-linux-x64.shell-extension.zip` | 需要系统 Python 3.10+；Codex 已内置 |
| GNOME，ARM64 | `gpt-usage-linux-arm64.shell-extension.zip` | 需要系统 Python 3.10+；Codex 已内置 |
| Windows x64 | `GPT-Usage-windows-x64.exe` | 都不需要额外安装 |
| macOS Apple Silicon | `GPT-Usage-macos-arm64.zip` | 都不需要额外安装 |
| macOS Intel | `GPT-Usage-macos-x64.zip` | 都不需要额外安装 |

完整 GNOME 包包含官方原生 Codex 运行时，因此文件较大（x64 约 107 MiB）。另有不含运行时的小体积开发包 `gpt-usage@local.shell-extension.zip`，它需要系统另行提供 Codex，普通用户请选择上表中的完整包。

### GNOME

支持目标为 GNOME Shell 46–50。下载对应架构的 ZIP 后，在下载目录执行：

```bash
gnome-extensions install --force ./gpt-usage-linux-x64.shell-extension.zip
```

ARM64 用户换成相应文件名。重新登录桌面后，在 Extensions / 扩展管理器中启用 **GPT Usage Indicator**，打开其设置。也可以执行：

```bash
gnome-extensions enable gpt-usage@local
gnome-extensions prefs gpt-usage@local
```

这两条是桌面插件的安装／管理命令，无需下载源码或在项目中构建。不需要 root。

在插件设置的 Accounts 中：

1. 输入账号 profile id（例如 `personal`）、显示名称和可选的预期邮箱，点击 **Add account**。
2. 选择该账号，点击 **Sign in**，在自动打开的官方网页中完成授权。
3. 返回设置，看到登录邮箱后，额度会自动刷新到顶栏左侧。

默认数据目录与运行时已经配置好，无需填写源码路径。顶栏菜单可以切换账号、查看重置时间、手动刷新或打开设置。

若浏览器回调不可用，点击 **Device code**，在官方页面输入设置页显示的设备码。设备授权是否可用取决于账号／组织策略。**Cancel** 或关闭设置可取消当前授权；**Sign out** 清除该 profile 的登录与额度。

### GNOME 官方平台版本（候选）

另提供适用于 extensions.gnome.org 的独立**上架候选版本**，尚未通过审核或上架。
当前面向 **GNOME Shell 46**，UUID 为 `gpt-usage@ruochen0513.github.io`。

- **扩展包**：`gpt-usage@ruochen0513.github.io.shell-extension.zip`，约 14 KB，
  仅含 GJS、元数据、样式、XML schema 和许可文件。
- **独立依赖**：`gpt-usage-companion-linux-x64.tar.gz` 或
  `gpt-usage-companion-linux-arm64.tar.gz`。从发行附件下载、解压，在解压目录执行：

```bash
python3 -B install.py
```

配套程序已内置 Codex，需要系统提供 GJS 和 Python 3.10+。安装不需要 root，
通过会话 D-Bus 按需启动，空闲 60 秒退出。扩展通过 D-Bus 通信，不启动外部命令，
也不读取凭据文件；仍可在设置中登录账号。标准数据目录下的原有账号可直接共享，
代理和外观设置则独立保存。启用此版本前请禁用原版，避免出现两个指示器。

小体积扩展包生成于 `dist/ego/`，配套程序生成于 `dist/release/`，新的发行构建会同时生成两者。
发行草稿在公开发布前仅所有者可见；提交 GNOME 审核前，需要先公开配套程序的下载。
安装、本机验收和上传步骤见[上架指南](docs/EGO-PUBLISHING.md)。上表中的完整 GNOME 包继续供 GitHub 用户安装。

### GNOME 系统代理与登录 403（v0.2.1）

内置 Codex 0.163.0 的 Linux 系统代理实现不可用，单纯在 GNOME 配置系统代理不一定会传入其后台进程。插件现在通过 GIO 解析系统代理／PAC，将登录与额度目标的路由显式传给各自的 Codex 进程。

设置 → **Network proxy** 提供三种模式：

- **GNOME system proxy / PAC**：默认，解析系统配置。解析失败会提示，不会自动改成直连。
- **Manual proxy URL**：填写代理客户端的本地 HTTP／混合端口，例如 `http://127.0.0.1:7897`，点击行内 Apply 后再登录。如果该端口实际提供 SOCKS5，可使用 `socks5h://127.0.0.1:端口`。不要在地址中填写用户名或密码。
- **Inherited launch environment**：仅继承启动环境，供已有环境变量配置的用户使用。

**Check route** 显示登录与额度查询将采用的代理路由，只检查配置，不发送登录请求、检测出口 IP 或确认地区。手动代理会覆盖后台进程中残留的代理变量和绕过列表，并保留 localhost 回调的直连。不会修改系统代理或浏览器设置。

`Country, region, or territory not supported` 是服务端地区拒绝。插件现在单独识别这类错误并保留安全的 request id；代理名称标为新加坡不等于已验证服务端看到的出口。如果已确认位于[支持地区](https://help.openai.com/en/articles/7947663-chatgpt-supported-countries)仍被拒绝，可向官方支持提交发生时间与 request id。

### Windows

下载 `GPT-Usage-windows-x64.exe`，双击运行即可。EXE 包含 Python/Tk 和 Codex 运行时，不需要安装 Python、Node.js、Codex，也不需要启动终端。

首次运行自动打开 Settings：添加账号后自动进入官方浏览器授权。已有账号可点击 **Sign in** 重新登录，或使用 **Device code**。设置也支持退出账号和取消授权。

### macOS

按芯片选择 ZIP，解压后打开其中的 `gpt-usage-desktop.app`，首次运行在 Settings 添加账号并登录。应用已包含运行依赖。

当前构建未配置开发者签名与公证；首次打开时系统可能要求确认来源。应用支持置顶、透明度、拖动、账号与视图切换。

## 界面操作

| 操作 | GNOME | 桌面小窗口 |
| --- | --- | --- |
| 切换账号 | 顶栏菜单或设置 | 顶部下拉列表 |
| 切换视图 | 设置 → Presentation | Text / Rings / Bars / Combined |
| 剩余／已用 | Show remaining quota | Remaining / Used |
| 手动刷新 | 菜单 → Refresh now | Refresh |
| 登录／退出／取消 | 设置 → Accounts | Settings |
| 位置、置顶、透明度 | 由 Shell 顶栏管理 | 拖动标题，或 Settings |
| 自动刷新 | 默认 120 秒，可设 30–3600 秒 | 相同 |

浏览器授权只发生在 OpenAI 官方 HTTPS 页面。本项目不接收密码，授权链接和设备码仅在当前设置会话中显示。登录完成后核对邮箱，再刷新额度；若配置了预期邮箱，登录到其他邮箱会退出错误账号并提示。

普通用户无需调整 Advanced。它用于设置自定义数据目录、Python 或 Codex 可执行文件；`codex` 默认优先使用发行包内置版本，找不到时才查找 PATH。

## 额度含义

展示的是 Codex `account/rateLimits/read` 返回的 **ChatGPT 订阅额度**，不是 ChatGPT 网页每个模型的消息次数，也不是 API 余额或 API token 计费。

- 根据服务端窗口时长识别 300 分钟与 10080 分钟，不硬编码主／次窗口顺序。
- 25% 已用对应 75% 剩余；可切换显示口径。
- 某窗口未提供时显示 `—`，不会当成 0% 已用。
- 超过 `max(600, 2 × 刷新间隔 + 120)` 秒未更新时显示过期，隐藏旧数值。
- 到达重置时刻后等待重新查询，不推算成满额。
- 网络、登录或身份校验失败时清除旧额度并提示原因。
- 剩余大于 25% 为绿，10–25% 为黄，10% 及以下为红；未知为灰色。

每个 profile 有独立的登录目录。共享数据目录的 GNOME 与桌面客户端会串行处理同一账号的查询、登录和退出，防止登录过程被定时查询覆盖。额度为同一 ChatGPT 账号共享，与从哪个客户端消耗无关。

## 数据、更新与卸载

| 版本 | 默认数据目录 |
| --- | --- |
| GNOME | `$XDG_DATA_HOME/gpt-usage-indicator`，默认 `~/.local/share/gpt-usage-indicator` |
| Windows EXE | `%LOCALAPPDATA%\gpt-usage-indicator` |
| macOS 应用 | `~/Library/Application Support/gpt-usage-indicator` |
| Linux 原生桌面应用 | `$XDG_DATA_HOME/gpt-usage-indicator` |
| 源码开发版 | 仓库中的 `.runtime/` |

升级插件或替换 EXE/.app 保留这些数据；不在可执行文件目录中保存登录，放到受保护目录也不会因保存配置失败而无法使用。

数据包含 `accounts.json`、各 profile 的 `codex-home`、不含 token 的额度快照、窗口偏好。Codex 登录凭据使用各 profile 的文件存储，未使用系统钥匙串中的共用登录。POSIX 私有目录为 `0700`、JSON 为 `0600`，Windows 依赖当前用户目录 ACL。

关闭窗口停止后台线程，禁用插件终止查询；没有系统常驻服务、注册表写入、全局 PATH 改动或自动登录项。卸载 GNOME：

```bash
gnome-extensions disable gpt-usage@local
gnome-extensions uninstall gpt-usage@local
```

Windows/macOS 关闭后删除应用即可。需要清除账号时先在设置中 Sign out；完全清除配置可删除上表对应目录。其他 Codex 客户端配置不由本项目管理。

## 故障排查

| 现象 | 处理 |
| --- | --- |
| GNOME 看不到插件 | 确认 Shell 版本与 ZIP 架构，安装后重新登录并启用 |
| Sign in 无法启动 | 完整包已含 Codex；GNOME 检查系统是否有 Python 3.10+，必要时在 Advanced 填绝对路径 |
| 浏览器没有自动打开 | 点 Open authorization page，或尝试 Device code |
| 授权超时／取消 | 再次 Sign in，关闭多余的授权页面 |
| 邮箱不匹配 | 登录预期邮箱，或创建另一个 profile |
| 一直显示 `—` | 核对登录状态、网络；账号可能未返回该时长窗口 |
| 只有一个窗口有数字 | 另一个窗口未提供，保持未知是正常行为 |
| 更新后旧数据不可见 | 若以前显式使用项目 `.runtime`，在 Advanced 指回其绝对路径即可 |
| Linux 源码缺 Tkinter | 为所用 Python 安装匹配的 Tcl/Tk；GNOME 插件不需要 Tk |

完整发行包使用固定版本 Codex。若官方协议发生变化，可更新发行版本；高级用户也可临时选择更新后的外部 Codex 二进制。程序不为查询额度启动模型 turn，不读取聊天记录；查询需连接官方服务。

## 给维护者：构建与发布

下面的步骤只供维护者。普通用户下载上表中的成品即可。

### 自动构建发行文件

[Build downloadable applications 工作流](.github/workflows/release.yml) 支持：

- GitHub Actions → **Build downloadable applications** → **Run workflow**：构建五个平台文件，并提供下载 artifacts。
- 推送 `v*` 标签：构建完成后创建一个包含直接下载附件的 **draft release**。维护者检查后发布，普通用户即可从 Releases 下载。

矩阵包含 Windows x64、macOS ARM64 / Intel、GNOME x64 / ARM64。Windows EXE 和 macOS `.app` 必须在相应系统的 runner 上构建，不在 Linux 中伪造或交叉拼装。

### 本地构建 GNOME 完整包

```bash
python3 -B scripts/fetch_codex.py --target linux-x64
python3 -B scripts/package_extension.py --target linux-x64
python3 -B scripts/package_release.py --target linux-x64
```

ARM64 换为 `linux-arm64`。本机不需要运行被打包的目标架构二进制。源码版轻量插件可只运行 `scripts/package_extension.py`。

官方平台源码候选包与独立配套程序分别构建：

```bash
python3 -B scripts/package_ego.py
python3 -B scripts/package_companion.py --target linux-x64
```

运行时来自 OpenAI 官方 `@openai/codex` npm 原生包，固定为 `0.163.0`；下载校验 npm 的 SHA-512 integrity，打包前再次校验原生文件 SHA-256，同时携带对应版本 LICENSE、NOTICE 和来源清单。只从归档提取明确的原生文件，不执行其中的安装脚本。

### 本地构建 Windows / macOS

在对应操作系统安装 Python/Tk 与 PyInstaller，选择目标：`win32-x64`、`darwin-arm64` 或 `darwin-x64`。

```bash
python -m pip install --no-cache-dir 'pyinstaller>=6.11,<7'
python -B scripts/fetch_codex.py --target win32-x64
python -B scripts/build_desktop.py --bundle-codex
python -B scripts/package_release.py --target win32-x64
```

macOS 替换 target。最终文件及 SHA-256 校验在 `dist/release/`，不是源码 ZIP；Windows 是单个 GUI EXE，macOS 使用 `ditto` 保存 `.app` 包结构。

### 源码运行与 CLI

开发依赖为 Python 3.10+；Tk 窗口另需 Tkinter，若没有内置运行时则需要系统 Codex。运行核心不依赖第三方 Python 库。

```bash
python3 -B bin/run.py account add personal --label Personal --email you@example.com
python3 -B bin/run.py login --account personal
python3 -B bin/run.py refresh --account personal
python3 -B bin/run.py desktop
```

Windows 用 `py -3` 或附带 `.cmd`；macOS 可用 `bin/GPT-Usage.command`。源码 Settings 也支持图形授权。其他命令：

| 命令 | 功能 |
| --- | --- |
| `account list` | 列出 profile，不输出凭据 |
| `login --account ID --gui [--device-auth]` | 向图形客户端输出安全的授权 JSONL 事件 |
| `logout --account ID` | 退出并清空额度 |
| `show --account ID` | 读取快照 |
| `--data-dir PATH --codex PATH` | 放在子命令前，自定义目录和运行时 |

独立 profile 不自动导入其他 Codex 客户端的登录，需要登录一次。profile id 支持 1–48 位字母、数字、`_`、`-`，拒绝目录穿越。

### 测试与自查

```bash
python3 -B -m unittest discover -s tests -v
node tests/test_ui.mjs
gjs -m tests/test_gjs.mjs
gjs -m tests/test_proxy_gjs.mjs
node --input-type=module --check < gnome-extension/gpt-usage@local/extension.js
node --input-type=module --check < gnome-extension/gpt-usage@local/prefs.js
git diff --check
```

模拟测试只在仓库 `.runtime/tests` 写数据，不使用真实登录、不联网查询额度。无可连接 display 时 Tk 测试明确跳过。配套程序测试使用私有会话总线和模拟后台，覆盖安装、D-Bus 按需激活、私有授权事件、调用者归属、代理隔离和取消。自查：[GNOME 阶段](docs/reviews/gnome.md)、[初版](docs/reviews/final.md)、[直接安装与图形登录升级](docs/reviews/distribution.md)、[GNOME 代理修复](docs/reviews/proxy.md)、[官方平台版本](docs/reviews/ego.md)。目标桌面的手工步骤见[验收清单](docs/ACCEPTANCE.md)与[上架指南](docs/EGO-PUBLISHING.md)。构建成功不等于真实账号授权／桌面交互已全部实测。

源码 `.runtime`、`build`、`dist` 不进入 Git；发行只携带指定程序、许可和校验信息，不包含开发账号数据。源码便携 ZIP 另由 `scripts/package_desktop.py` 生成，仅供开发用途。

## 参考与许可

- [官方 App Server 协议](https://developers.openai.com/codex/app-server/)：额度与受管理的浏览器／设备授权接口。
- [官方认证说明](https://developers.openai.com/codex/auth/)。
- [GNOME 扩展 API](https://gjs.guide/extensions/topics/extension.html)、[设置页](https://gjs.guide/extensions/development/preferences.html)。
- [参考项目 Agent Status Indicator](https://github.com/Ruochen0513/agent-status-indicator)，未对参考仓库做修改。

本项目为 MIT（[LICENSE](LICENSE)），内置 Codex 为 Apache-2.0，完整包随附上游许可与 NOTICE。本项目不是 OpenAI 官方产品。
