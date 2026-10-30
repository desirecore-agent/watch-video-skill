# Changelog

## 1.1.4 — 2026-10-30

- Removed `internet` from `requires.connections`. That field names credentials to inject into script environments; it does not mean the skill needs network access. DesireCore looked up a credential called `internet` on every Bash call, found none, and appended a "credential not injected" notice to the command output, which led agents to report a missing network credential. The skill needs no credentials, and URL inputs still reach the network through `yt-dlp`.

中文：

- 从 `requires.connections` 中移除 `internet`。该字段声明的是要注入脚本环境的凭据，并不表示技能需要联网。DesireCore 每次执行 Bash 都会查找名为 `internet` 的凭据，查不到就在命令输出后追加「连接凭据未注入」的提示，Agent 因此误报缺少网络凭据。本技能不需要任何凭据，URL 输入仍由 `yt-dlp` 联网下载。

## 1.1.3 — 2026-10-28

- The skill body now tells the agent how to handle a missing dependency: always run the check before preparing media, explain what the missing command is for, propose the install command and ask for approval, install after approval and re-run the check, and fall back to an authorized local copy if the user declines or installation fails. It also states that `yt-dlp` is not in `requires.bins`, so runtimes that read that list do not warn about it and the check is the only place it is detected.
- `scripts/check_dependencies.sh` prints an install command for each missing program on the current platform (Homebrew on macOS, winget on Windows under Git Bash, pipx or pip for `yt-dlp` on Linux) plus the official yt-dlp installation guide, instead of one generic macOS line.
- For URL inputs the check also reports `deno` as recommended: without a JavaScript runtime, yt-dlp has limited YouTube support. A missing `deno` does not fail the check.
- Added tests for the dependency check and for preparation stopping at the check before any download.

中文：

- Skill 正文写明缺少依赖时的处理方式：准备媒体前始终先运行检查，说明缺少的命令用来做什么，给出安装命令并征求批准，获批后安装并重新检查；用户拒绝或安装失败时改为分析用户有权使用的本地副本。正文也说明 `yt-dlp` 不在 `requires.bins` 中，读取该列表的运行环境不会提醒缺少它，只有这项检查能发现。
- `scripts/check_dependencies.sh` 按当前平台为每个缺少的程序给出安装命令（macOS 用 Homebrew，Windows 的 Git Bash 下用 winget，Linux 上的 `yt-dlp` 用 pipx 或 pip），并附 yt-dlp 官方安装指南，不再只有一行通用的 macOS 提示。
- URL 输入时检查还会把 `deno` 报为推荐项：没有 JavaScript 运行时，yt-dlp 对 YouTube 的支持有限。缺少 `deno` 不会让检查失败。
- 为依赖检查、以及准备脚本在下载前停在检查处增加测试。

## 1.1.2 — 2026-10-24

- Removed `yt-dlp` from `requires.bins`. Runtimes such as DesireCore treat every program in that list as required for all inputs, so a missing `yt-dlp` made the whole skill look unusable even for local files, which only need `ffmpeg`, `ffprobe`, and `python3`. URL inputs still need `yt-dlp`; `scripts/check_dependencies.sh --url` reports it when it is missing.

中文：

- 从 `requires.bins` 中移除 `yt-dlp`。DesireCore 等运行环境会把该列表里的每个程序都当作所有输入的必需项，缺少 `yt-dlp` 时整个技能都会被判为不可用，但本地文件只需要 `ffmpeg`、`ffprobe` 和 `python3`。URL 输入仍然需要 `yt-dlp`，缺少时由 `scripts/check_dependencies.sh --url` 报告。

## 1.1.1 — 2026-10-18

- Declared the required command-line programs (`yt-dlp`, `ffmpeg`, `ffprobe`, `python3`) in `requires.bins`, so runtimes that read the declaration can report missing programs before the scripts fail. The optional Whisper fallback stays undeclared.

中文：

- 在 `requires.bins` 中声明必需的命令行程序（`yt-dlp`、`ffmpeg`、`ffprobe`、`python3`），读取该声明的运行环境可以在脚本失败前提示缺少哪些程序。可选的 Whisper 回退不在声明中。

## 1.1.0 — 2026-08-07

- Added DesireCore market metadata, versioning, risk classification, and a Chinese skill body.
- Added `--no-playlist` to URL preparation so one request cannot expand into an unintended playlist download.
- Added a timestamp fallback for the first frame when a video has no detected scene changes.
- Added scene-index unit tests and CI coverage.

中文：

- 增加 DesireCore 市场元数据、版本号、风险分级和中文 Skill 正文。
- URL 准备流程增加 `--no-playlist`，避免一次请求意外下载整个播放列表。
- 视频没有检测到场景变化时，为首帧补充零时刻时间戳。
- 增加场景索引单元测试并纳入 CI。
