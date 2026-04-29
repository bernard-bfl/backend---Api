import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.db.database import init_db, close_pool, get_pool
from app.routes.profiles import router as profiles_router
from app.routes.admin import router as admin_router
from app.auth.router import router as auth_router

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_pool()


app = FastAPI(
    title="Insighta Labs+",
    version="3.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(admin_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    try:
        pool = await get_pool()
        user_id = None
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            token = request.cookies.get("access_token")
        if token:
            from app.auth.jwt import decode_token
            payload = decode_token(token)
            if payload:
                user_id = int(payload.get("sub", 0)) or None

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO request_logs (user_id, method, path, status_code, duration_ms)
                VALUES ($1, $2, $3, $4, $5)
                """,
                user_id,
                request.method,
                str(request.url.path),
                response.status_code,
                duration_ms,
            )
    except Exception:
        pass

    return response





@app.exception_handler(422)
async def validation_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Invalid query parameters"},
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": "Internal server error"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}