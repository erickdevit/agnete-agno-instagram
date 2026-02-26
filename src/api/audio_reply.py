"""
Generate short audio replies and expose temporary files for Instagram attachment URL.
"""
import asyncio
import logging
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from openai import OpenAI

from src.config import (
    AUDIO_REPLY_MODEL,
    AUDIO_REPLY_VOICE,
    MAX_AUDIO_REPLY_CHARS,
    OPENAI_API_KEY,
    PUBLIC_BASE_URL,
)

logger = logging.getLogger(__name__)

AUDIO_REPLY_DIR = Path(tempfile.mkdtemp(prefix="vsimple_audio_replies_"))
AUDIO_REPLY_TTL_SECONDS = 900


def _cleanup_expired_files() -> None:
    now = time.time()
    AUDIO_REPLY_DIR.mkdir(parents=True, exist_ok=True)
    for pattern in ("*.mp3", "*.wav"):
        for file in AUDIO_REPLY_DIR.glob(pattern):
            try:
                if now - file.stat().st_mtime > AUDIO_REPLY_TTL_SECONDS:
                    file.unlink(missing_ok=True)
            except OSError:
                continue


def _trim_for_five_seconds(text: str) -> str:
    cleaned = " ".join((text or "").strip().split())
    if len(cleaned) <= MAX_AUDIO_REPLY_CHARS:
        return cleaned
    clipped = cleaned[:MAX_AUDIO_REPLY_CHARS].rstrip(" ,.;:!?")
    return clipped + "."


def _convert_to_wav(input_path: Path, output_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(output_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def _synthesize_to_wav_file(text: str, output_path: Path) -> None:
    client = OpenAI(api_key=OPENAI_API_KEY)
    temp_mp3 = output_path.with_suffix(".mp3")
    try:
        with client.audio.speech.with_streaming_response.create(
            model=AUDIO_REPLY_MODEL,
            voice=AUDIO_REPLY_VOICE,
            input=text,
            response_format="mp3",
        ) as response:
            response.stream_to_file(str(temp_mp3))
    except TypeError:
        # Compatibility fallback for older OpenAI SDK versions.
        with client.audio.speech.with_streaming_response.create(
            model=AUDIO_REPLY_MODEL,
            voice=AUDIO_REPLY_VOICE,
            input=text,
        ) as response:
            response.stream_to_file(str(temp_mp3))
    _convert_to_wav(temp_mp3, output_path)
    try:
        temp_mp3.unlink(missing_ok=True)
    except OSError:
        pass


async def create_audio_reply_url(text: str) -> Optional[str]:
    """
    Creates a WAV from text and returns a public URL for Instagram attachment.
    Returns None if PUBLIC_BASE_URL is not configured or synthesis fails.
    """
    if not PUBLIC_BASE_URL:
        return None

    _cleanup_expired_files()
    AUDIO_REPLY_DIR.mkdir(parents=True, exist_ok=True)

    safe_text = _trim_for_five_seconds(text)
    if not safe_text:
        return None

    file_name = f"{uuid.uuid4().hex}.wav"
    output_path = AUDIO_REPLY_DIR / file_name

    try:
        await asyncio.to_thread(_synthesize_to_wav_file, safe_text, output_path)
    except Exception as exc:
        logger.error("Failed to synthesize audio reply: %s", exc, exc_info=True)
        return None

    base = PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/media/audio/{file_name}"


def resolve_audio_file(file_name: str) -> Optional[Path]:
    """
    Safely resolves a generated audio file from temp directory.
    """
    if not file_name.endswith(".wav"):
        return None
    if "/" in file_name or ".." in file_name:
        return None
    candidate = AUDIO_REPLY_DIR / file_name
    if not candidate.exists():
        return None
    return candidate
