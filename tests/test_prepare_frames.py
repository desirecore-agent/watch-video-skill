from __future__ import annotations

import csv
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills/watch/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("prepare_frames", SCRIPTS / "prepare_frames.py")
frames = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frames)


class SamplingTests(unittest.TestCase):
    def test_default_preview_keeps_the_start_and_obeys_small_budget(self):
        self.assertEqual(frames.sample_times(0, 12, None, 2), [0, 6])

    def test_explicit_sampling_rejects_silent_coarsening(self):
        with self.assertRaisesRegex(ValueError, "above --max-frames"):
            frames.sample_times(0, 10, 0.1, 5)

    def test_sampling_respects_a_selected_range(self):
        actual = frames.sample_times(4, 5, 0.1, 10)
        self.assertEqual(len(actual), 10)
        self.assertAlmostEqual(actual[0], 4)
        self.assertAlmostEqual(actual[-1], 4.9)

    def test_integer_pts_avoids_rounded_showinfo_time(self):
        log = "config in time_base: 1/1000000, frame_rate: 10/1\nn:0 pts:5123456 pts_time:5.12346"
        self.assertEqual(frames.decoded_times(log), [5.123456])


class MediaRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.encoder = os.environ.get("WATCH_TEST_ENCODER") or shutil.which("ffmpeg")
        cls.decoder = os.environ.get("WATCH_TEST_DECODER") or shutil.which("ffmpeg")
        cls.probe = os.environ.get("WATCH_TEST_PROBE") or shutil.which("ffprobe")
        if not all((cls.encoder, cls.decoder, cls.probe)):
            raise unittest.SkipTest("Real-media regressions need ffmpeg and ffprobe")
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.environment = os.environ.copy()
        cls.environment["PATH"] = str(Path(cls.decoder).parent) + os.pathsep + cls.environment["PATH"]
        cls.video = cls.root / "recording.mp4"
        cls.static = cls.root / "static.mp4"
        cls.vfr = cls.root / "variable.mp4"
        cls.offset = cls.root / "offset.mp4"
        cls.encode(cls.video, "drawbox=x=50:y=40:w=60:h=20:color=red:t=fill:enable='between(t,1.2,1.5)'")
        cls.encode(cls.static, "null", duration=1)
        cls.encode(cls.vfr, "setpts='if(lt(N,10),N/(10*TB),(1+(N-10)/5)/TB)'")
        cls.encode(cls.offset, "null", extra=["-output_ts_offset", "5.123456"])

    @classmethod
    def encode(cls, target, video_filter, duration=3, extra=()):
        subprocess.run([
            cls.encoder, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
            f"color=c=white:s=160x90:r=10:d={duration}", "-vf", video_filter,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-fps_mode", "vfr", *extra, str(target),
        ], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def prepare(self, video, output, *options, success=True):
        output.mkdir(exist_ok=True)
        result = subprocess.run([
            sys.executable, str(SCRIPTS / "prepare_frames.py"), "--video", str(video),
            "--workdir", str(output), *options,
        ], env=self.environment, capture_output=True, text=True)
        if not success:
            self.assertNotEqual(result.returncode, 0)
            return result
        self.assertEqual(result.returncode, 0, result.stderr)
        with (output / "scene_index.csv").open(newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    def test_preview_includes_first_scene_and_brief_local_change(self):
        output = self.root / "preview"
        rows = self.prepare(self.video, output)
        self.assertEqual(float(rows[0]["seconds"]), 0)
        popup = next(row for row in rows if 1.2 <= float(row["seconds"]) <= 1.5)
        selected = output / "frames-selected"
        self.assertNotEqual((selected / rows[0]["selected_frame"]).read_bytes(),
                            (selected / popup["selected_frame"]).read_bytes())
        self.assertLessEqual(len(rows), 150)

    def test_dense_range_retains_source_timestamps(self):
        rows = self.prepare(self.video, self.root / "range", "--start-sec", "1.1", "--end-sec", "1.8",
                            "--sample-interval", "0.1", "--max-frames", "8")
        times = [float(row["seconds"]) for row in rows]
        self.assertTrue(all(1.1 - 1e-6 <= time < 1.8 for time in times))
        self.assertTrue(any(1.2 <= time <= 1.5 for time in times))
        self.assertLessEqual(len(rows), 8)

    def test_reusing_outputs_removes_stale_frames(self):
        output = self.root / "reused"
        self.prepare(self.video, output)
        rows = self.prepare(self.static, output)
        self.assertLessEqual(len(rows), 10)
        self.assertEqual(len(list((output / "frames").glob("*.png"))), len(rows))
        self.assertEqual(len(list((output / "frames-selected").glob("*.png"))), len(rows))
        self.assertTrue(all(float(row["seconds"]) < 1 for row in rows))

    def test_variable_rate_uses_decoded_pts_instead_of_requested_time(self):
        output = self.root / "vfr"
        rows = self.prepare(self.vfr, output, "--start-sec", "1", "--end-sec", "2.5",
                            "--sample-interval", "0.15", "--max-frames", "12")
        result = subprocess.run([
            self.probe, "-v", "error", "-select_streams", "v:0", "-show_entries",
            "frame=best_effort_timestamp_time", "-of", "json", str(self.vfr),
        ], check=True, capture_output=True, text=True)
        source_times = {round(float(frame["best_effort_timestamp_time"]), 6)
                        for frame in json.loads(result.stdout)["frames"]}
        self.assertTrue(all(round(float(row["seconds"]), 6) in source_times for row in rows))
        self.assertTrue(any(abs(float(row["seconds"]) - float(row["requested_seconds"])) > 0.01
                            for row in rows))

    def test_nonzero_source_origin_is_normalized_to_player_time(self):
        output = self.root / "offset"
        rows = self.prepare(self.offset, output)
        coverage = json.loads((output / "coverage.json").read_text())
        self.assertEqual(float(rows[0]["seconds"]), 0)
        self.assertAlmostEqual(coverage["duration_sec"], 3, places=1)

    def test_frame_budget_and_out_of_range_fail_clearly(self):
        result = self.prepare(self.video, self.root / "budget", "--sample-interval", "0.01",
                              "--max-frames", "3", success=False)
        self.assertIn("above --max-frames", result.stderr)
        result = self.prepare(self.video, self.root / "outside", "--start-sec", "9", success=False)
        self.assertIn("does not overlap", result.stderr)


if __name__ == "__main__":
    unittest.main()
