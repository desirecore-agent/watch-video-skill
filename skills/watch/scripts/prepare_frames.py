#!/usr/bin/env python3
"""Extract a bounded preview and retain decoded source timestamps."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from scene_index import evenly_spaced_indices, format_timecode


PTS = re.compile(r"\bpts_time:\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)")
INTEGER_PTS = re.compile(r"\bpts:\s*(-?\d+)")
TIME_BASE = re.compile(r"config in time_base:\s*(\d+)/(\d+)")
FIELDS = ["selected_frame", "source_frame", "seconds", "timecode", "requested_seconds"]


def run_media(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True, errors="replace")
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or f"{command[0]} exited {result.returncode}")
    return result


def decoded_times(log: str) -> list[float]:
    time_base = TIME_BASE.search(log)
    if time_base:
        numerator, denominator = map(int, time_base.groups())
        return [int(match.group(1)) * numerator / denominator for match in INTEGER_PTS.finditer(log)]
    return [float(match.group(1)) for match in PTS.finditer(log)]


def probe_video(video: Path) -> tuple[float, float]:
    result = run_media([
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,start_time:stream=codec_type,duration,start_time", "-of", "json", str(video),
    ])
    metadata = json.loads(result.stdout)
    streams = [stream for stream in metadata.get("streams", []) if stream.get("codec_type") == "video"]
    if not streams:
        raise ValueError("The input has no video stream.")
    container = metadata.get("format", {})
    duration = float(container.get("duration", streams[0].get("duration", "nan")))
    origin = float(container.get("start_time", streams[0].get("start_time", 0)))
    if not math.isfinite(duration) or duration <= 0 or not math.isfinite(origin):
        raise ValueError("The input needs a finite duration and start time.")
    return duration, origin


def sample_times(start: float, end: float, interval: float | None, limit: int) -> list[float]:
    if interval is None:
        count = min(24, limit)
        interval = (end - start) / count
    else:
        count = math.ceil((end - start) / interval - 1e-9)
        if count > limit:
            raise ValueError(
                f"The requested interval needs {count} preview frames, above --max-frames {limit}. "
                "Use a shorter time range, a larger interval, or a larger frame budget."
            )
    return [start + index * interval for index in range(count)]


def detect_scenes(video: Path, threshold: float, origin: float, start: float, end: float, log: Path) -> list[float]:
    result = run_media([
        "ffmpeg", "-hide_banner", "-nostdin", "-copyts", "-ss", f"{start:.9f}",
        "-t", f"{end - start:.9f}", "-i", str(video), "-an",
        "-vf", f"select='gt(scene,{threshold})',showinfo", "-fps_mode", "passthrough", "-f", "null", "-",
    ])
    log.write_text(result.stderr, encoding="utf-8")
    times = [seconds - origin for seconds in decoded_times(result.stderr)]
    return [seconds for seconds in times if start <= seconds < end]


def extract_frame(video: Path, requested: float, origin: float, output: Path) -> float | None:
    result = run_media([
        "ffmpeg", "-hide_banner", "-nostdin", "-y", "-copyts", "-ss", f"{requested:.9f}",
        "-i", str(video), "-an", "-vf", "showinfo", "-frames:v", "1",
        "-fps_mode", "passthrough", str(output),
    ])
    times = decoded_times(result.stderr)
    if not output.is_file():
        return None
    if not times:
        raise RuntimeError("FFmpeg produced a frame without a source timestamp.")
    return times[0] - origin


def prepare_frames(args: argparse.Namespace) -> dict[str, float | int]:
    duration, origin = probe_video(args.video)
    end = min(args.end_sec if args.end_sec is not None else duration, duration)
    if args.start_sec >= end:
        raise ValueError("The selected time range does not overlap the video.")
    samples = sample_times(args.start_sec, end, args.sample_interval, args.max_frames)
    scenes = detect_scenes(args.video, args.scene_threshold, origin, args.start_sec, end, args.workdir / "scenes.log")
    candidates = sorted({round(seconds, 9) for seconds in samples + scenes})
    if args.sample_interval is None:
        chosen = [candidates[index] for index in evenly_spaced_indices(len(candidates), args.max_frames)]
    else:
        extra = sorted(set(candidates) - {round(seconds, 9) for seconds in samples})
        remaining = args.max_frames - len(samples)
        extra = [extra[index] for index in evenly_spaced_indices(len(extra), remaining)] if remaining else []
        chosen = sorted(set(samples + extra))
    rows: list[dict[str, str]] = []
    seen: set[float] = set()
    with tempfile.TemporaryDirectory(prefix=".watch-frames-", dir=args.workdir) as temporary:
        stage = Path(temporary)
        frames = stage / "frames"
        selected = stage / "frames-selected"
        frames.mkdir()
        selected.mkdir()
        for requested in chosen:
            filename = f"frame_{len(rows) + 1:06d}.png"
            output = frames / filename
            actual = extract_frame(args.video, requested, origin, output)
            if actual is None:
                continue
            key = round(actual, 6)
            if key in seen or actual < args.start_sec - 1e-6 or actual >= end:
                output.unlink()
                continue
            seen.add(key)
            shutil.copy2(output, selected / filename)
            rows.append({
                "selected_frame": filename, "source_frame": filename,
                "seconds": f"{actual:.6f}", "timecode": format_timecode(actual),
                "requested_seconds": f"{requested:.6f}",
            })
        if not rows:
            raise RuntimeError("No readable video frames were extracted in the selected range.")
        with (stage / "scene_index.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        for name in ("frames", "frames-selected"):
            target = args.workdir / name
            if target.is_symlink():
                raise ValueError(f"Refusing to replace a linked output directory: {name}")
            if target.exists():
                shutil.rmtree(target)
            (stage / name).replace(target)
        (stage / "scene_index.csv").replace(args.workdir / "scene_index.csv")
    return {
        "duration_sec": duration, "range_start_sec": args.start_sec, "range_end_sec": end,
        "candidate_count": len(candidates), "selected_count": len(rows),
        "budget_limited": int(len(candidates) > args.max_frames),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--workdir", required=True, type=Path)
    parser.add_argument("--scene-threshold", type=float, default=0.30)
    parser.add_argument("--max-frames", type=int, default=150)
    parser.add_argument("--start-sec", type=float, default=0)
    parser.add_argument("--end-sec", type=float)
    parser.add_argument("--sample-interval", type=float)
    args = parser.parse_args()
    values = [args.start_sec, args.scene_threshold]
    values += [value for value in (args.end_sec, args.sample_interval) if value is not None]
    if not all(math.isfinite(value) for value in values):
        parser.error("Time and threshold values must be finite.")
    if args.start_sec < 0 or args.max_frames < 1 or not 0 <= args.scene_threshold <= 1:
        parser.error("Start time must be nonnegative, frame budget positive, and threshold between 0 and 1.")
    if args.end_sec is not None and args.end_sec <= args.start_sec:
        parser.error("--end-sec must be greater than --start-sec.")
    if args.sample_interval is not None and args.sample_interval <= 0:
        parser.error("--sample-interval must be positive.")
    try:
        coverage = prepare_frames(args)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        parser.exit(1, f"Frame preparation failed: {error}\n")
    (args.workdir / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(coverage))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
