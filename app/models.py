from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    hardware_id = Column(String, nullable=True)

    subscription_expires_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)

    is_banned = Column(Boolean, default=False)


class LicenseKey(Base):
    __tablename__ = "license_keys"

    id = Column(Integer, primary_key=True, index=True)

    key_hash = Column(String, unique=True, nullable=False)

    duration_days = Column(Integer, nullable=False)

    used = Column(Boolean, default=False)

    used_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    used_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())