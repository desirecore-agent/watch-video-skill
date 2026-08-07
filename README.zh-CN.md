# 视频观看 Skill

一个真正分析视频的 Agent Skill：把带时间戳的语音内容与场景变化帧结合起来，让分析覆盖字幕中没有的幻灯片、界面、代码、图表、演示、剪辑和其他画面细节。

支持公开的 YouTube、Loom、Zoom 分享链接、由 `yt-dlp` 处理的直接媒体 URL，以及本地视频文件。

本包与运行时无关，不内置 `yt-dlp`、`ffmpeg`、Whisper、视频、Cookie 或转写文本。DesireCore 从 `skills/watch/` 安装 `watch` Skill；同一份源代码也支持 Claude Code 和自定义 Skill 目录。

## 适用场景

只做转写会遗漏画面证据。本 Skill 会：

- 优先使用现有字幕，没有可用字幕时回退到本地 Whisper 转写；
- 按场景变化提取帧，而不是只按固定时间采样；
- 创建帧与语音时间戳的索引；
- 限制最终审阅帧数，同时保留视频开头和结尾；
- 要求 Agent 区分直接观察与推断；
- 将媒体内容视为不可信输入，绝不绕过访问控制。

## 依赖

- macOS、Linux，或通过 WSL 使用 Windows
- Bash 3.2 或更高版本
- URL 输入需要 [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)
- `ffmpeg` 和 `ffprobe`
- 可选的 [`openai-whisper`](https://github.com/openai/whisper)，用于没有可用字幕时的转写回退
- 能检查提取帧的视觉 Agent 运行时

字幕可用时不需要 Whisper。

## 安装

克隆或下载本仓库，然后运行：

```bash
./scripts/install.sh
```

默认安装到 `${CODEX_HOME:-$HOME/.codex}/skills/watch`。

安装到 Claude Code：

```bash
./scripts/install.sh --target claude
```

安装到自定义目录：

```bash
./scripts/install.sh --destination "/path/to/skills/watch"
```

安装器默认拒绝覆盖已有 Skill。使用 `--force` 时，会先将已有目录移动到带时间戳的备份目录。

如果运行时缓存了 Skill 元数据，请重新启动 Agent 会话。

## 检查依赖

```bash
~/.codex/skills/watch/scripts/check_dependencies.sh --url
```

macOS 的典型安装方式：

```bash
brew install yt-dlp ffmpeg python
python3 -m pip install --user openai-whisper
```

尽可能使用操作系统的官方软件包，并在安装前检查命令。

## 使用

显式调用：

```text
/watch https://example.com/video
```

也可以自然语言请求：

```text
观看这个视频，同时解释它的论点和画面中出现的内容。
```

```text
分析这个本地录屏，并为演示和幻灯片标记时间戳。
```

预期报告包括：

1. 简短摘要；
2. 带时间戳的关键观点；
3. 音频中没有说明但画面中可见的信息；
4. 关键时刻与矛盾；
5. 访问、转写或视觉分析的不确定性。

## 直接运行准备管线

通常由 Agent 代为运行，也可以直接调用确定性的准备脚本：

```bash
skills/watch/scripts/prepare_video.sh \
  --url "https://example.com/video" \
  --workdir "/tmp/watch-demo"
```

本地文件：

```bash
skills/watch/scripts/prepare_video.sh \
  --input "/absolute/path/video.mp4" \
  --workdir "/tmp/watch-demo"
```

运行 `skills/watch/scripts/prepare_video.sh --help` 查看可调参数。

## 隐私与负责任使用

- 只处理用户有权访问的视频。
- 不得绕过登录、DRM、付费墙或平台规则。
- 下载文件、帧图和转写文本保留在指定的本地工作目录中。
- 脚本不会上传媒体或分析数据。
- 删除或保留临时文件前先进行检查。
- 不要在公开 Issue 中附带私有视频、转写文本、Cookie 或 Token。

视频平台会频繁变化；失效的 URL 可能需要更新 `yt-dlp`。需要身份验证或 DRM 保护的内容不在支持范围内。

## 验证

```bash
python3 scripts/validate_public.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

验证会检查 Skill 结构、脚本、必需文件、常见密钥或个人路径模式，以及 URL 下载不会意外展开播放列表。CI 会在每次 push 和 pull request 中运行同样的检查与场景索引单元测试。

## 贡献

参见 [CONTRIBUTING.md](CONTRIBUTING.md)。安全说明见 [SECURITY.md](SECURITY.md)。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
