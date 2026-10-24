# Changelog

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
