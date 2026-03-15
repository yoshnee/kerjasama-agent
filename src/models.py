"""Read-only SQLAlchemy models referencing tables owned by the onboarding API."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase
import uuid


class Base(DeclarativeBase):
    pass


class User(Base):
    """Minimal reference for FK resolution only."""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Business(Base):
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    owner_name = Column(String(255))
    business_name = Column(String(255))
    business_type = Column(String(100))
    location = Column(String(255))
    whatsapp_number = Column(String(20))
    about = Column(Text)
    pricing_text = Column(Text)
    services = Column(JSONB, nullable=True)
    accent_color = Column(String(7), default="#3BABCD")
    is_active = Column(Boolean, default=False)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    expires_at = Column(DateTime(timezone=True))
