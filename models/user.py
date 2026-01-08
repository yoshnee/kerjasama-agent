from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, validates
from datetime import datetime, timezone
from utils.constants import USER_STATUS_ONBOARDING, USER_STATUS_ACTIVE, USER_STATUS_SUSPENDED
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    status = Column(String(50), default=USER_STATUS_ONBOARDING)

    @validates('status')
    def validate_status(self, _, value):
        if value not in [USER_STATUS_ONBOARDING, USER_STATUS_ACTIVE, USER_STATUS_SUSPENDED]:
            raise ValueError(f"Invalid user status: {value}.")
        return value
