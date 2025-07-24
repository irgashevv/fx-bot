from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import Base
from config import DATABASE_URL

async_engine = create_async_engine(DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Database tables created.")


async def delete_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("Database tables deleted.")
