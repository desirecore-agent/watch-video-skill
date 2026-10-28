# Watch Video Skill

An agent skill that actually watches videos: it combines timestamped speech with
scene-change frames so the analysis includes slides, interfaces, code, charts,
demos, editing, and other details that never appear in a transcript.

It supports public YouTube, Loom, Zoom-share, and direct media URLs handled by
`yt-dlp`, plus local video files.

The package is runtime-neutral and does not bundle `yt-dlp`, `ffmpeg`, Whisper,
video files, cookies, or transcripts. DesireCore installs the `watch` skill
from `skills/watch/`; the same source also supports Claude Code and custom
skill destinations.

## Why use it

Transcript-only summaries miss visual evidence. This skill:

- prefers existing subtitles, then falls back to local Whisper transcription;
- extracts frames when scenes change instead of sampling on a fixed timer;
- creates a timestamp index for matching frames to speech;
- caps the visual review set without losing the beginning or end;
- tells the agent to separate observations from inferences;
- treats media contents as untrusted input and never bypasses access controls.

## Requirements

- macOS, Linux, or Windows through WSL
- Bash 3.2 or newer
- Python 3.9 or newer
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) for URL inputs, plus
  [`deno`](https://deno.com/) (recommended) for full YouTube support
- [`ffmpeg`](https://ffmpeg.org/) and `ffprobe`
- [`openai-whisper`](https://github.com/openai/whisper) for optional
  transcription fallback
- a vision-capable agent runtime for reviewing the extracted frames

Whisper is optional when the source has usable subtitles.

## Install

Clone or download this repository, then run:

```bash
./scripts/install.sh
```

This installs the skill to `${CODEX_HOME:-$HOME/.codex}/skills/watch`.

For Claude Code:

```bash
./scripts/install.sh --target claude
```

For another compatible runtime:

```bash
./scripts/install.sh --destination "/path/to/skills/watch"
```

The installer refuses to overwrite an existing skill. Pass `--force` to move
the existing copy to a timestamped backup before installing.

Start a new agent session after installation if the runtime caches skill
metadata.

## Check the setup

```bash
~/.codex/skills/watch/scripts/check_dependencies.sh --url
```

Typical macOS setup:

```bash
brew install yt-dlp ffmpeg python
python3 -m pip install --user openai-whisper
```

When a command is missing, the check prints an install command for the current
platform. Use your operating system's official packages where possible. Review
commands before installing software.

## Use

Invoke the skill explicitly:

```text
/watch https://example.com/video
```

Or ask naturally:

```text
Watch this video and explain both the argument and what appears on screen.
```

```text
Analyze this local recording. Include timestamps for demos and slides.
```

The expected report contains:

1. a short summary;
2. timestamped key points;
3. information visible on screen but absent from the audio;
4. notable moments and contradictions;
5. access, transcription, or visual uncertainties.

## Run the preparation pipeline directly

The agent normally runs this for you, but the deterministic pipeline is also
available as a command:

```bash
skills/watch/scripts/prepare_video.sh \
  --url "https://example.com/video" \
  --workdir "/tmp/watch-demo"
```

For a local file:

```bash
skills/watch/scripts/prepare_video.sh \
  --input "/absolute/path/video.mp4" \
  --workdir "/tmp/watch-demo"
```

Run `skills/watch/scripts/prepare_video.sh --help` for tuning options.

## Privacy and responsible use

- Process only videos you are authorized to access.
- Do not use this project to bypass logins, DRM, paywalls, or platform rules.
- Downloads, frames, and transcripts stay local in the selected working
  directory.
- The scripts do not upload media or analytics.
- Review temporary files before deleting or retaining them.
- Do not attach private videos, transcripts, cookies, or tokens to public bug
  reports.

Video hosting sites change frequently. A URL that stops working may require a
newer `yt-dlp`; authenticated or DRM-protected content is intentionally outside
the supported workflow.

## Validate

```bash
python3 scripts/validate_public.py
```

The validation checks skill structure, scripts, required files, and common
secret or personal-path patterns. It also verifies that URL downloads cannot
expand a playlist unexpectedly. CI runs the same check and the scene-index unit
tests on every push and pull request.

Run the unit tests directly with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security guidance is in
[SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
