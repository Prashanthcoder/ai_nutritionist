import asyncio
from database.config import engine, Base


async def go():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("tables ok")

asyncio.run(go())
