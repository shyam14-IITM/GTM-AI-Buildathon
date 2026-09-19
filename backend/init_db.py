import asyncio
from sqlalchemy import text
from database import engine, Base
# Import models so Base.metadata is aware of all tables before creation
import models 

async def init_database():
    async with engine.begin() as conn:
        print("Enabling pgvector extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        
        print("Dropping existing tables for fresh schema...")
        # Manually drop outreach_logs with CASCADE because it was removed from models.py
        await conn.execute(text("DROP TABLE IF EXISTS outreach_logs CASCADE;"))
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    print("Database initialization complete.")

if __name__ == "__main__":
    asyncio.run(init_database())