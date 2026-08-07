#!/usr/bin/env bash
set -euo pipefail

script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
input_url=""
input_file=""
work_dir=""
languages="ru,en"
scene_threshold="0.30"
max_frames="150"
whisper_model="small"
whisper_language="auto"

usage() {
  cat <<'EOF'
Usage:
  prepare_video.sh --url URL [options]
  prepare_video.sh --input FILE [options]

Options:
  --workdir DIR              Output directory; defaults to a secure temp folder
  --languages LIST           Subtitle language priority (default: ru,en)
  --scene-threshold NUMBER   ffmpeg scene threshold from 0 to 1 (default: 0.30)
  --max-frames NUMBER        Maximum selected frames (default: 150)
  --whisper-model NAME       Whisper fallback model (default: small)
  --whisper-language CODE    Language code or auto (default: auto)
EOF
}

require_value() {
  if [ "$#" -lt 2 ] || [ -z "$2" ]; then
    printf 'Missing value for %s\n' "$1" >&2
    exit 2
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --url)
      require_value "$@"
      input_url="$2"
      shift
      ;;
    --input)
      require_value "$@"
      input_file="$2"
      shift
      ;;
    --workdir)
      require_value "$@"
      work_dir="$2"
      shift
      ;;
    --languages)
      require_value "$@"
      languages="$2"
      shift
      ;;
    --scene-threshold)
      require_value "$@"
      scene_threshold="$2"
      shift
      ;;
    --max-frames)
      require_value "$@"
      max_frames="$2"
      shift
      ;;
    --whisper-model)
      require_value "$@"
      whisper_model="$2"
      shift
      ;;
    --whisper-language)
      require_value "$@"
      whisper_language="$2"
      shift
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

if [ -n "$input_url" ] && [ -n "$input_file" ]; then
  printf 'Use either --url or --input, not both.\n' >&2
  exit 2
fi
if [ -z "$input_url" ] && [ -z "$input_file" ]; then
  printf 'Provide --url or --input.\n' >&2
  exit 2
fi
if [ -n "$input_file" ] && [ ! -f "$input_file" ]; then
  printf 'Input file does not exist: %s\n' "$input_file" >&2
  exit 2
fi
if [[ ! "$scene_threshold" =~ ^(0([.][0-9]+)?|1([.]0+)?)$ ]]; then
  printf -- '--scene-threshold must be between 0 and 1.\n' >&2
  exit 2
fi
case "$max_frames" in
  ''|*[!0-9]*|0)
    printf -- '--max-frames must be a positive integer.\n' >&2
    exit 2
    ;;
esac

if [ -z "$work_dir" ]; then
  work_dir="$(mktemp -d "${TMPDIR:-/tmp}/watch.XXXXXX")"
fi
mkdir -p "$work_dir/frames" "$work_dir/frames-selected"

if [ -n "$input_url" ]; then
  "$script_dir/check_dependencies.sh" --url
else
  "$script_dir/check_dependencies.sh" --local
fi

transcript_status="unavailable"
video_path=""

if [ -n "$input_url" ]; then
  printf 'Attempting subtitles...\n'
  if yt-dlp \
    --no-playlist \
    --write-subs \
    --write-auto-subs \
    --sub-langs "$languages" \
    --skip-download \
    --convert-subs srt \
    -o "$work_dir/subtitles.%(ext)s" \
    -- "$input_url"; then
    :
  else
    printf 'Subtitle retrieval failed; continuing with fallback.\n' >&2
  fi

  for candidate in "$work_dir"/subtitles*.srt; do
    if [ -f "$candidate" ]; then
      cp "$candidate" "$work_dir/transcript.srt"
      transcript_status="subtitles"
      break
    fi
  done

  printf 'Downloading video...\n'
  yt-dlp \
    --no-playlist \
    -f "bv*[height<=720]+ba/b[height<=720]" \
    --merge-output-format mp4 \
    -o "$work_dir/video.%(ext)s" \
    -- "$input_url"

  for candidate in "$work_dir"/video.*; do
    if [ -f "$candidate" ]; then
      video_path="$candidate"
      break
    fi
  done
else
  video_path="$input_file"
fi

if [ -z "$video_path" ]; then
  printf 'Video preparation did not produce a readable media file.\n' >&2
  exit 1
fi

if [ "$transcript_status" = "unavailable" ]; then
  if command -v whisper >/dev/null 2>&1; then
    if ffprobe \
      -v error \
      -select_streams a:0 \
      -show_entries stream=index \
      -of csv=p=0 \
      "$video_path" | grep -q .; then
      printf 'No subtitles found; running Whisper fallback...\n'
      if ffmpeg \
        -hide_banner \
        -nostdin \
        -y \
        -i "$video_path" \
        -vn \
        -ac 1 \
        -ar 16000 \
        "$work_dir/audio.wav" \
        >/dev/null 2>&1; then
        if [ "$whisper_language" = "auto" ]; then
          if whisper \
            "$work_dir/audio.wav" \
            --model "$whisper_model" \
            --output_format srt \
            --output_dir "$work_dir"; then
            :
          else
            printf 'Whisper transcription failed; continuing visually.\n' >&2
          fi
        else
          if whisper \
            "$work_dir/audio.wav" \
            --model "$whisper_model" \
            --language "$whisper_language" \
            --output_format srt \
            --output_dir "$work_dir"; then
            :
          else
            printf 'Whisper transcription failed; continuing visually.\n' >&2
          fi
        fi
        if [ -f "$work_dir/audio.srt" ]; then
          cp "$work_dir/audio.srt" "$work_dir/transcript.srt"
          transcript_status="whisper"
        fi
      else
        printf 'Audio extraction failed; continuing visually.\n' >&2
      fi
    else
      printf 'The video has no audio stream; continuing visually.\n' >&2
    fi
  else
    printf 'No subtitles found and Whisper is unavailable; continuing visually.\n' >&2
  fi
fi

printf 'Extracting scene-change frames...\n'
ffmpeg \
  -hide_banner \
  -nostdin \
  -y \
  -i "$video_path" \
  -vf "select='gt(scene,${scene_threshold})',showinfo" \
  -fps_mode vfr \
  "$work_dir/frames/frame_%06d.png" \
  2> "$work_dir/scenes.log"

if ! find "$work_dir/frames" -type f -name 'frame_*.png' -print -quit | grep -q .; then
  printf 'No scene changes detected; extracting the first frame.\n'
  ffmpeg \
    -hide_banner \
    -nostdin \
    -y \
    -i "$video_path" \
    -frames:v 1 \
    "$work_dir/frames/frame_000001.png" \
    >/dev/null 2>&1
fi

python3 "$script_dir/scene_index.py" \
  --log "$work_dir/scenes.log" \
  --frames "$work_dir/frames" \
  --selected "$work_dir/frames-selected" \
  --output "$work_dir/scene_index.csv" \
  --max-frames "$max_frames"

{
  printf 'transcript=%s\n' "$transcript_status"
  printf 'video=%s\n' "$video_path"
  printf 'scene_threshold=%s\n' "$scene_threshold"
  printf 'max_frames=%s\n' "$max_frames"
} > "$work_dir/manifest.txt"

printf '\nPrepared video in: %s\n' "$work_dir"
printf 'Transcript status: %s\n' "$transcript_status"
printf 'Review frames: %s\n' "$work_dir/frames-selected"
printf 'Timestamp index: %s\n' "$work_dir/scene_index.csv"
