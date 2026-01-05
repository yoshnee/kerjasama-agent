from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
import uuid
from models.user import Base
from utils.constants import OAUTH_PROVIDER_GOOGLE, OAUTH_PROVIDER_WHATSAPP

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    provider = Column(String(50), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text)
    token_expiry = Column(DateTime(timezone=True))
    scope = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @validates('provider')
    def validate_provider(self, _, value):
        if value not in [OAUTH_PROVIDER_GOOGLE, OAUTH_PROVIDER_WHATSAPP]:
            raise ValueError(f"Invalid oauth provider: {value}.")
        return value

    # Relationship
    user = relationship("User", backref="oauth_tokens")
