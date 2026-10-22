"""Telegram notification service via Telegram Bot API."""

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TelegramService:
    def __init__(self, bot_token: str | None = None) -> None:
        self.bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.bot_token.strip())

    async def send_message(self, chat_id: str | int, text: str) -> bool:
        """Send a markdown message to a Telegram chat. Graceful fallback if disabled."""
        if not self.is_configured:
            logger.debug("Telegram notifications disabled: TELEGRAM_BOT_TOKEN not configured.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    logger.info("Telegram notification sent successfully", chat_id=chat_id)
                    return True
                else:
                    logger.warning(
                        "Telegram API responded with error",
                        status_code=response.status_code,
                        body=response.text,
                    )
                    return False
        except Exception as exc:
            logger.warning("Failed to deliver Telegram notification", error=str(exc))
            return False
