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
missing_recommended=""

check_command() {
  command_name="$1"
  requirement="$2"
  if command -v "$command_name" >/dev/null 2>&1; then
    printf 'ok       %s\n' "$command_name"
  elif [ "$requirement" = "required" ]; then
    printf 'missing  %s (required)\n' "$command_name"
    missing_required="${missing_required} ${command_name}"
  elif [ "$requirement" = "recommended" ]; then
    printf 'missing  %s (recommended for YouTube)\n' "$command_name"
    missing_recommended="${missing_recommended} ${command_name}"
  else
    printf 'missing  %s (optional)\n' "$command_name"
    missing_optional="${missing_optional} ${command_name}"
  fi
}

platform="other"
case "$(uname -s 2>/dev/null || true)" in
  Darwin)
    platform="macos"
    ;;
  Linux)
    platform="linux"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    platform="windows"
    ;;
esac

# Prints one install suggestion per missing command for the current platform.
print_install_hint() {
  case "$1" in
    yt-dlp)
      if [ "$platform" = "macos" ] && command -v brew >/dev/null 2>&1; then
        hint='brew install yt-dlp'
      elif [ "$platform" = "windows" ]; then
        hint='winget install yt-dlp.yt-dlp'
      elif [ "$platform" = "linux" ] && command -v pipx >/dev/null 2>&1; then
        hint='pipx install "yt-dlp[default]"'
      else
        hint='python3 -m pip install --user -U "yt-dlp[default]"'
      fi
      printf '  %-9s %s\n' 'yt-dlp:' "$hint"
      printf '  %-9s %s\n' '' 'other methods: https://github.com/yt-dlp/yt-dlp/wiki/Installation'
      ;;
    ffmpeg|ffprobe)
      case "$platform" in
        macos)
          hint='brew install ffmpeg'
          ;;
        windows)
          hint='winget install Gyan.FFmpeg'
          ;;
        linux)
          hint='the ffmpeg package from your distribution, e.g. sudo apt install ffmpeg'
          ;;
        *)
          hint='https://ffmpeg.org/download.html'
          ;;
      esac
      printf '  %-9s %s (ffprobe ships with ffmpeg)\n' "$1:" "$hint"
      ;;
    python3)
      case "$platform" in
        macos)
          hint='brew install python'
          ;;
        linux)
          hint='the python3 package from your distribution'
          ;;
        *)
          hint='https://www.python.org/downloads/'
          ;;
      esac
      printf '  %-9s %s\n' 'python3:' "$hint"
      ;;
    deno)
      case "$platform" in
        macos)
          hint='brew install deno'
          ;;
        windows)
          hint='winget install DenoLand.Deno'
          ;;
        *)
          hint='https://docs.deno.com/runtime/getting_started/installation/'
          ;;
      esac
      printf '  %-9s %s\n' 'deno:' "$hint"
      ;;
    whisper)
      printf '  %-9s %s\n' 'whisper:' 'python3 -m pip install --user openai-whisper'
      ;;
  esac
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

if [ "$mode" = "url" ]; then
  check_command deno recommended
fi

if [ -n "$missing_optional" ]; then
  printf '\nWhisper is only needed when subtitles are unavailable.\n'
fi

if [ -n "$missing_required" ]; then
  {
    printf '\nInstall the missing commands, then run this check again.\n'
    printf 'Suggested install commands for this platform:\n'
    hinted_ffmpeg="false"
    for command_name in $missing_required; do
      case "$command_name" in
        ffmpeg|ffprobe)
          if [ "$hinted_ffmpeg" = "true" ]; then
            continue
          fi
          hinted_ffmpeg="true"
          ;;
      esac
      print_install_hint "$command_name"
    done
  } >&2
fi

if [ -n "$missing_recommended" ]; then
  printf '\nWithout a JavaScript runtime, yt-dlp has limited YouTube support. Suggested install:\n'
  for command_name in $missing_recommended; do
    print_install_hint "$command_name"
  done
fi

if [ -n "$missing_required" ]; then
  exit 1
fi

printf '\nDependency check passed for %s input.\n' "$mode"
