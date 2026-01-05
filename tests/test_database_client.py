"""Tests for database client operations."""

import pytest
import uuid
from unittest.mock import patch

from src.database_client import DatabaseClient


# ============================================================================
# USER OPERATION TESTS
# ============================================================================

def test_get_user_by_id(test_db, sample_user_active):
    """
    Test get_user_by_id function.

    Should verify:
    - Returns User object when user exists
    - Returns None when user does not exist
    """
    with patch('src.database_client.SessionLocal', return_value=test_db):
        client = DatabaseClient()

        # Test finding existing user
        result = client.get_user_by_id(sample_user_active.id)
        assert result is not None
        assert result.email == sample_user_active.email

        # Test user not found
        result = client.get_user_by_id(uuid.uuid4())
        assert result is None


def test_get_user_by_email(test_db, sample_user_active):
    """
    Test get_user_by_email function.

    Should verify:
    - Returns User object when user with email exists
    - Returns None when user with email does not exist
    """
    with patch('src.database_client.SessionLocal', return_value=test_db):
        client = DatabaseClient()

        # Test finding existing user
        result = client.get_user_by_email("test@example.com")
        assert result is not None
        assert result.id == sample_user_active.id

        # Test email not found
        result = client.get_user_by_email("nonexistent@example.com")
        assert result is None


# ============================================================================
# OAUTH TOKEN OPERATION TESTS
# ============================================================================

def test_get_oauth_token_google(test_db, sample_user_active, sample_google_oauth_token):
    """
    Test get_oauth_token function for Google Calendar token.

    Should verify:
    - Returns OAuthToken object when token exists for user and provider
    - Returns decrypted token data
    """
    def mock_decrypt(token):
        # Simulate decryption by removing "encrypted_" prefix
        if token and token.startswith("encrypted_"):
            return token.replace("encrypted_", "decrypted_")
        return token

    with patch('src.database_client.SessionLocal', return_value=test_db), \
         patch('src.database_client.decrypt_token', side_effect=mock_decrypt):
        client = DatabaseClient()

        # Test finding existing Google token with decryption
        result = client.get_oauth_token(sample_user_active.id, "GOOGLE_CALENDAR", decrypt=True)
        assert result is not None
        assert result.provider == "GOOGLE_CALENDAR"
        assert result.access_token == "decrypted_google_access_token"
        assert result.refresh_token == "decrypted_google_refresh_token"


def test_get_oauth_token_whatsapp(test_db, sample_user_active, sample_whatsapp_oauth_token):
    """
    Test get_oauth_token function for WhatsApp token.

    Should verify:
    - Returns OAuthToken object when token exists for user and provider
    - Returns decrypted token data
    """
    def mock_decrypt(token):
        # Simulate decryption by removing "encrypted_" prefix
        if token and token.startswith("encrypted_"):
            return token.replace("encrypted_", "decrypted_")
        return token

    with patch('src.database_client.SessionLocal', return_value=test_db), \
         patch('src.database_client.decrypt_token', side_effect=mock_decrypt):
        client = DatabaseClient()

        # Test finding existing WhatsApp token with decryption
        result = client.get_oauth_token(sample_user_active.id, "WHATSAPP", decrypt=True)
        assert result is not None
        assert result.provider == "WHATSAPP"
        assert result.access_token == "decrypted_whatsapp_access_token"
        assert result.refresh_token is None


def test_get_oauth_token_not_found(test_db):
    """
    Test get_oauth_token returns None when token does not exist.

    Should verify:
    - Returns None when no token exists for user/provider combination
    """
    with patch('src.database_client.SessionLocal', return_value=test_db):
        client = DatabaseClient()

        # Test token not found
        result = client.get_oauth_token(uuid.uuid4(), "GOOGLE_CALENDAR")
        assert result is None


# ============================================================================
# BUSINESS OPERATION TESTS
# ============================================================================

def test_get_business_by_user_id(test_db, sample_business):
    """
    Test get_business_by_user_id function.

    Should verify:
    - Returns Business object when business exists for user
    - Returns None when business does not exist
    """
    with patch('src.database_client.SessionLocal', return_value=test_db):
        client = DatabaseClient()

        # Test finding existing business
        result = client.get_business_by_user_id(sample_business.user_id)
        assert result is not None
        assert result.business_name == "Test Photography"

        # Test business not found
        result = client.get_business_by_user_id(uuid.uuid4())
        assert result is None


def test_get_business_by_whatsapp_number(test_db, sample_business):
    """
    Test get_business_by_whatsapp_number function.

    Should verify:
    - Returns Business object when business with WhatsApp number exists
    - Returns None when business with WhatsApp number does not exist
    """
    with patch('src.database_client.SessionLocal', return_value=test_db):
        client = DatabaseClient()

        # Test finding existing business
        result = client.get_business_by_whatsapp_number("+19292491619")
        assert result is not None
        assert result.business_name == "Test Photography"

        # Test number not found
        result = client.get_business_by_whatsapp_number("+10000000000")
        assert result is None


def test_get_business_by_whatsapp_account_id(test_db, sample_business):
    """
    Test looking up business by WhatsApp account ID.

    This function is called on every incoming webhook message to identify
    which business the message is for.

    Should verify:
    - Returns Business object when business with WhatsApp account ID exists and is ACTIVE
    - Returns None when business with WhatsApp account ID does not exist
    """
    with patch('src.database_client.SessionLocal', return_value=test_db):
        client = DatabaseClient()

        # Test finding existing active business
        result = client.get_business_by_whatsapp_account_id(sample_business.whatsapp_business_account_id)
        assert result is not None
        assert result.business_name == "Test Photography"
        assert result.workflow_status == "ACTIVE"


def test_get_business_ignores_inactive_workflows(test_db, inactive_business):
    """
    Test that inactive workflows are not returned.

    Should verify:
    - Returns None when business exists but workflow_status is INACTIVE
    - Only ACTIVE workflow_status businesses are returned
    """
    with patch('src.database_client.SessionLocal', return_value=test_db):
        client = DatabaseClient()

        # Test that inactive business returns None
        result = client.get_business_by_whatsapp_account_id(inactive_business.whatsapp_business_account_id)
        assert result is None


def test_get_business_not_found(test_db):
    """
    Test looking up non-existent business returns None.

    Should verify:
    - Returns None when business with account ID does not exist
    """
    with patch('src.database_client.SessionLocal', return_value=test_db):
        client = DatabaseClient()

        # Test with account ID that doesn't exist
        result = client.get_business_by_whatsapp_account_id("nonexistent_account_id")
        assert result is None
