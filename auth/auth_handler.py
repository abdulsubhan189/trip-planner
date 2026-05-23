# auth/auth_handler.py
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
from database.models import SessionLocal, User

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("JWT_SECRET", "your-super-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------
def register_user(email: str, username: str, password: str) -> dict:
    db = SessionLocal()
    try:
        # Check if email exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return {"error": "Email already registered"}

        # Check if username exists
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return {"error": "Username already taken"}

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            username=username,
            hashed_password=hash_password(password),
            created_at=datetime.utcnow(),
            is_active="true"
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id, user.email)
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "token": token
        }
    finally:
        db.close()

def login_user(email: str, password: str) -> dict:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"error": "Invalid email or password"}
        if not verify_password(password, user.hashed_password):
            return {"error": "Invalid email or password"}

        token = create_access_token(user.id, user.email)
        return {
            "user_id": user.id,
            "email": user.email,
            "username": user.username,
            "token": token
        }
    finally:
        db.close()

def get_current_user(token: str) -> Optional[dict]:
    payload = decode_token(token)
    if not payload:
        return None
    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email")
    }