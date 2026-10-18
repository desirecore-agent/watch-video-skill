# Changelog

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
