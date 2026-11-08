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
skip_whisper="false"
start_sec="0"
end_sec=""
sample_interval=""

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
  --start-sec NUMBER         Start the visual review at this source time
  --end-sec NUMBER           Stop the visual review before this source time
  --sample-interval NUMBER   Seconds between preview frames in the selected range
                            (default: up to 24 evenly spaced preview frames)
  --whisper-model NAME       Whisper fallback model (default: small)
  --whisper-language CODE    Language code or auto (default: auto)
  --skip-whisper             Leave a missing transcript to the runtime's
                             TranscribeAudio tool instead of running Whisper
EOF
}

# File tools outside this shell cannot open MSYS paths such as /tmp/... on Windows.
native_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  else
    printf '%s\n' "$1"
  fi
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
    --start-sec)
      require_value "$@"
      start_sec="$2"
      shift
      ;;
    --end-sec)
      require_value "$@"
      end_sec="$2"
      shift
      ;;
    --sample-interval)
      require_value "$@"
      sample_interval="$2"
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
    --skip-whisper)
      skip_whisper="true"
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
mkdir -p "$work_dir"

if [ -n "$input_url" ]; then
  "$script_dir/check_dependencies.sh" --url
else
  "$script_dir/check_dependencies.sh" --local
fi

lock_dir="$work_dir/.watch-preparing"
if ! mkdir "$lock_dir" 2>/dev/null; then
  printf 'This work directory is already being prepared. Use a separate directory; after an interrupted run, check its owner before removing .watch-preparing.\n' >&2
  exit 1
fi
trap 'rmdir "$lock_dir" 2>/dev/null || true' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# An interrupted attempt must not leave a successful index from an older run.
rm -f "$work_dir/manifest.txt" "$work_dir/scene_index.csv" "$work_dir/coverage.json" \
  "$work_dir/transcript.srt" "$work_dir/audio.srt"

transcript_status="unavailable"
video_path=""

if [ -n "$input_url" ]; then
  for generated in "$work_dir"/video.* "$work_dir"/subtitles*.srt; do
    if [ -f "$generated" ]; then rm -f "$generated"; fi
  done
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
    -f "bv*[height<=?720]+ba/b[height<=?720]" \
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
  if [ "$skip_whisper" = "true" ]; then
    printf 'No subtitles found; leaving transcription to the runtime.\n'
  elif command -v whisper >/dev/null 2>&1; then
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

printf 'Extracting preview and scene-change frames...\n'
frame_args=(--video "$(native_path "$video_path")" --workdir "$(native_path "$work_dir")"
  --scene-threshold "$scene_threshold" --max-frames "$max_frames" --start-sec "$start_sec")
if [ -n "$end_sec" ]; then frame_args+=(--end-sec "$end_sec"); fi
if [ -n "$sample_interval" ]; then frame_args+=(--sample-interval "$sample_interval"); fi
python3 "$(native_path "$script_dir/prepare_frames.py")" "${frame_args[@]}"

{
  printf 'transcript=%s\n' "$transcript_status"
  printf 'video=%s\n' "$(native_path "$video_path")"
  printf 'scene_threshold=%s\n' "$scene_threshold"
  printf 'max_frames=%s\n' "$max_frames"
} > "$work_dir/manifest.txt"

printf '\nPrepared video in: %s\n' "$(native_path "$work_dir")"
printf 'Media file: %s\n' "$(native_path "$video_path")"
printf 'Transcript status: %s\n' "$transcript_status"
printf 'Review frames: %s\n' "$(native_path "$work_dir/frames-selected")"
printf 'Timestamp index: %s\n' "$(native_path "$work_dir/scene_index.csv")"
printf 'Coverage: %s\n' "$(native_path "$work_dir/coverage.json")"
