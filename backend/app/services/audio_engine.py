"""Audio transcription engine using whisper.cpp subprocess.

Handles:
- FFmpeg transcoding (MP3/OGG -> 16kHz WAV)
- whisper.cpp execution for speech-to-text
- Graceful degradation if either binary is missing
"""

import logging
import subprocess
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# Whisper binary and model paths (relative to backend/)
WHISPER_BINARY = Path("whisper.cpp/main")
WHISPER_MODEL = Path("whisper.cpp/models/ggml-base.en.bin")


def _check_binary(path: Path) -> bool:
    """Check if a binary exists and is executable."""
    return path.exists() and path.is_file()


def _check_ffmpeg() -> bool:
    """Check if FFmpeg is available on the system."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


# Check availability on module load
_ffmpeg_available = _check_ffmpeg()
_whisper_available = _check_binary(WHISPER_BINARY) and _check_binary(WHISPER_MODEL)

if not _ffmpeg_available:
    logger.warning(
        "FFmpeg not found on system PATH — audio transcription will be skipped"
    )
if not _whisper_available:
    logger.warning(
        "whisper.cpp binary or model not found — audio transcription will be skipped. "
        "Run 'make build-whisper' to set up."
    )


def transcribe_audio(audio_path: str, timeout: int = 60) -> str | None:
    """Transcribe an audio file to text using FFmpeg + whisper.cpp.

    Args:
        audio_path: Path to the audio file (MP3, OGG, WAV, etc.)
        timeout: Maximum seconds for each subprocess call

    Returns:
        Transcript string, or None if transcription fails/is unavailable
    """
    if not _ffmpeg_available or not _whisper_available:
        logger.info(
            "Audio transcription skipped (ffmpeg=%s, whisper=%s)",
            _ffmpeg_available,
            _whisper_available,
        )
        return None

    source = Path(audio_path)
    if not source.exists():
        logger.warning("Audio file not found: %s", audio_path)
        return None

    # Create temporary WAV file
    tmp_wav = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}.wav"

    try:
        # Step 1: Transcode to 16kHz mono WAV
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", str(source),
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-y",  # Overwrite
            str(tmp_wav),
        ]
        logger.info("Running FFmpeg: %s", " ".join(ffmpeg_cmd))
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.error("FFmpeg failed: %s", result.stderr[:500])
            return None

        # Step 2: Run whisper.cpp
        whisper_cmd = [
            str(WHISPER_BINARY),
            "-m", str(WHISPER_MODEL),
            "-f", str(tmp_wav),
            "-nt",  # No timestamps
        ]
        logger.info("Running whisper.cpp: %s", " ".join(whisper_cmd))
        result = subprocess.run(
            whisper_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            logger.error("whisper.cpp failed: %s", result.stderr[:500])
            return None

        transcript = result.stdout.strip()
        logger.info(
            "Transcription complete (%d chars): %s...",
            len(transcript),
            transcript[:100],
        )
        return transcript if transcript else None

    except subprocess.TimeoutExpired:
        logger.error("Audio transcription timed out after %ds", timeout)
        return None
    except Exception:
        logger.exception("Unexpected error during audio transcription")
        return None
    finally:
        # Cleanup temporary WAV
        if tmp_wav.exists():
            tmp_wav.unlink()
            logger.debug("Cleaned up temp WAV: %s", tmp_wav)
