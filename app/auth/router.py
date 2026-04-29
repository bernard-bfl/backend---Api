import httpx
import secrets
import hashlib
import base64
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
import asyncpg

from app.db.database import get_pool
from app.auth.config import (
    GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET,
    FRONTEND_URL, BACKEND_URL,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory PKCE store (use Redis in production)
pkce_store = {}


@router.get("/login")
async def login(request: Request):
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    state = secrets.token_urlsafe(32)
    pkce_store[state] = code_verifier

    github_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={BACKEND_URL}/auth/callback"
        f"&scope=read:user user:email"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )
    return RedirectResponse(github_url)


@router.get("/callback")
async def callback(
    request: Request,
    response: Response,
    code: str = None,
    state: str = None,
    pool: asyncpg.Pool = Depends(get_pool),
):
    if not code or not state:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Missing code or state"})

    code_verifier = pkce_store.pop(state, None)
    if not code_verifier:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Invalid state"})

    # Exchange code for GitHub access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{BACKEND_URL}/auth/callback",
                "code_verifier": code_verifier,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_response.json()

    github_token = token_data.get("access_token")
    if not github_token:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "GitHub auth failed"})

    # Get GitHub user info
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_token}"},
        )
        github_user = user_response.json()

    # Upsert user in database
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            INSERT INTO users (github_id, username, email, avatar_url, last_login)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (github_id) DO UPDATE SET
                username = EXCLUDED.username,
                email = EXCLUDED.email,
                avatar_url = EXCLUDED.avatar_url,
                last_login = NOW()
            RETURNING *
            """,
            str(github_user["id"]),
            github_user.get("login"),
            github_user.get("email"),
            github_user.get("avatar_url"),
        )
        user = dict(user)
        async with pool.acquire() as conn:
            fresh_user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user["id"])
            user = dict(fresh_user)

    # Create tokens
    access_token = create_access_token({"sub": str(user["id"]), "role": user["role"]})
    refresh_token = create_refresh_token({"sub": str(user["id"])})

    # Store refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO refresh_tokens (user_id, token, expires_at) VALUES ($1, $2, $3)",
            user["id"], refresh_token, expires_at,
        )
    # Redirect to frontend with tokens
    redirect = RedirectResponse(
        url=f"{FRONTEND_URL}/auth/success?access_token={access_token}&refresh_token={refresh_token}"
    )
    redirect.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=900,
    )
    redirect.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )
    return redirect


@router.post("/refresh")
async def refresh_token(
    request: Request,
    pool: asyncpg.Pool = Depends(get_pool),
):
    token = request.cookies.get("refresh_token")
    if not token:
        body = await request.json()
        token = body.get("refresh_token")

    if not token:
        raise HTTPException(status_code=401, detail={"status": "error", "message": "Missing refresh token"})

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={"status": "error", "message": "Invalid refresh token"})

    async with pool.acquire() as conn:
        stored = await conn.fetchrow(
            "SELECT * FROM refresh_tokens WHERE token = $1", token
        )

    if not stored:
        raise HTTPException(status_code=401, detail={"status": "error", "message": "Refresh token not found"})

    user_id = payload.get("sub")
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", int(user_id))

    access_token = create_access_token({"sub": str(user["id"]), "role": user["role"]})

    return {"status": "success", "access_token": access_token}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    pool: asyncpg.Pool = Depends(get_pool),
    current_user: dict = Depends(get_current_user),
):
    token = request.cookies.get("refresh_token")
    if token:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM refresh_tokens WHERE token = $1", token)

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"status": "success", "message": "Logged out"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "data": {
            "id": current_user["id"],
            "username": current_user["username"],
            "email": current_user["email"],
            "avatar_url": current_user["avatar_url"],
            "role": current_user["role"],
            "created_at": str(current_user["created_at"]),
            "last_login": str(current_user["last_login"]),
        }
    }