"""JWT creation/verification and password hashing.

Uses the `bcrypt` package directly (instead of passlib) because passlib is
unmaintained and incompatible with bcrypt ≥ 4.x (raises ValueError on its
own internal wrap-bug detection test).

Integration notes
-----------------
* SECRET_KEY is read from the environment at import time (module-level), so
  load_dotenv() in main.py MUST run before this module is first imported.
* Tokens expire in 72 hours (ACCESS_TOKEN_EXPIRE_HOURS). Adjust for production.
* The ALGORITHM is HS256 — symmetric; the same key signs and verifies.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt  # noqa: F401  (JWTError re-exported for callers)

# ─── Secret key resolution ─────────────────────────────────────────────────────
# .env.example documents the variable as JWT_SECRET_KEY; older deployments may
# have used JWT_SECRET. We check both names so neither breaks, then fall back to
# an insecure dev default that is intentionally recognisable in logs.
# IMPORTANT: set JWT_SECRET_KEY to a random 32-byte hex string in production:
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = (
    os.getenv("JWT_SECRET_KEY")       # canonical name (see .env.example)
    or os.getenv("JWT_SECRET")        # legacy name — kept for backward compat
    or "verse-dev-secret-change-in-production"  # fallback for local dev only
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 72  # 3 days — long enough to survive a weekend shoot


def _encode(plain: str) -> bytes:
    """UTF-8 encode and truncate to 72 bytes (bcrypt's hard limit).

    bcrypt silently truncates inputs longer than 72 bytes, which can create
    false positives where two different long passwords hash the same way.
    By truncating explicitly here we make the behaviour obvious and auditable.
    """
    return plain.encode("utf-8")[:72]


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*. Store this in the database, never the plaintext."""
    return bcrypt.hashpw(_encode(plain), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*. Never raises — returns False on any error."""
    try:
        return bcrypt.checkpw(_encode(plain), hashed.encode())
    except Exception:
        # Catch malformed hash strings, encoding errors, etc.
        return False


def create_token(user_id: str, email: str) -> str:
    """Create a signed JWT containing the user id (sub) and email.

    The token is returned to the frontend as `access_token` in the auth
    response and must be sent back as `Authorization: Bearer <token>` on
    every protected request.
    """
    payload = {
        "sub": user_id,     # standard JWT claim — subject identifier
        "email": email,     # convenience claim read by decode_token callers
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises JWTError if the token is invalid or expired.

    Called by get_current_user() in dependencies.py — do not call this directly
    in route handlers; use the Depends(get_current_user) FastAPI dependency instead.
    """
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
