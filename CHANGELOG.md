# Changelog

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
