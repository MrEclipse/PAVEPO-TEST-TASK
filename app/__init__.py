from fastapi import FastAPI
from app.routes.routes import router


def create_app(lifespan) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(router=router)
    return app