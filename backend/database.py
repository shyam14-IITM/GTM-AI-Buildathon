import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Actually load the .env file into the environment!
load_dotenv()

# Use environment variable for the database URL, with a fallback for local development.
# Example: postgresql+asyncpg://user:password@localhost/dbname
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is missing")

# Create the async engine
# pool_size and max_overflow can be tuned based on the concurrency requirements.
engine = create_async_engine(
    DATABASE_URL,
    echo=False, # Set to True for debugging SQL queries
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # IMPORTANT: Checks if connection is alive before using it
    pool_recycle=1800    # Recycle connections after 30 minutes
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Declarative base for models
Base = declarative_base()

# Dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
