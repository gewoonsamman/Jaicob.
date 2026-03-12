"""Configuration loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

JAICOB_API_KEY = os.environ.get("JAICOB_API_KEY", "")
JAICOB_BASE_URL = os.environ.get("JAICOB_BASE_URL", "https://api.jaicob.ai")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
NOTIFICATION_EMAIL = os.environ.get("NOTIFICATION_EMAIL", "")
DEFAULT_LANGUAGE = "nl"
