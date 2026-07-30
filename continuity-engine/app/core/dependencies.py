"""FastAPI dependency functions shared across routers."""

from __future__ import annotations

from contextlib import closing

from fastapi import Depends, Header, HTTPException
from jose import JWTError

from app.core.database import db
from app.core.security import decode_token


def get_current_user(authorization: str = Header(...)) -> dict:
    """Extract and validate JWT from Authorization: Bearer <token> header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header.")
    token = authorization[7:]
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(401, "Token is invalid or expired.")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(401, "Malformed token.")

    conn = db()
    with closing(conn.cursor()) as cur:
        row = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(401, "User not found.")

    return dict(row)


def get_current_user_optional(authorization: str | None = Header(default=None)) -> dict | None:
    """Like get_current_user but returns None if no token is provided (public routes)."""
    if not authorization:
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None
