import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import jwt

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

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

async def get_db():
    async with async_session() as session:
        yield session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

#SQLALCHEMY модели
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    yandex_id = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    audio_files = relationship("AudioFile", back_populates="owner")


class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="audio_files")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Неверные учетные данные: отсутствует sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен просрочен")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Ошибка декодирования токена: {e}")

    result = await db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": int(user_id)})
    user_row = result.fetchone()
    if user_row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    user = await db.get(User, int(user_id))
    return user

def superuser_required(user: User = Depends(get_current_user)):
    if not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещён")
    return user