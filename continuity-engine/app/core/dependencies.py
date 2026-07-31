"""FastAPI dependency functions shared across routers.

These are injected via FastAPI's Depends() mechanism. Route handlers that need
an authenticated user declare:

    current_user: Annotated[dict, Depends(get_current_user)]

and FastAPI calls get_current_user() automatically, passing it the request
headers. If the token is missing or invalid the dependency raises 401 and
FastAPI short-circuits the route — the handler body never executes.
"""

from __future__ import annotations

from contextlib import closing

from fastapi import Depends, Header, HTTPException
from jose import JWTError

from app.core.database import db
from app.core.security import decode_token


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    """Extract and validate the JWT from the Authorization: Bearer <token> header.

    Returns the full user row from the database as a plain dict (hashed_pw
    included — callers must omit it when serialising to JSON).

    Raises HTTP 401 for:
    - Missing or malformed Authorization header
    - Expired or tampered JWT
    - Token whose subject (user id) no longer exists in the database

    The header is declared Optional so that a missing header produces a clean
    401 rather than FastAPI's default 422 Unprocessable Entity.
    """
    if not authorization or not authorization.startswith("Bearer "):
        # Return a user-friendly message that the frontend displays verbatim
        raise HTTPException(401, "Not authenticated. Please sign in to continue.")

    token = authorization[7:]  # strip the "Bearer " prefix

    try:
        payload = decode_token(token)
    except JWTError:
        # Covers expired tokens, bad signature, malformed base64, etc.
        raise HTTPException(401, "Token is invalid or expired.")

    user_id = payload.get("sub")
    if not user_id:
        # A token without a subject claim is structurally invalid
        raise HTTPException(401, "Malformed token.")

    # Verify the user still exists — they might have been deleted since the
    # token was issued. This is the only DB call in the hot auth path.
    conn = db()
    with closing(conn.cursor()) as cur:
        row = cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(401, "User not found.")

    return dict(row)


def get_current_user_optional(authorization: str | None = Header(default=None)) -> dict | None:
    """Like get_current_user but returns None when no token is provided.

    Use this on public routes that behave differently for authenticated users
    (e.g. showing personalised content) but must not reject unauthenticated
    requests entirely.
    """
    if not authorization:
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        # Invalid token on an optional route → treat as anonymous
        return None
