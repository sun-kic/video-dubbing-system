from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable, List

from backend.core.config import settings


class VideoProcessingError(RuntimeError):
    pass


class VideoProcessor:
    @staticmethod
    def _run(cmd: List[str]) -> str:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise VideoProcessingError(
                f"Command failed ({' '.join(cmd)}): {proc.stderr.strip()}"
            )
        return proc.stdout

    @classmethod
    def probe_duration(cls, media_path: str) -> float:
        cmd = [
            settings.FFPROBE_BIN,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            media_path,
        ]
        output = cls._run(cmd)
        try:
            payload = json.loads(output)
            return float(payload["format"]["duration"])
        except (KeyError, TypeError, ValueError) as exc:
            raise VideoProcessingError(f"Failed parsing ffprobe output for {media_path}") from exc

    @classmethod
    def extract_audio(cls, video_path: str, output_audio_path: str, sample_rate: int = 16000) -> str:
        out = Path(output_audio_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            settings.FFMPEG_BIN,
            "-y",
            "-i",
            video_path,
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(out),
        ]
        cls._run(cmd)
        return str(out)

    @classmethod
    def merge_audio_segments(cls, audio_paths: Iterable[str], output_path: str) -> str:
        audio_list = [Path(p) for p in audio_paths]
        if not audio_list:
            raise VideoProcessingError("No audio segments were provided")

        concat_file = Path(output_path).with_suffix(".txt")
        concat_file.parent.mkdir(parents=True, exist_ok=True)
        concat_file.write_text(
            "\n".join([f"file '{p.resolve()}'" for p in audio_list]),
            encoding="utf-8",
        )

        cmd = [
            settings.FFMPEG_BIN,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            output_path,
        ]
        try:
            cls._run(cmd)
        finally:
            concat_file.unlink(missing_ok=True)
        return output_path

    @classmethod
    def mux_video_with_audio(cls, video_path: str, dubbed_audio_path: str, output_video_path: str) -> str:
        out = Path(output_video_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            settings.FFMPEG_BIN,
            "-y",
            "-i",
            video_path,
            "-i",
            dubbed_audio_path,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ]
        cls._run(cmd)
        return str(out)
