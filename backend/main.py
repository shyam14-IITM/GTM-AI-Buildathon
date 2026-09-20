import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import timedelta
from pydantic import BaseModel

from database import get_db
from models import User
from auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_current_user
)
from routers import campaigns, prospects

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SDR Buildathon API")

raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allow_origins = [origin.strip() for origin in raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

# --- Application Routing ---
app.include_router(campaigns.router, prefix="/api")
app.include_router(prospects.router, prefix="/api")

@app.get("/api/reps", tags=["system"])
async def get_available_reps():
    """
    Hybrid approach: Returns a hardcoded list of Sales Reps for DronaHQ dropdown binding.
    """
    return [
        {"id": "rep_1", "name": "Alex Miller", "email": "alex@company.com"},
        {"id": "rep_2", "name": "Priya Sharma", "email": "priya@company.com"},
        {"id": "rep_3", "name": "Devin Reed", "email": "devin@company.com"}
    ]

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

# --- Pydantic Schemas ---
class UserCreate(BaseModel):
    name: str
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    is_active: bool

# --- Authentication Routes ---

@app.post("/signup", response_model=UserResponse)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_pwd = get_password_hash(user.password)
    new_user = User(
        name=user.name,
        email=user.email,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Pydantic will serialize the UUID to a string automatically
    return {"id": str(new_user.id), "name": new_user.name, "email": new_user.email, "is_active": new_user.is_active}


@app.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # Find user by email (OAuth2 uses 'username' field for the email)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    # Verify password
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Generate JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


# --- Protected Route Example ---

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    This endpoint is protected. It requires a valid JWT token in the Authorization header.
    """
    return {"id": str(current_user.id), "name": current_user.name, "email": current_user.email, "is_active": current_user.is_active}

