import asyncio
from database import engine, Base
import models # Important: import models so Base knows about all tables

async def reset_database():
    async with engine.begin() as conn:
        print("Dropping all existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        
        print("Recreating database tables with latest schema...")
        await conn.run_sync(Base.metadata.create_all)
        
    print("Database reset complete! You can now run `python seed.py`.")

if __name__ == "__main__":
    asyncio.run(reset_database())
