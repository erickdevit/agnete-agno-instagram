import sys
from unittest.mock import MagicMock

# Mock external dependencies that are not installed in the environment
mock_modules = [
    "fastapi",
    "fastapi.responses",
    "pydantic",
    "src.config",
    "src.agent",
    "src.api.instagram",
    "src.api.transcription",
    "src.api.scope_classifier",
    "src.api.audio_reply",
    "src.models",
    "src.interaction_blocker",
    "dotenv",
]

for module in mock_modules:
    sys.modules[module] = MagicMock()

# Now we can import the function under test
from src.api.webhook import _extract_audio_url

def test_extract_audio_url_empty_list():
    assert _extract_audio_url([]) == ""

def test_extract_audio_url_none():
    assert _extract_audio_url(None) == ""

def test_extract_audio_url_audio_success():
    attachments = [
        {
            "type": "audio",
            "payload": {"url": "https://example.com/audio.mp3"}
        }
    ]
    assert _extract_audio_url(attachments) == "https://example.com/audio.mp3"

def test_extract_audio_url_file_success():
    attachments = [
        {
            "type": "file",
            "payload": {"url": "https://example.com/file.m4a"}
        }
    ]
    assert _extract_audio_url(attachments) == "https://example.com/file.m4a"

def test_extract_audio_url_image_ignored():
    attachments = [
        {
            "type": "image",
            "payload": {"url": "https://example.com/image.png"}
        }
    ]
    assert _extract_audio_url(attachments) == ""

def test_extract_audio_url_multiple_attachments():
    attachments = [
        {
            "type": "image",
            "payload": {"url": "https://example.com/image.png"}
        },
        {
            "type": "audio",
            "payload": {"url": "https://example.com/audio.mp3"}
        }
    ]
    assert _extract_audio_url(attachments) == "https://example.com/audio.mp3"

def test_extract_audio_url_missing_payload():
    attachments = [{"type": "audio"}]
    assert _extract_audio_url(attachments) == ""

def test_extract_audio_url_missing_url_in_payload():
    attachments = [{"type": "audio", "payload": {}}]
    assert _extract_audio_url(attachments) == ""

def test_extract_audio_url_invalid_attachment_format():
    attachments = ["not a dict", {"type": "audio", "payload": {"url": "http://url"}}]
    assert _extract_audio_url(attachments) == "http://url"

def test_extract_audio_url_payload_is_none():
    attachments = [{"type": "audio", "payload": None}]
    assert _extract_audio_url(attachments) == ""
