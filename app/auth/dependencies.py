from fastapi import Depends, HTTPException, Request, Cookie
from typing import Optional
import asyncpg

from app.db.database import get_pool
from app.auth.jwt import decode_token


async def get_current_user(
    request: Request,
    pool: asyncpg.Pool = Depends(get_pool),
):
    # Try Authorization header first
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    # Fall back to cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "Not authenticated"}
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "Invalid or expired token"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "Invalid token"}
        )

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id = $1", int(user_id)
        )

    if not user:
        raise HTTPException(
            status_code=401,
            detail={"status": "error", "message": "User not found"}
        )

    return dict(user)


async def require_admin(
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "message": "Admin access required"}
        )
    return current_user


async def require_analyst(
    current_user: dict = Depends(get_current_user),
):
    if current_user["role"] not in ("admin", "analyst"):
        raise HTTPException(
            status_code=403,
            detail={"status": "error", "message": "Access denied"}
        )
    return current_user