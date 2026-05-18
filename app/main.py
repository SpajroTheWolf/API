from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import hashlib
import string
import random

from app.database import Base, engine, get_db
from app.models import User, LicenseKey
from app.schemas import (
    RegisterSchema,
    LoginSchema,
    RedeemSchema,
    CreateKeySchema,
    ResetHWIDSchema
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token
)
from app.config import ADMIN_TOKEN

Base.metadata.create_all(bind=engine)

app = FastAPI()


# ------------------------
# HELPERS
# ------------------------


def hash_license_key(key: str):
    return hashlib.sha256(key.encode()).hexdigest()



def generate_license_key():
    parts = []

    chars = string.ascii_uppercase + string.digits

    for _ in range(4):
        parts.append(
            ''.join(random.choice(chars) for _ in range(4))
        )

    return '-'.join(parts)


# ------------------------
# REGISTER
# ------------------------


@app.post("/register")
def register(data: RegisterSchema, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(
        User.username == data.username
    ).first()

    if existing_user:
        raise HTTPException(400, "User already exists")

    user = User(
        username=data.username,
        password_hash=hash_password(data.password)
    )

    db.add(user)
    db.commit()

    return {
        "success": True
    }


# ------------------------
# LOGIN
# ------------------------


@app.post("/login")
def login(data: LoginSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    if user.is_banned:
        raise HTTPException(403, "User banned")

    if not user.subscription_expires_at:
        raise HTTPException(403, "No active subscription")

    if user.subscription_expires_at < datetime.utcnow():
        raise HTTPException(403, "Subscription expired")

    # First login HWID bind
    if not user.hardware_id:
        user.hardware_id = data.hardware_id

    # HWID mismatch
    elif user.hardware_id != data.hardware_id:
        return {
            "success": False,
            "reason": "invalid_hwid"
        }

    user.last_login = datetime.utcnow()

    db.commit()

    token = create_access_token({
        "sub": user.username
    })

    return {
        "success": True,
        "token": token,
        "expires_at": user.subscription_expires_at
    }


# ------------------------
# REDEEM
# ------------------------


@app.post("/redeem")
def redeem(data: RedeemSchema, db: Session = Depends(get_db)):

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    hashed_key = hash_license_key(data.key)

    license_key = db.query(LicenseKey).filter(
        LicenseKey.key_hash == hashed_key
    ).first()

    if not license_key:
        raise HTTPException(404, "Invalid key")

    if license_key.used:
        raise HTTPException(400, "Key already used")

    now = datetime.utcnow()

    if user.subscription_expires_at and user.subscription_expires_at > now:
        user.subscription_expires_at += timedelta(days=license_key.duration_days)
    else:
        user.subscription_expires_at = now + timedelta(days=license_key.duration_days)

    license_key.used = True
    license_key.used_by_user_id = user.id
    license_key.used_at = now

    db.commit()

    return {
        "success": True,
        "subscription_expires_at": user.subscription_expires_at
    }


# ------------------------
# CREATE KEY
# ------------------------


@app.post("/create_key")
def create_key(data: CreateKeySchema, db: Session = Depends(get_db)):

    if data.admin_token != ADMIN_TOKEN:
        raise HTTPException(403, "Invalid admin token")

    plaintext_key = generate_license_key()

    hashed_key = hash_license_key(plaintext_key)

    key = LicenseKey(
        key_hash=hashed_key,
        duration_days=data.duration_days
    )

    db.add(key)
    db.commit()

    return {
        "success": True,
        "key": plaintext_key,
        "duration_days": data.duration_days
    }


# ------------------------
# RESET HWID
# ------------------------


@app.post("/reset_hardware_id")
def reset_hardware_id(data: ResetHWIDSchema, db: Session = Depends(get_db)):

    if data.admin_token != ADMIN_TOKEN:
        raise HTTPException(403, "Invalid admin token")

    user = db.query(User).filter(
        User.username == data.username
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    user.hardware_id = None

    db.commit()

    return {
        "success": True
    }


# ------------------------
# HEALTH CHECK
# ------------------------


@app.get("/")
def home():
    return {
        "status": "online"
    }
