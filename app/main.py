import os
from contextlib import asynccontextmanager
import uvicorn

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from fastapi import FastAPI

from sqlalchemy.orm import sessionmaker, declarative_base
from app import create_app
from app.database import Base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/postgres")

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)








