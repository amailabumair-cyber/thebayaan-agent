import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')


from agent_am.database.connection import engine
from agent_am.database.models import Base

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("OK: Growth tables created - growth_channel_snapshots, growth_video_snapshots")

asyncio.run(create_tables())
