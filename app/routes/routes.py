import os
import shutil
from datetime import timedelta, datetime
from typing import Optional, List

import httpx
import jwt
from fastapi import Depends, HTTPException, UploadFile, File, Form, APIRouter
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import RedirectResponse

from app.models import get_db, User, AudioFile
from app.schemas import Token, UserOut, UserUpdate, AudioFileOut


YANDEX_CLIENT_ID = os.getenv("YANDEX_CLIENT_ID", "fa167c5799d149dfa27a6c800f1ec2c3")
YANDEX_CLIENT_SECRET = os.getenv("YANDEX_CLIENT_SECRET", "b3a926fc679f4dd2a6eeb2b1185a4fc6")
YANDEX_REDIRECT_URI = os.getenv("YANDEX_REDIRECT_URI", "заглушка")
JWT_SECRET = os.getenv("JWT_SECRET", "adea1f25c9f637d7a6cd34bc0ef8a2fab2ce26211722ee03c97c0009289321585c9be331fdce27972ebaec47c9ad609a5bb83a546b7653d0cbdb554308f21139dc8e3b8780cfe23d2577e5f8a05b6cb6b85f57f60189767f20df6e2a6e2807d6096fb2b37be4906e639f5da777123986530fe103fb2f31af19d98cb5976fb53c6748832ab9dd4a84f8980652d3bfbb79c56bac9b4f519c96de5471a0e41ec8356e12a5b9e651443ff67a24f182ce47a44c036da07369475884116647fa6ad5c7230a92efaaeed72a3cddc3cc5f931ab55957240f9a3899ec1eb889933ff89f292f4a39d226915d0e02d3f9cd304c3f10c29321d897df344442e813d291287943")  # ОБЯЗАТЕЛЬНО поменяйте на сгенерированное значение!
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

"""
ФУНКЦИИ
"""

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

"""
ЭНДПОИНТЫ АВТОРИЗАЦИИ
"""

router = APIRouter()

@router.get("/auth/yandex/login")
async def yandex_login():
    params = {
        "response_type": "code",
        "client_id": YANDEX_CLIENT_ID,
        "redirect_uri": YANDEX_REDIRECT_URI,
    }
    query = "&".join([f"{key}={value}" for key, value in params.items()])
    yandex_auth_url = f"https://oauth.yandex.ru/authorize?{query}"
    return RedirectResponse(url=yandex_auth_url)


@router.get("/auth/yandex/callback", response_model=Token)
async def yandex_callback(code: str, db: AsyncSession = Depends(get_db)):
    # Обмен кода на access token у Яндекса
    token_url = "https://oauth.yandex.ru/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": YANDEX_CLIENT_ID,
        "client_secret": YANDEX_CLIENT_SECRET,
        "redirect_uri": YANDEX_REDIRECT_URI,
    }
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=data)
    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Ошибка авторизации Яндекса: {token_response.text}")
    try:
        token_json = token_response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Невозможно разобрать JSON токена: {e}")

    yandex_access_token = token_json.get("access_token")
    if not yandex_access_token:
        raise HTTPException(status_code=400, detail="В ответе отсутствует access_token")

    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://login.yandex.ru/info",
            headers={"Authorization": f"OAuth {yandex_access_token}"},
            params={"format": "json"}
        )
    if user_response.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Ошибка получения данных пользователя: {user_response.text}")
    try:
        user_data = user_response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Невозможно разобрать JSON пользователя: {e}")

    yandex_id = str(user_data.get("id"))
    username = user_data.get("display_name", "NoName")
    email = user_data.get("default_email")

    # Поиск пользователя в БД по yandex_id
    result = await db.execute(text("SELECT * FROM users WHERE yandex_id = :yandex_id"), {"yandex_id": yandex_id})
    user_row = result.fetchone()
    if user_row is None:
        new_user = User(
            yandex_id=yandex_id,
            username=username,
            email=email,
            is_superuser=False  # Логику определения суперпользователя можно настроить отдельно
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user = new_user
    else:
        user = await db.get(User, user_row[0])
    # Генерация внутреннего JWT токена
    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)


@router.post("/auth/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    new_token = create_access_token(data={"sub": str(current_user.id)})
    return Token(access_token=new_token)

"""
ЭНДПОИНТЫ USEREXP
"""

@router.get("/users/me", response_model=UserOut)
async def read_user_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/users/me", response_model=UserOut)
async def update_user_me(user_update: UserUpdate, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    if user_update.username:
        current_user.username = user_update.username
    if user_update.email:
        current_user.email = user_update.email
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db),
                      current_user: User = Depends(superuser_required)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    await db.delete(user)
    await db.commit()
    return {"detail": "Пользователь удалён"}

"""
ЭНДПОИНТЫ РАБОТЫ С АУДИО
"""

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=AudioFileOut)
async def upload_audio(file: UploadFile = File(...), name: str = Form(...),
                       db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    audio_file = AudioFile(
        user_id=current_user.id,
        file_name=name,
        file_path=file_location
    )
    db.add(audio_file)
    await db.commit()
    await db.refresh(audio_file)
    return audio_file


@router.get("/audio-files", response_model=List[AudioFileOut])
async def list_audio_files(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(text("SELECT * FROM audio_files WHERE user_id = :user_id"), {"user_id": current_user.id})
    rows = result.fetchall()
    audio_files = []
    for row in rows:
        af = await db.get(AudioFile, row[0])
        audio_files.append(af)
    return audio_files