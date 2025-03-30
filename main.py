import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import jwt
from pydantic import BaseModel

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from starlette.responses import RedirectResponse
from routes import router
from . import create

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/postgres")
YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID", "fa167c5799d149dfa27a6c800f1ec2c3")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET", "b3a926fc679f4dd2a6eeb2b1185a4fc6")
YANDEX_REDIRECT_URI = os.getenv("YANDEX_REDIRECT_URI", "заглушка")
JWT_SECRET = os.getenv("JWT_SECRET", "adea1f25c9f637d7a6cd34bc0ef8a2fab2ce26211722ee03c97c0009289321585c9be331fdce27972ebaec47c9ad609a5bb83a546b7653d0cbdb554308f21139dc8e3b8780cfe23d2577e5f8a05b6cb6b85f57f60189767f20df6e2a6e2807d6096fb2b37be4906e639f5da777123986530fe103fb2f31af19d98cb5976fb53c6748832ab9dd4a84f8980652d3bfbb79c56bac9b4f519c96de5471a0e41ec8356e12a5b9e651443ff67a24f182ce47a44c036da07369475884116647fa6ad5c7230a92efaaeed72a3cddc3cc5f931ab55957240f9a3899ec1eb889933ff89f292f4a39d226915d0e02d3f9cd304c3f10c29321d897df344442e813d291287943")  # ОБЯЗАТЕЛЬНО поменяйте на сгенерированное значение!
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(title="Audio-reg service")








