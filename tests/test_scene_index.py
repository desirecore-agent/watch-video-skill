from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/watch/scripts/scene_index.py"


class SceneIndexTests(unittest.TestCase):
    def run_index(self, log_text: str, frame_names: list[str], max_frames: int) -> list[dict[str, str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            log_path = root / "scenes.log"
            frames_dir = root / "frames"
            selected_dir = root / "selected"
            output_path = root / "scene_index.csv"
            frames_dir.mkdir()
            log_path.write_text(log_text, encoding="utf-8")
            for name in frame_names:
                (frames_dir / name).write_bytes(b"synthetic-frame")

            subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--log",
                    str(log_path),
                    "--frames",
                    str(frames_dir),
                    "--selected",
                    str(selected_dir),
                    "--output",
                    str(output_path),
                    "--max-frames",
                    str(max_frames),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            with output_path.open(newline="", encoding="utf-8") as handle:
                return list(csv.DictReader(handle))

    def test_caps_selection_and_preserves_endpoints(self) -> None:
        rows = self.run_index(
            "[Parsed_showinfo] n:0 pts_time:0.000\n"
            "[Parsed_showinfo] n:1 pts_time:2.500\n"
            "[Parsed_showinfo] n:2 pts_time:5.000\n",
            ["frame_000001.png", "frame_000002.png", "frame_000003.png"],
            2,
        )
        self.assertEqual([row["source_frame"] for row in rows], ["frame_000001.png", "frame_000003.png"])
        self.assertEqual([row["timecode"] for row in rows], ["00:00:00.000", "00:00:05.000"])

    def test_fallback_first_frame_gets_zero_timestamp(self) -> None:
        rows = self.run_index(
            "",
            ["frame_000001.png"],
            150,
        )
        self.assertEqual(rows[0]["timecode"], "00:00:00.000")
        self.assertEqual(rows[0]["seconds"], "0.000")


if __name__ == "__main__":
    unittest.main()
