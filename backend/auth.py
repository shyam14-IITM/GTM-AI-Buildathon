import os
import uuid
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models import User

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is missing")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 1 week

STATIC_API_KEY = os.getenv("DRONAHQ_API_KEY")
if not STATIC_API_KEY:
    raise ValueError("DRONAHQ_API_KEY environment variable is missing")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt requires bytes
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_bytes.decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

from fastapi import Header
from typing import Optional

async def get_current_user(db: AsyncSession = Depends(get_db)):
    """
    HACKATHON DEMO BYPASS: 
    Ignore JWT tokens entirely and always return the seeded admin user.
    """
    result = await db.execute(select(User).where(User.email == "admin@company.com"))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Admin user not found. Did you run seed.py?"
        )
    return user
