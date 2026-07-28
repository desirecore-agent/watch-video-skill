#!/usr/bin/env python3
"""Build a bounded timestamp index for scene-change frames."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
from pathlib import Path


PTS_PATTERN = re.compile(r"\bpts_time:([0-9]+(?:\.[0-9]+)?)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--frames", required=True, type=Path)
    parser.add_argument("--selected", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-frames", type=int, default=150)
    return parser.parse_args()


def evenly_spaced_indices(total: int, limit: int) -> list[int]:
    if total <= limit:
        return list(range(total))
    if limit == 1:
        return [0]
    return sorted(
        {round(position * (total - 1) / (limit - 1)) for position in range(limit)}
    )


def format_timecode(seconds: float | None) -> str:
    if seconds is None:
        return ""
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{millis:03d}"


def main() -> int:
    args = parse_args()
    if args.max_frames < 1:
        raise SystemExit("--max-frames must be at least 1")

    frames = sorted(args.frames.glob("frame_*.png"))
    timestamps = [
        float(match.group(1))
        for match in PTS_PATTERN.finditer(args.log.read_text(errors="replace"))
    ]

    args.selected.mkdir(parents=True, exist_ok=True)
    for old_file in args.selected.glob("frame_*.png"):
        old_file.unlink()

    chosen = evenly_spaced_indices(len(frames), args.max_frames)
    rows: list[dict[str, str]] = []
    for selected_number, frame_index in enumerate(chosen, start=1):
        source = frames[frame_index]
        target = args.selected / f"frame_{selected_number:06d}.png"
        shutil.copy2(source, target)
        seconds = timestamps[frame_index] if frame_index < len(timestamps) else None
        rows.append(
            {
                "selected_frame": target.name,
                "source_frame": source.name,
                "seconds": "" if seconds is None else f"{seconds:.3f}",
                "timecode": format_timecode(seconds),
            }
        )

    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["selected_frame", "source_frame", "seconds", "timecode"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"indexed={len(frames)} selected={len(rows)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
