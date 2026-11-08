# 视频观看 Skill

一个真正分析视频的 Agent Skill：把带时间戳的语音内容与场景变化帧结合起来，让分析覆盖字幕中没有的幻灯片、界面、代码、图表、演示、剪辑和其他画面细节。

支持公开的 YouTube、Loom、Zoom 分享链接、由 `yt-dlp` 处理的直接媒体 URL，以及本地视频文件。

本包与运行时无关，不内置 `yt-dlp`、`ffmpeg`、Whisper、视频、Cookie 或转写文本。DesireCore 从 `skills/watch/` 安装 `watch` Skill；同一份源代码也支持 Claude Code 和自定义 Skill 目录。

## 适用场景

只做转写会遗漏画面证据。本 Skill 会：

- 优先使用现有字幕；没有可用字幕时，用运行环境的 `TranscribeAudio` 工具转写语音（DesireCore 提供），没有该工具时回退到本地 Whisper；
- 结合首帧、均匀预览采样与场景变化帧；
- 创建帧与语音时间戳的索引；
- 限制提取图片数量，支持对选定区间加密采样复查；
- 要求 Agent 区分直接观察与推断；
- 将媒体内容视为不可信输入，绝不绕过访问控制。

## 依赖

- macOS、Linux，或通过 Git Bash、WSL 使用 Windows
- Bash 3.2 或更高版本
- Python 3.9 或更高版本
- URL 输入需要 [`yt-dlp`](https://github.com/yt-dlp/yt-dlp)；完整支持 YouTube 还推荐安装 [`deno`](https://deno.com/)
- `ffmpeg` 和 `ffprobe`
- 可选的 [`openai-whisper`](https://github.com/openai/whisper)，运行环境没有语音转写工具时用作转写回退
- 能检查提取帧的视觉 Agent 运行时

字幕可用或运行环境提供 `TranscribeAudio` 时不需要 Whisper。

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

缺少命令时，检查脚本会给出适合当前平台的安装命令。尽可能使用操作系统的官方软件包，并在安装前检查命令。

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

短暂事件可以先看预览，再缩小画面复查区间。

```bash
skills/watch/scripts/prepare_video.sh \
  --input "/absolute/path/video.mp4" --workdir "/tmp/watch-detail" \
  --start-sec 4 --end-sec 5 --sample-interval 0.1 --max-frames 20 --skip-whisper
```

索引记录实际解码时间与请求定位时间。`coverage.json` 记录选定区间和帧数预算导致的候选缩减。
稀疏采样可能遗漏短暂事件。工作目录仅保存生成产物，成功重跑会替换帧集合与索引，并发运行使用独立目录。
必需命令需要通过实际版本调用，Windows Store 的 Python 占位程序会被报告为缺失。

## 隐私与负责任使用

- 只处理用户有权访问的视频。
- 不得绕过登录、DRM、付费墙或平台规则。
- 下载文件、帧图和转写文本保留在指定的本地工作目录中。
- 脚本不会上传媒体或分析数据。Agent 使用 `TranscribeAudio` 时，运行环境会把音频发送到用户选定的语音识别服务，并在结果中写明该服务。该服务由用户另行配置，条款和费用以服务商为准。
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
