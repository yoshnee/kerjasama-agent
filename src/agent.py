"""Gemini-powered chat agent."""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

from google import genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Business, OAuthToken
from src.prompt import build_system_prompt
from src.services.calendar import get_calendar_availability, format_availability
from utils.crypto import decrypt_token

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"

FALLBACK_RESPONSE = {
    "reply": "I'm sorry, I'm having trouble right now. Please try again later.",
    "show_whatsapp_cta": True,
}


class ChatAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    async def generate_response(
        self,
        message: str,
        history: list,
        business: Business,
        db: AsyncSession,
    ) -> dict:
        if not self.client:
            return FALLBACK_RESPONSE

        availability_text = await self._get_availability(business, db)
        system_prompt = build_system_prompt(business, availability_text)

        # Build conversation contents for Gemini
        contents = []
        for msg in history:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config={
                    "system_instruction": system_prompt,
                    "response_mime_type": "application/json",
                },
            )
            parsed = json.loads(response.text)
            return {
                "reply": parsed.get("reply", FALLBACK_RESPONSE["reply"]),
                "show_whatsapp_cta": parsed.get("show_whatsapp_cta", False),
            }
        except Exception as e:
            logger.error("Gemini error: %s", e)
            return FALLBACK_RESPONSE

    async def _get_availability(self, business: Business, db: AsyncSession) -> str:
        try:
            result = await db.execute(
                select(OAuthToken).where(OAuthToken.user_id == business.user_id)
            )
            oauth_token = result.scalar_one_or_none()
            if not oauth_token:
                logger.warning("No oauth_token found for user_id=%s", business.user_id)
                return "CALENDAR_UNAVAILABLE"

            logger.info(
                "OAuth token found: id=%s, has_access=%s, has_refresh=%s, expires_at=%s",
                oauth_token.id,
                bool(oauth_token.access_token),
                bool(oauth_token.refresh_token),
                oauth_token.expires_at,
            )

            access_token = decrypt_token(oauth_token.access_token)
            refresh_token = decrypt_token(oauth_token.refresh_token) if oauth_token.refresh_token else None

            if not access_token:
                logger.error("Failed to decrypt access token for user_id=%s", business.user_id)
                return "CALENDAR_UNAVAILABLE"

            logger.info("Tokens decrypted successfully, fetching calendar for next 365 days")

            now = datetime.now(timezone.utc)
            time_max = now + timedelta(days=365)

            cal_result = await get_calendar_availability(
                access_token=access_token,
                refresh_token=refresh_token,
                token_expiry=oauth_token.expires_at,
                oauth_token_id=oauth_token.id,
                time_min=now,
                time_max=time_max,
                db=db,
            )

            if cal_result.error:
                logger.error("Calendar fetch error: %s", cal_result.error)

            return format_availability(cal_result)
        except Exception as e:
            logger.error("Failed to get availability: %s", e, exc_info=True)
            return "CALENDAR_UNAVAILABLE"
