import os
from dotenv import load_dotenv

load_dotenv()

# External APIs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NOCODB_API_TOKEN = os.getenv("NOCODB_API_TOKEN")

# Instagram / Meta Graph API
INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "my_verify_token")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_API_VERSION = os.getenv("INSTAGRAM_API_VERSION", "v25.0")

# Agent configs
AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")
AGENT_NAME = os.getenv("AGENT_NAME", "Assistente_Instagram")

# Infra
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
