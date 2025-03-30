from contextlib import asynccontextmanager
import uvicorn
from fastapi.openapi.utils import get_openapi

from fastapi import FastAPI

from app import create_app
from app.database import Base, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = create_app(lifespan)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Audio Upload Service",
        version="1.0.0",
        description="API для загрузки аудио с авторизацией через Яндекс",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Введите: Bearer <JWT токен>"
        }
    }
    # Применяем схему безопасности ко всем эндпоинтам, требующим авторизации
    for path in openapi_schema["paths"].values():
        for operation in path.values():
            operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)








