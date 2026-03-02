from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Iterable, List, Tuple

from backend.core.config import settings
from backend.core.logging import logger


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
    def extract_audio_segment(
        cls, audio_path: str, output_path: str, start: float, duration: float, sample_rate: int = 16000
    ) -> str:
        """Extract a time-ranged segment from an audio file."""
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            settings.FFMPEG_BIN,
            "-y",
            "-i", audio_path,
            "-ss", str(start),
            "-t", str(duration),
            "-ac", "1",
            "-ar", str(sample_rate),
            "-c:a", "pcm_s16le",
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
    def separate_vocals(cls, audio_path: str, output_dir: str) -> Tuple[str, str]:
        """
        Use Demucs to separate vocals and background music.

        Returns:
            (vocals_path, background_path)
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        stem = Path(audio_path).stem
        cmd = [
            "demucs",
            "--two-stems", "vocals",
            "-o", str(out),
            str(audio_path),
        ]
        logger.info("Running Demucs: %s", " ".join(cmd))
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise VideoProcessingError(f"Demucs failed: {proc.stderr.strip()}")

        vocals_path = out / "htdemucs" / stem / "vocals.wav"
        background_path = out / "htdemucs" / stem / "no_vocals.wav"

        if not vocals_path.exists():
            raise VideoProcessingError(
                f"Demucs output not found at {vocals_path}. "
                f"Files in output: {list((out / 'htdemucs').rglob('*.wav'))}"
            )

        logger.info("Demucs done: vocals=%s background=%s", vocals_path, background_path)
        return str(vocals_path), str(background_path)

    @classmethod
    def mix_dubbed_with_background(
        cls,
        segment_audio_pairs: List[Tuple[float, str]],
        background_path: str,
        output_path: str,
        bg_volume_db: float = -8.0,
    ) -> str:
        """
        Mix TTS dubbed segments (placed at correct timestamps) with the background
        music/SFX track, using pydub.

        Args:
            segment_audio_pairs: List of (start_seconds, tts_wav_path)
            background_path: Path to background audio (Demucs no_vocals.wav)
            output_path: Output mixed WAV path
            bg_volume_db: Background volume adjustment in dB (negative = quieter)
        """
        try:
            from pydub import AudioSegment
        except ImportError as exc:
            raise RuntimeError("pydub is not installed. Run: pip install pydub") from exc

        logger.info("Loading background audio: %s", background_path)
        background = AudioSegment.from_file(background_path)
        total_ms = len(background)

        # Build a silent voiceover track of the same length
        voiceover_track = AudioSegment.silent(duration=total_ms)

        logger.info("Overlaying %d TTS segments onto voiceover track", len(segment_audio_pairs))
        for idx, (start_sec, tts_path) in enumerate(segment_audio_pairs):
            try:
                seg_audio = AudioSegment.from_file(tts_path)
                start_ms = int(start_sec * 1000)
                voiceover_track = voiceover_track.overlay(seg_audio, position=start_ms)
            except Exception as exc:
                logger.warning("Failed to overlay segment %d (%s): %s", idx, tts_path, exc)

        # Reduce background volume then mix
        quieter_bg = background + bg_volume_db
        final_mix = quieter_bg.overlay(voiceover_track)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        final_mix.export(output_path, format="wav")
        logger.info("Mixed audio saved: %s", output_path)
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
