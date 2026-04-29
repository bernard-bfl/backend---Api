from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import asyncpg

from app.db.database import get_pool
from app.auth.dependencies import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def get_users(
    pool: asyncpg.Pool = Depends(get_pool),
    current_user: dict = Depends(require_admin),
):
    async with pool.acquire() as conn:
        users = await conn.fetch(
            """
            SELECT id, github_id, username, email, avatar_url, role,
                   to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at,
                   to_char(last_login AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS last_login
            FROM users
            ORDER BY created_at DESC
            """
        )
    return {
        "status": "success",
        "total": len(users),
        "data": [dict(u) for u in users],
    }


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: str,
    pool: asyncpg.Pool = Depends(get_pool),
    current_user: dict = Depends(require_admin),
):
    if role not in ("admin", "analyst"):
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": "Role must be admin or analyst"}
        )

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "UPDATE users SET role = $1 WHERE id = $2 RETURNING *",
            role, user_id
        )

    if not user:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "User not found"}
        )

    return {
        "status": "success",
        "message": f"User {user_id} role updated to {role}",
        "data": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        }
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    pool: asyncpg.Pool = Depends(get_pool),
    current_user: dict = Depends(require_admin),
):
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "DELETE FROM users WHERE id = $1 RETURNING id, username",
            user_id
        )

    if not user:
        raise HTTPException(
            status_code=404,
            detail={"status": "error", "message": "User not found"}
        )

    return {
        "status": "success",
        "message": f"User {user['username']} deleted",
    }


@router.get("/logs")
async def get_logs(
    limit: int = 50,
    pool: asyncpg.Pool = Depends(get_pool),
    current_user: dict = Depends(require_admin),
):
    async with pool.acquire() as conn:
        logs = await conn.fetch(
            """
            SELECT l.id, l.user_id, u.username, l.method, l.path,
                   l.status_code, l.duration_ms,
                   to_char(l.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at
            FROM request_logs l
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.created_at DESC
            LIMIT $1
            """,
            limit
        )
    return {
        "status": "success",
        "total": len(logs),
        "data": [dict(l) for l in logs],
    }