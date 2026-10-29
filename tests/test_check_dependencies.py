from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/watch/scripts"
CHECK = SCRIPTS / "check_dependencies.sh"
PREPARE = SCRIPTS / "prepare_video.sh"
BASH = shutil.which("bash") or "/bin/bash"


class CheckDependenciesTests(unittest.TestCase):
    """Runs the scripts with a PATH that holds only stub commands."""

    def make_path(self, commands: list[str], system: str = "Darwin", tools: list[str] | None = None) -> str:
        bin_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, bin_dir)
        for name in commands:
            stub = bin_dir / name
            stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            stub.chmod(0o755)
        uname = bin_dir / "uname"
        uname.write_text(f"#!/bin/sh\necho {system}\n", encoding="utf-8")
        uname.chmod(0o755)
        for name in tools or []:
            target = shutil.which(name)
            self.assertIsNotNone(target, f"{name} is required to run this test")
            os.symlink(target, bin_dir / name)
        return str(bin_dir)

    def run_script(self, script: Path, args: list[str], path: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [BASH, str(script), *args],
            env={"PATH": path},
            capture_output=True,
            text=True,
            check=False,
        )

    def test_url_input_reports_missing_yt_dlp_with_a_platform_install_command(self) -> None:
        path = self.make_path(["ffmpeg", "ffprobe", "python3", "deno", "brew"])
        result = self.run_script(CHECK, ["--url"], path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing  yt-dlp (required)", result.stdout)
        self.assertIn("brew install yt-dlp", result.stderr)
        self.assertIn("https://github.com/yt-dlp/yt-dlp/wiki/Installation", result.stderr)

    def test_windows_hint_uses_winget(self) -> None:
        path = self.make_path(["ffmpeg", "ffprobe", "python3", "deno"], system="MINGW64_NT-10.0-26100")
        result = self.run_script(CHECK, ["--url"], path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("winget install yt-dlp.yt-dlp", result.stderr)

    def test_local_input_does_not_need_yt_dlp_or_deno(self) -> None:
        path = self.make_path(["ffmpeg", "ffprobe", "python3"])
        result = self.run_script(CHECK, ["--local"], path)
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("yt-dlp", result.stdout + result.stderr)
        self.assertNotIn("deno", result.stdout + result.stderr)

    def test_missing_deno_is_recommended_but_does_not_fail(self) -> None:
        path = self.make_path(["yt-dlp", "ffmpeg", "ffprobe", "python3", "brew"])
        result = self.run_script(CHECK, ["--url"], path)
        self.assertEqual(result.returncode, 0)
        self.assertIn("missing  deno (recommended for YouTube)", result.stdout)
        self.assertIn("brew install deno", result.stdout)
        self.assertIn("Dependency check passed for url input.", result.stdout)

    def test_missing_ffmpeg_and_ffprobe_share_one_hint(self) -> None:
        path = self.make_path(["yt-dlp", "python3", "deno"])
        result = self.run_script(CHECK, ["--url"], path)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr.count("brew install ffmpeg"), 1)

    def test_prepare_stops_at_the_dependency_check_before_downloading(self) -> None:
        path = self.make_path(["ffmpeg", "ffprobe", "python3"], tools=["bash", "dirname", "mkdir"])
        with tempfile.TemporaryDirectory() as work_dir:
            result = self.run_script(
                PREPARE,
                ["--url", "https://example.com/video", "--workdir", work_dir],
                path,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing  yt-dlp (required)", result.stdout)
        self.assertNotIn("Attempting subtitles", result.stdout)


if __name__ == "__main__":
    unittest.main()
