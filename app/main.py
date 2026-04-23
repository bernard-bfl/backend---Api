from contextlib import asynccontextmanager
from fastapi import FastAPI, Request 
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import JSONResponse

from app.db.database import init_db, close_pool
from app.routes.profiles import router as profiles_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_pool()

app = FastAPI(
    title="Insighta Labs - Inteligence Query Engine",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(profiles_router)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"status": "error", "message": "Not found"},
    )

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