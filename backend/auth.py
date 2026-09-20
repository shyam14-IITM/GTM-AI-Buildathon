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
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-buildathon-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 1 week

STATIC_API_KEY = os.getenv("DRONAHQ_API_KEY", "buildathon-secret-drona-key-2026")

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

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme), 
    x_api_key: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db)
):
    # 1. Check for DronaHQ API Key Bypass
    if x_api_key == STATIC_API_KEY:
        # Return a mock superuser payload for DronaHQ actions
        mock_admin = User(
            id=uuid.UUID('00000000-0000-0000-0000-000000000000'), 
            email="admin@dronahq.internal", 
            name="DronaHQ Admin", 
            is_active=True
        )
        return mock_admin

    # 2. Fall back to standard JWT extraction
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.InvalidTokenError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user
