# agent.py
"""AI Agent for generating responses to customer messages using Google Gemini."""

import logging
import os
from typing import Optional

from google import genai

from models import Business
from src.database_client import DatabaseClient
from src.services.calendar import (
    get_calendar_availability,
    format_availability_for_prompt,
)
from utils.constants import (
    CATEGORY_GREETING,
    CATEGORY_AVAILABILITY,
    CATEGORY_PRICING,
    BUSINESS_AI_VOICE_FIRST_PERSON,
    BUSINESS_AI_VOICE_NAME,
    BUSINESS_AI_VOICE_WE,
    OAUTH_PROVIDER_GOOGLE,
)
from utils.date_parser import extract_datetime_range
from prompts import GREETING_PROMPT, PRICING_PROMPT, AVAILABILITY_PROMPT

logger = logging.getLogger(__name__)

AI_DISCLAIMER = "\n\n---\n🤖 This response was AI generated"

FALLBACK_RESPONSE = "I'm sorry, I'm having trouble processing your request right now. Please try again later."

GEMINI_MODEL = "gemini-2.0-flash"

# Early return messages for AVAILABILITY when we can't proceed to Gemini
NO_DATE_RESPONSE = "I'd be happy to check availability! Could you let me know which date you're interested in?"

# =============================================================================
# AI AGENT
# =============================================================================


class AIAgent:
    """AI Agent for handling customer inquiries using Google Gemini."""

    def __init__(self):
        """
        Initialize agent with Gemini client and database client.

        Requires GOOGLE_ADK_API_KEY environment variable.
        """
        logger.info("Initializing AIAgent")

        self.db_client = DatabaseClient()

        api_key = os.getenv("GOOGLE_ADK_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_ADK_API_KEY not set - agent will return fallback responses")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized")

    def _get_voice_instruction(self, ai_voice: str) -> str:
        """Get voice instruction based on business ai_voice setting."""
        if ai_voice == BUSINESS_AI_VOICE_NAME:
            return "Professional and courteous, refer to the business in third person"
        elif ai_voice == BUSINESS_AI_VOICE_FIRST_PERSON:
            return "Friendly and casual, using 'I'"
        elif ai_voice == BUSINESS_AI_VOICE_WE:
            return "Friendly and casual, using 'we'"
        else:
            # Default to professional third person
            return "Professional and courteous, refer to the business in third person"

    def generate_response(
        self,
        message: str,
        classification: str,
        business: Business,
        availability_info: Optional[str] = None,
    ) -> str:
        """
        Generate response using Gemini based on message classification.

        Args:
            message: The customer's message text
            classification: GREETING, AVAILABILITY, or PRICING
            business: Business object with context
            availability_info: Formatted availability info for AVAILABILITY classification

        Returns:
            Generated response text, or fallback message on error
        """
        if not self.client:
            logger.error("Gemini client not initialized")
            return FALLBACK_RESPONSE

        # Build prompt based on classification
        prompt = self._build_prompt(message, classification, business, availability_info)

        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            response_text = response.text

            # Append AI disclaimer if enabled
            if business.show_ai_disclaimer:
                response_text += AI_DISCLAIMER

            return response_text
        except Exception as e:
            logger.error("Gemini API error: %s", e)
            return FALLBACK_RESPONSE

    def _build_prompt(
        self,
        message: str,
        classification: str,
        business: Business,
        availability_info: Optional[str] = None,
    ) -> str:
        """Build the appropriate prompt based on classification."""
        voice_instruction = self._get_voice_instruction(business.ai_voice)
        business_vertical = business.business_type or "business"

        if classification == CATEGORY_GREETING:
            return GREETING_PROMPT.format(
                business_name=business.business_name or "",
                business_vertical=business_vertical,
                business_description=business.business_description or "No description available",
                voice_instruction=voice_instruction,
                message=message
            )
        elif classification == CATEGORY_AVAILABILITY:
            return AVAILABILITY_PROMPT.format(
                business_name=business.business_name or "",
                business_vertical=business_vertical,
                voice_instruction=voice_instruction,
                message=message,
                availability_info=availability_info or "No availability information",
            )
        elif classification == CATEGORY_PRICING:
            return PRICING_PROMPT.format(
                business_name=business.business_name or "",
                business_vertical=business_vertical,
                voice_instruction=voice_instruction,
                message=message,
                pricing_info=business.pricing_packages or "No pricing information available"
            )
        else:
            # Fallback for unknown classification
            return f"Respond helpfully to this message: {message}"

    async def invoke_agent(
        self,
        category: str,
        message: str,
        business: Business
    ) -> str:
        """
        Invoke AI agent to generate response.

        Args:
            category: GREETING, AVAILABILITY, or PRICING
            message: The customer's message text
            business: Business object to respond for

        Returns:
            Generated response text
        """
        logger.info(
            "Invoking agent for category=%s, business_id=%s",
            category,
            business.id if business else None
        )

        # AVAILABILITY requires calendar lookup before calling Gemini
        if category == CATEGORY_AVAILABILITY:
            return await self._handle_availability(message, business)

        return self.generate_response(message, category, business)

    async def _handle_availability(self, message: str, business: Business) -> str:
        """
        Handle AVAILABILITY category with calendar lookup.

        Flow:
        1. Extract date/time from message
        2. If no date found, return early asking for a date
        3. Get OAuth token for user's Google Calendar
        4. Query FreeBusy API for availability
        5. Pass availability info to Gemini for response generation

        Args:
            message: The customer's message text
            business: Business object to respond for

        Returns:
            Generated response or early return message
        """
        # 1. Extract date from message
        date_range = extract_datetime_range(message)

        if date_range is None:
            logger.info("No date found in availability message, returning early")
            return NO_DATE_RESPONSE

        time_min, time_max = date_range
        logger.info("Extracted date range: %s to %s", time_min, time_max)

        # 2. Get OAuth token for this business's user
        oauth_token = self.db_client.get_oauth_token(business.user_id, OAUTH_PROVIDER_GOOGLE)

        if not oauth_token:
            logger.error("No Google Calendar OAuth token for user_id=%s", business.user_id)
            return

        # 3. Check calendar availability via FreeBusy API
        availability = get_calendar_availability(
            access_token=oauth_token.access_token,
            refresh_token=oauth_token.refresh_token,
            token_expiry=oauth_token.token_expiry,
            oauth_token_id=oauth_token.id,
            time_min=time_min,
            time_max=time_max,
        )

        if availability.error:
            logger.error("Calendar API error: %s", availability.error)
            return

        # 4. Format availability and generate response with Gemini
        availability_info = format_availability_for_prompt(availability)
        logger.info("Availability info: %s", availability_info)

        return self.generate_response(
            message=message,
            classification=CATEGORY_AVAILABILITY,
            business=business,
            availability_info=availability_info,
        )
