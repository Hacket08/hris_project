from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth.bootstrap import bootstrap_default_admin_if_empty
from app.auth.router import router as auth_router
from app.core.config import get_settings
from app.core.db import AsyncSessionLocal

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with AsyncSessionLocal() as db:
        await bootstrap_default_admin_if_empty(db)
    yield


app = FastAPI(title="HRIS System API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
