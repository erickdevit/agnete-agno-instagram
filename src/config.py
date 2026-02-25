import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Validate required environment variables
def _validate_env_vars():
    """Validate that required environment variables are set."""
    required_vars = ["OPENAI_API_KEY", "NOCODB_API_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error("Missing required environment variables: %s", ", ".join(missing_vars))
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Warn if optional but important vars are not set
    if not os.getenv("INSTAGRAM_ACCESS_TOKEN"):
        logger.warning("INSTAGRAM_ACCESS_TOKEN not set - messages will not be sent")
    
    logger.info("Environment variables validated successfully")


# External APIs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOCODB_API_TOKEN = (os.getenv("NOCODB_API_TOKEN") or "").strip()
NOCODB_TABLE_URL = os.getenv("NOCODB_TABLE_URL", "")

# Instagram / Meta Graph API
INSTAGRAM_VERIFY_TOKEN = (os.getenv("INSTAGRAM_VERIFY_TOKEN") or "").strip()
INSTAGRAM_ACCESS_TOKEN = (os.getenv("INSTAGRAM_ACCESS_TOKEN") or "").strip()
INSTAGRAM_PAGE_ID = (os.getenv("INSTAGRAM_PAGE_ID") or "").strip()
INSTAGRAM_API_VERSION = os.getenv("INSTAGRAM_API_VERSION", "v25.0")

# Agent configs
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")
AGENT_NAME = os.getenv("AGENT_NAME", "Assistente_Instagram")
AUDIO_TRANSCRIPTION_MODEL = os.getenv("AUDIO_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe")
AUDIO_REPLY_MODEL = os.getenv("AUDIO_REPLY_MODEL", "gpt-4o-mini-tts")
AUDIO_REPLY_VOICE = os.getenv("AUDIO_REPLY_VOICE", "alloy")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
ENABLE_INSTAGRAM_AUDIO_REPLY = os.getenv("ENABLE_INSTAGRAM_AUDIO_REPLY", "false").lower() == "true"

# Infra
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Validate on import
try:
    _validate_env_vars()
except RuntimeError as e:
    logger.error("Configuration error: %s", e)
    raise
