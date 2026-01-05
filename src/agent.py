# agent.py
"""AI Agent for generating responses to customer messages using Google Gemini."""

import logging
import os

from google import genai

from models import Business
from utils.constants import (
    CATEGORY_GREETING,
    CATEGORY_AVAILABILITY,
    CATEGORY_PRICING,
    BUSINESS_AI_VOICE_FIRST_PERSON,
    BUSINESS_AI_VOICE_NAME,
    BUSINESS_AI_VOICE_WE,
)
from prompts import GREETING_PROMPT, PRICING_PROMPT, AVAILABILITY_PROMPT

logger = logging.getLogger(__name__)

AI_DISCLAIMER = "\n\n---\n🤖 This response was AI generated"

FALLBACK_RESPONSE = "I'm sorry, I'm having trouble processing your request right now. Please try again later."

GEMINI_MODEL = "gemini-2.0-flash"

# =============================================================================
# AI AGENT
# =============================================================================


class AIAgent:
    """AI Agent for handling customer inquiries using Google Gemini."""

    def __init__(self):
        """
        Initialize agent with Gemini client.

        Requires GOOGLE_ADK_API_KEY environment variable.
        """
        logger.info("Initializing AIAgent")

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
        business: Business
    ) -> str:
        """
        Generate response using Gemini based on message classification.

        Args:
            message: The customer's message text
            classification: GREETING, AVAILABILITY, or PRICING
            business: Business object with context

        Returns:
            Generated response text, or fallback message on error
        """
        if not self.client:
            logger.error("Gemini client not initialized")
            return FALLBACK_RESPONSE

        # Build prompt based on classification
        prompt = self._build_prompt(message, classification, business)

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
        business: Business
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
                availability_info="Calendar integration pending - assume available"
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

        return self.generate_response(message, category, business)
