from __future__ import annotations

import json
import math
import os
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path

from cli_anything.wavetone.utils import wavetone_backend


def make_wav(path: Path, freq: float = 440.0, duration: float = 0.5, sample_rate: int = 8000) -> Path:
    frames = int(duration * sample_rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for idx in range(frames):
            sample = int(16000 * math.sin(2 * math.pi * freq * idx / sample_rate))
            handle.writeframes(struct.pack("<h", sample))
    return path


def _resolve_cli(name: str) -> list[str]:
    """Resolve installed CLI command; fall back to python -m for development."""
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = "cli_anything.wavetone.wavetone_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-wavetone")

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(self.CLI_BASE + args, capture_output=True, text=True, check=check)

    def test_help(self) -> None:
        result = self._run(["--help"])
        assert "Agent-native CLI harness for WaveTone" in result.stdout

    def test_project_audio_workflow_json(self, tmp_path: Path) -> None:
        wav = make_wav(tmp_path / "tone.wav")
        project = tmp_path / "tone.wt.json"

        result = self._run(["--json", "project", "new", str(wav), "-o", str(project)])
        data = json.loads(result.stdout)
        assert data["ok"] is True
        assert project.exists()

        result = self._run(
            ["--project", str(project), "--json", "project", "set-tempo", "--bpm", "132.5", "--first-bar", "0.1"]
        )
        assert json.loads(result.stdout)["tempo"]["bpm"] == 132.5

        result = self._run(["--project", str(project), "--json", "project", "add-label", "intro", "--time", "0.25"])
        assert json.loads(result.stdout)["labels"][0]["name"] == "intro"

        result = self._run(["--project", str(project), "--json", "audio", "probe"])
        audio = json.loads(result.stdout)["audio"]
        assert audio["duration_seconds"] == 0.5
        assert audio["channels"] == 1
        print(f"\n  Project: {project}")
        print(f"  Audio: {wav} ({wav.stat().st_size:,} bytes)")

    def test_formats_json(self) -> None:
        result = self._run(["--json", "wavetone", "formats"])
        data = json.loads(result.stdout)
        assert ".wav" in data["formats"]["extensions"]
        assert "MP3" in data["formats"]["from_readme"]


class TestRealWaveToneBackend:
    CLI_BASE = _resolve_cli("cli-anything-wavetone")

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(self.CLI_BASE + args, capture_output=True, text=True, check=check)

    def test_doctor_real_backend(self) -> None:
        result = self._run(["--json", "wavetone", "doctor"])
        data = json.loads(result.stdout)
        assert data["ready"] is True
        assert any(check["name"] == "data/asdecoder.exe" and check["ok"] for check in data["checks"])
        print(f"\n  WaveTone root: {data['root']}")

    def test_launch_real_backend_with_wav(self, tmp_path: Path) -> None:
        exe = wavetone_backend.find_wavetone()
        wav = make_wav(tmp_path / "launch.wav")
        result = self._run(
            [
                "--json",
                "wavetone",
                "launch",
                str(wav),
                "--exe",
                str(exe),
                "--wait",
                "1",
                "--terminate",
            ]
        )
        data = json.loads(result.stdout)["launch"]
        assert data["backend"] == "wavetone.exe"
        assert data["audio_path"] == str(wav.resolve())
        assert data["running_after_wait"] is True
        assert data["terminated"] is True
        print(f"\n  Launched WaveTone PID: {data['pid']}")
        print(f"  WAV: {wav} ({wav.stat().st_size:,} bytes)")
