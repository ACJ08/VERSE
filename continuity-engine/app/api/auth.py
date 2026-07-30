"""Authentication router — register, login, verify-email, forgot-password, /me.

Email flows
-----------
* verify-email  : POST /auth/verify-email/request  → generates a 6-digit OTP,
                  stores its SHA-256 hash in the users table, returns it in dev
                  (or sends via SMTP when SMTP_HOST is configured).
                  POST /auth/verify-email           → accepts the OTP, marks verified.

* forgot-password: POST /auth/forgot-password  → same OTP mechanism stored in
                  password_reset_tokens table.
                  POST /auth/reset-password    → validates token, sets new password.

Production email:
  Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM in the environment.
  When SMTP_HOST is absent, the token is returned in the JSON response so the
  dev/demo flow works without an email server.
"""

from __future__ import annotations

import hashlib
import os
import random
import smtplib
import string
import uuid
from contextlib import closing
from email.mime.text import MIMEText
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.database import db
from app.core.dependencies import get_current_user
from app.core.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# ─── Email helper ──────────────────────────────────────────────────────────────

def _send_email(to: str, subject: str, body: str) -> bool:
    """Send via SMTP if configured; return True on success, False otherwise."""
    host = os.getenv("SMTP_HOST", "")
    if not host:
        return False
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        from_addr = os.getenv("SMTP_FROM", user)
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(from_addr, [to], msg.as_string())
        return True
    except Exception:
        return False


def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ─── DB helpers for token tables ──────────────────────────────────────────────

_TOKEN_SCHEMA = """
CREATE TABLE IF NOT EXISTS email_verify_tokens (
    user_id     TEXT PRIMARY KEY,
    token_hash  TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    email       TEXT PRIMARY KEY,
    token_hash  TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);
"""


def _ensure_token_tables() -> None:
    conn = db()
    with closing(conn.cursor()) as cur:
        cur.executescript(_TOKEN_SCHEMA)
    conn.commit()


# ─── Request / Response models ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    name: str
    organization: str = ""
    production_company: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    token: str
    new_password: str = Field(min_length=6)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=AuthResponse)
def register(req: RegisterRequest):
    conn = db()
    with closing(conn.cursor()) as cur:
        existing = cur.execute("SELECT id FROM users WHERE email = ?", (req.email.lower(),)).fetchone()
        if existing:
            raise HTTPException(400, "An account with this email already exists.")

        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (id, email, name, hashed_pw, verified) VALUES (?, ?, ?, ?, 0)",
            (user_id, req.email.lower(), req.name, hash_password(req.password)),
        )
        conn.commit()

        user = dict(cur.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())

    token = create_token(user_id, req.email.lower())
    return AuthResponse(
        access_token=token,
        user={k: v for k, v in user.items() if k != "hashed_pw"},
    )


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    conn = db()
    with closing(conn.cursor()) as cur:
        row = cur.execute("SELECT * FROM users WHERE email = ?", (req.email.lower(),)).fetchone()

    if row is None or not verify_password(req.password, row["hashed_pw"]):
        raise HTTPException(401, "Invalid email or password.")

    user = {k: v for k, v in dict(row).items() if k != "hashed_pw"}
    token = create_token(row["id"], row["email"])
    return AuthResponse(access_token=token, user=user)


@router.post("/verify-email/request")
def request_email_verification(current_user: Annotated[dict, Depends(get_current_user)]):
    """
    Generate a 6-digit OTP for email verification.
    Sends it via SMTP when configured; returns it in the response body in dev mode.
    """
    _ensure_token_tables()
    otp = _generate_otp()
    token_hash = _hash_token(otp)

    conn = db()
    with closing(conn.cursor()) as cur:
        cur.execute(
            "INSERT OR REPLACE INTO email_verify_tokens (user_id, token_hash) VALUES (?, ?)",
            (current_user["id"], token_hash),
        )
    conn.commit()

    sent = _send_email(
        current_user["email"],
        "VERSE — Verify your email",
        f"Your VERSE email verification code is: {otp}\n\nThis code is valid for 24 hours.",
    )
    response: dict = {"message": "Verification code sent."}
    if not sent:
        # Dev/demo mode — surface the token so the frontend can prefill the OTP
        response["dev_token"] = otp
        response["message"] = "SMTP not configured — token returned for development."
    return response


@router.post("/verify-email")
def verify_email(
    req: VerifyEmailRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Validate the OTP and mark the account as verified."""
    _ensure_token_tables()
    conn = db()
    with closing(conn.cursor()) as cur:
        row = cur.execute(
            "SELECT token_hash FROM email_verify_tokens WHERE user_id = ?",
            (current_user["id"],),
        ).fetchone()

    if row is None or row["token_hash"] != _hash_token(req.token):
        raise HTTPException(400, "Invalid or expired verification code.")

    with closing(conn.cursor()) as cur:
        cur.execute("UPDATE users SET verified = 1 WHERE id = ?", (current_user["id"],))
        cur.execute("DELETE FROM email_verify_tokens WHERE user_id = ?", (current_user["id"],))
    conn.commit()
    return {"verified": True, "email": current_user["email"]}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    """
    Generate a 6-digit password reset OTP.
    Sends it via SMTP when configured; returns it in the response body in dev mode.
    Always returns 200 — never reveals whether an account exists.
    """
    _ensure_token_tables()
    conn = db()
    with closing(conn.cursor()) as cur:
        row = cur.execute(
            "SELECT id FROM users WHERE email = ?", (req.email.lower(),)
        ).fetchone()

    response: dict = {
        "message": "If an account with that email exists, a reset code has been sent."
    }
    if row is None:
        return response  # Don't leak account existence

    otp = _generate_otp()
    token_hash = _hash_token(otp)

    with closing(conn.cursor()) as cur:
        cur.execute(
            "INSERT OR REPLACE INTO password_reset_tokens (email, token_hash) VALUES (?, ?)",
            (req.email.lower(), token_hash),
        )
    conn.commit()

    sent = _send_email(
        req.email.lower(),
        "VERSE — Password reset code",
        f"Your VERSE password reset code is: {otp}\n\nIf you did not request this, ignore this email.",
    )
    if not sent:
        response["dev_token"] = otp
        response["message"] = "SMTP not configured — token returned for development."
    return response


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest):
    """Validate the OTP and set a new password."""
    _ensure_token_tables()
    conn = db()
    with closing(conn.cursor()) as cur:
        row = cur.execute(
            "SELECT token_hash FROM password_reset_tokens WHERE email = ?",
            (req.email.lower(),),
        ).fetchone()

    if row is None or row["token_hash"] != _hash_token(req.token):
        raise HTTPException(400, "Invalid or expired reset code.")

    with closing(conn.cursor()) as cur:
        cur.execute(
            "UPDATE users SET hashed_pw = ? WHERE email = ?",
            (hash_password(req.new_password), req.email.lower()),
        )
        cur.execute(
            "DELETE FROM password_reset_tokens WHERE email = ?", (req.email.lower(),)
        )
    conn.commit()
    return {"message": "Password updated successfully. Please sign in with your new password."}


@router.get("/me")
def me(current_user: Annotated[dict, Depends(get_current_user)]):
    return {k: v for k, v in current_user.items() if k != "hashed_pw"}
