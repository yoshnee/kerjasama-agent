from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
import uuid
from models.user import Base
from utils.constants import (
    BUSINESS_WORKFLOW_STATUS_ACTIVE,
    BUSINESS_WORKFLOW_STATUS_DISABLED,
    BUSINESS_AI_VOICE_FIRST_PERSON,
    BUSINESS_AI_VOICE_NAME,
    BUSINESS_AI_VOICE_WE,
)

class Business(Base):
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)

    # Basic Info
    owner_name = Column(String(255))
    business_name = Column(String(255))
    business_type = Column(String(100))
    location = Column(String(255))
    business_description = Column(Text)

    # AI Configuration
    ai_voice = Column(String(50))
    show_ai_disclaimer = Column(Boolean, default=True)

    # Pricing
    pricing_packages = Column(Text)

    # Portfolio
    instagram_handle = Column(String(255))
    website_url = Column(Text)

    # WhatsApp
    whatsapp_number = Column(String(20))
    whatsapp_business_account_id = Column(String(255))

    # Workflow
    workflow_status = Column(String(50), default=BUSINESS_WORKFLOW_STATUS_DISABLED)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @validates('ai_voice')
    def validate_ai_voice(self, _, value):
        if value and value not in [BUSINESS_AI_VOICE_FIRST_PERSON, BUSINESS_AI_VOICE_NAME, BUSINESS_AI_VOICE_WE]:
            raise ValueError(f"Invalid ai_voice: {value}")
        return value

    @validates('workflow_status')
    def validate_workflow_status(self, _, value):
        if value not in [BUSINESS_WORKFLOW_STATUS_ACTIVE, BUSINESS_WORKFLOW_STATUS_DISABLED]:
            raise ValueError(f"Invalid workflow_status: {value}")
        return value

    # Relationship
    user = relationship("User", backref="business")
