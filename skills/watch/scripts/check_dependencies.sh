#!/usr/bin/env bash
set -euo pipefail

mode="url"
require_whisper="false"

usage() {
  cat <<'EOF'
Usage: check_dependencies.sh [--url|--local] [--require-whisper]

Checks commands used by the watch skill. Whisper is optional unless
--require-whisper is supplied.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --url)
      mode="url"
      ;;
    --local)
      mode="local"
      ;;
    --require-whisper)
      require_whisper="true"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

missing_required=""
missing_optional=""

check_command() {
  command_name="$1"
  requirement="$2"
  if command -v "$command_name" >/dev/null 2>&1; then
    printf 'ok       %s\n' "$command_name"
  elif [ "$requirement" = "required" ]; then
    printf 'missing  %s (required)\n' "$command_name"
    missing_required="${missing_required} ${command_name}"
  else
    printf 'missing  %s (optional)\n' "$command_name"
    missing_optional="${missing_optional} ${command_name}"
  fi
}

if [ "$mode" = "url" ]; then
  check_command yt-dlp required
fi
check_command ffmpeg required
check_command ffprobe required
check_command python3 required

if [ "$require_whisper" = "true" ]; then
  check_command whisper required
else
  check_command whisper optional
fi

if [ -n "$missing_optional" ]; then
  printf '\nWhisper is only needed when subtitles are unavailable.\n'
fi

if [ -n "$missing_required" ]; then
  printf '\nInstall the missing commands, then run this check again.\n' >&2
  case "$(uname -s 2>/dev/null || true)" in
    Darwin)
      printf 'macOS hint: brew install yt-dlp ffmpeg python\n' >&2
      printf 'Whisper hint: python3 -m pip install --user openai-whisper\n' >&2
      ;;
    Linux)
      printf 'Linux hint: install ffmpeg and python3 with your package manager,\n' >&2
      printf 'then install yt-dlp and openai-whisper from their official packages.\n' >&2
      ;;
  esac
  exit 1
fi

printf '\nDependency check passed for %s input.\n' "$mode"
