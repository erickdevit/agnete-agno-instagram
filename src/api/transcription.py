"""
Audio transcription helper for Instagram webhook attachments.
"""
import asyncio
import logging
import mimetypes
import os
import subprocess
import tempfile
from typing import Optional

import httpx
from openai import BadRequestError, OpenAI

from src.config import (
    AUDIO_TRANSCRIPTION_MODEL,
    INSTAGRAM_ACCESS_TOKEN,
    MAX_TRANSCRIPTION_AUDIO_MB,
    MAX_TRANSCRIPTION_AUDIO_SECONDS,
    OPENAI_API_KEY,
)

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = MAX_TRANSCRIPTION_AUDIO_MB * 1024 * 1024


def _guess_suffix(content_type: str) -> str:
    base_type = (content_type or "").split(";")[0].strip().lower()
    guessed = mimetypes.guess_extension(base_type) if base_type else None
    return guessed or ".m4a"


def _extract_transcription_text(result) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if hasattr(result, "text"):
        return (getattr(result, "text", "") or "").strip()
    if isinstance(result, dict):
        return (result.get("text", "") or "").strip()
    return ""


def _transcribe_audio_bytes(audio_bytes: bytes, suffix: str, model: str = AUDIO_TRANSCRIPTION_MODEL) -> str:
    client = OpenAI(api_key=OPENAI_API_KEY)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        with open(tmp.name, "rb") as audio_file:
            result = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
            )
    return _extract_transcription_text(result)


def _convert_audio_to_wav(audio_bytes: bytes, suffix: str) -> bytes:
    """
    Convert arbitrary audio bytes to WAV mono 16kHz using ffmpeg.
    Raises on conversion failures.
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as source_tmp:
        source_tmp.write(audio_bytes)
        source_path = source_tmp.name

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as target_tmp:
        target_path = target_tmp.name

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                source_path,
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                target_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        with open(target_path, "rb") as wav_file:
            return wav_file.read()
    finally:
        for path in (source_path, target_path):
            try:
                os.remove(path)
            except OSError:
                pass


def _get_audio_duration_seconds(audio_bytes: bytes, suffix: str) -> Optional[float]:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        source_path = tmp.name
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                source_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        raw = (proc.stdout or "").strip()
        return float(raw) if raw else None
    except Exception:
        return None
    finally:
        try:
            os.remove(source_path)
        except OSError:
            pass


async def transcribe_audio_from_url(audio_url: str, sender_id: str) -> Optional[str]:
    """
    Download an Instagram audio attachment URL and transcribe it with OpenAI.
    Returns None when download/transcription fails.
    """
    short_id = sender_id[-6:] if sender_id else "unknown"
    headers = {}
    if INSTAGRAM_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {INSTAGRAM_ACCESS_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(audio_url, headers=headers or None)
            if response.status_code in (401, 403) and headers:
                # Some attachment URLs are public signed links; retry without auth header.
                response = await client.get(audio_url)
            response.raise_for_status()
            audio_bytes = response.content
            content_type = response.headers.get("content-type", "")
    except Exception as exc:
        logger.error("[%s] Failed to download audio attachment: %s", short_id, exc)
        return None

    if not audio_bytes:
        logger.warning("[%s] Empty audio attachment", short_id)
        return None

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        logger.warning("[%s] Audio too large for transcription (%d bytes)", short_id, len(audio_bytes))
        return None

    suffix = _guess_suffix(content_type)
    wav_bytes = None
    try:
        wav_bytes = await asyncio.to_thread(_convert_audio_to_wav, audio_bytes, suffix)
    except FileNotFoundError:
        logger.error("[%s] ffmpeg not found in container; trying direct transcription", short_id)
    except Exception as exc:
        logger.warning("[%s] Audio conversion failed, trying direct transcription: %s", short_id, exc)

    transcribe_bytes = wav_bytes if wav_bytes else audio_bytes
    transcribe_suffix = ".wav" if wav_bytes else suffix
    duration_seconds = await asyncio.to_thread(_get_audio_duration_seconds, transcribe_bytes, transcribe_suffix)
    if duration_seconds and duration_seconds > MAX_TRANSCRIPTION_AUDIO_SECONDS:
        logger.warning(
            "[%s] Audio too long for transcription (%.1fs > %ss)",
            short_id,
            duration_seconds,
            MAX_TRANSCRIPTION_AUDIO_SECONDS,
        )
        return None

    try:
        transcription = await asyncio.to_thread(
            _transcribe_audio_bytes, transcribe_bytes, transcribe_suffix, AUDIO_TRANSCRIPTION_MODEL
        )
        if transcription:
            return transcription
        if AUDIO_TRANSCRIPTION_MODEL != "whisper-1":
            logger.warning("[%s] Empty transcription with %s, trying whisper-1", short_id, AUDIO_TRANSCRIPTION_MODEL)
            fallback = await asyncio.to_thread(
                _transcribe_audio_bytes, transcribe_bytes, transcribe_suffix, "whisper-1"
            )
            if fallback:
                return fallback
        return None
    except BadRequestError as exc:
        logger.error("[%s] Audio transcription rejected: %s", short_id, exc)
        return None
    except Exception as exc:
        logger.error("[%s] Audio transcription failed: %s", short_id, exc, exc_info=True)
        return None
