import asyncio
from sqlalchemy import text
from database import engine, Base
# Import models so Base.metadata is aware of all tables before creation
import models 

async def init_database():
    async with engine.begin() as conn:
        print("Enabling pgvector extension...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        
        print("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        
    print("Database initialization complete.")

if __name__ == "__main__":
    asyncio.run(init_database())