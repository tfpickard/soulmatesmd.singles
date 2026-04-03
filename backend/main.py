from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from core.errors import DomainError
from database import get_sessionmaker, init_db
from routes.admin import router as admin_router
from routes.analytics import router as analytics_router
from routes.feed import router as feed_router
from routes.agents import router as agents_router
from routes.chat import router as chat_router
from routes.forum import router as forum_router
from routes.matches import router as match_detail_router
from routes.portraits import router as portraits_router
from routes.swipe import matches_router, router as swipe_router
from routes.users import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_init_db:
        await init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.resolved_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(agents_router, prefix=settings.api_v1_prefix)
app.include_router(portraits_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(swipe_router, prefix=settings.api_v1_prefix)
app.include_router(matches_router, prefix=settings.api_v1_prefix)
app.include_router(match_detail_router, prefix=settings.api_v1_prefix)
app.include_router(chat_router, prefix=settings.api_v1_prefix)
app.include_router(forum_router, prefix=settings.api_v1_prefix)
app.include_router(analytics_router, prefix=settings.api_v1_prefix)
app.include_router(feed_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)


@app.exception_handler(DomainError)
async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
