# database_client.py
"""
Database client with reusable CRUD operations.
Separates database logic from route handlers.

Each method manages its own database session to ensure proper cleanup.
"""

import logging
from typing import Optional
import uuid

from src.database import SessionLocal
from models import User, OAuthToken, Business
from utils.constants import BUSINESS_WORKFLOW_STATUS_ACTIVE
from utils.crypto import decrypt_token

logger = logging.getLogger(__name__)


class DatabaseClient:
    """
    Database client for kerjasama-agent.

    Lightweight client - each method creates and closes its own session.
    Safe to instantiate per-request.
    """

    # =========================================================================
    # USER OPERATIONS
    # =========================================================================

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User's UUID

        Returns:
            User object if found, None otherwise
        """
        db = SessionLocal()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Args:
            email: User's email address

        Returns:
            User object if found, None otherwise
        """
        db = SessionLocal()
        try:
            return db.query(User).filter(User.email == email).first()
        finally:
            db.close()

    # =========================================================================
    # OAUTH TOKEN OPERATIONS
    # =========================================================================

    def get_oauth_token(
        self,
        user_id: uuid.UUID,
        provider: str,
        decrypt: bool = True
    ) -> Optional[OAuthToken]:
        """
        Get OAuth token for a user and provider.

        Args:
            user_id: User's UUID
            provider: Provider name (GOOGLE_CALENDAR, WHATSAPP)
            decrypt: Whether to decrypt tokens (default: True)

        Returns:
            OAuthToken object if found, None otherwise
        """
        db = SessionLocal()
        try:
            token = db.query(OAuthToken).filter(
                OAuthToken.user_id == user_id,
                OAuthToken.provider == provider
            ).first()

            if token and decrypt:
                # Decrypt tokens before returning
                token.access_token = decrypt_token(token.access_token)
                if token.refresh_token:
                    token.refresh_token = decrypt_token(token.refresh_token)

            return token
        finally:
            db.close()

    # =========================================================================
    # BUSINESS OPERATIONS
    # =========================================================================

    def get_business_by_user_id(self, user_id: uuid.UUID) -> Optional[Business]:
        """
        Get business for a user.

        Args:
            user_id: User's UUID

        Returns:
            Business object if found, None otherwise
        """
        db = SessionLocal()
        try:
            return db.query(Business).filter(Business.user_id == user_id).first()
        finally:
            db.close()

    def get_business_by_whatsapp_number(self, whatsapp_number: str) -> Optional[Business]:
        """
        Get business by WhatsApp phone number.

        Args:
            whatsapp_number: WhatsApp business phone number

        Returns:
            Business object if found, None otherwise
        """
        db = SessionLocal()
        try:
            return db.query(Business).filter(
                Business.whatsapp_number == whatsapp_number
            ).first()
        finally:
            db.close()

    def get_business_by_whatsapp_account_id(self, whatsapp_business_account_id: str) -> Optional[Business]:
        """
        Get Active business by WhatsApp Business Account ID.

        Only returns business if workflow is ACTIVE.
        Inactive businesses will not have messages processed.

        This is called on every incoming webhook message to identify which business
        the message is for.

        Args:
            whatsapp_business_account_id: WhatsApp Business Account ID from webhook

        Returns:
            Business object if found and ACTIVE, None otherwise
        """
        db = SessionLocal()
        try:
            # First check if business exists at all
            business = db.query(Business).filter(
                Business.whatsapp_business_account_id == whatsapp_business_account_id
            ).first()

            if not business:
                logger.error("Business not found for WhatsApp account ID: %s", whatsapp_business_account_id)
                return None

            # Check if workflow is active
            if business.workflow_status != BUSINESS_WORKFLOW_STATUS_ACTIVE:
                logger.info(
                    "Business %s found but workflow is inactive (status: %s)",
                    business.id,
                    business.workflow_status
                )
                return None

            return business
        finally:
            db.close()
