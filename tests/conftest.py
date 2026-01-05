"""Shared pytest fixtures for all test modules."""

import pytest
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.user import Base
from models import User, Business, OAuthToken
from utils.constants import (
    BUSINESS_WORKFLOW_STATUS_ACTIVE,
    BUSINESS_WORKFLOW_STATUS_DISABLED,
    USER_STATUS_ACTIVE,
    USER_STATUS_SUSPENDED,
    OAUTH_PROVIDER_GOOGLE,
    OAUTH_PROVIDER_WHATSAPP,
)


@pytest.fixture(scope="session")
def test_config() -> dict:
    """
    Provide test configuration shared across all test sessions.

    Returns configuration values used across multiple test files.
    """
    return {
        "test_timeout": 30,
        "mock_whatsapp_token": "test_verify_token",
        "mock_database_url": "postgresql://test:test@localhost:5432/test_db",
    }


@pytest.fixture(scope="function")
def test_db():
    """
    Create in-memory SQLite database for testing.

    Creates fresh database for each test function to ensure isolation.
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session factory
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create and yield session
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def sample_user_active(test_db):
    """Create a sample user for testing."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        status=USER_STATUS_ACTIVE
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def sample_user_inactive(test_db):
    """Create a sample user for testing."""
    user = User(
        id=uuid.uuid4(),
        email="test2@example.com",
        status=USER_STATUS_SUSPENDED
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def sample_business(test_db, sample_user_active):
    """Create a sample active business for testing."""
    business = Business(
        id=uuid.uuid4(),
        user_id=sample_user_active.id,
        business_name="Test Photography",
        business_description="Professional photography services",
        whatsapp_number="+19292491619",
        whatsapp_business_account_id="1233158775296511",
        pricing_packages="$100/hour",
        show_ai_disclaimer=True,
        workflow_status=BUSINESS_WORKFLOW_STATUS_ACTIVE
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


@pytest.fixture
def inactive_business(test_db, sample_user_inactive):
    """Create an inactive business for testing."""
    # Create a second user for the inactive business

    business = Business(
        id=uuid.uuid4(),
        user_id=sample_user_inactive.id,
        business_name="Inactive Business",
        whatsapp_business_account_id="9999999999",
        workflow_status=BUSINESS_WORKFLOW_STATUS_DISABLED
    )
    test_db.add(business)
    test_db.commit()
    test_db.refresh(business)
    return business


@pytest.fixture
def sample_google_oauth_token(test_db, sample_user_active):
    """Create a sample Google OAuth token for testing."""
    token = OAuthToken(
        id=uuid.uuid4(),
        user_id=sample_user_active.id,
        provider=OAUTH_PROVIDER_GOOGLE,
        access_token="encrypted_google_access_token",
        refresh_token="encrypted_google_refresh_token",
        scope="https://www.googleapis.com/auth/calendar",
    )
    test_db.add(token)
    test_db.commit()
    test_db.refresh(token)
    return token


@pytest.fixture
def sample_whatsapp_oauth_token(test_db, sample_user_active):
    """Create a sample WhatsApp OAuth token for testing."""
    token = OAuthToken(
        id=uuid.uuid4(),
        user_id=sample_user_active.id,
        provider=OAUTH_PROVIDER_WHATSAPP,
        access_token="encrypted_whatsapp_access_token",
        refresh_token=None,
    )
    test_db.add(token)
    test_db.commit()
    test_db.refresh(token)
    return token
