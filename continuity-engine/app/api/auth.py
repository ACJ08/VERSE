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

Gmail setup (recommended for production / staging):
  1. Enable 2-Step Verification on the Gmail account.
  2. Create an App Password:
       Google Account → Security → 2-Step Verification → App Passwords
       Select "Mail" + "Other (Custom name)" → copy the 16-char password.
  3. Set these env vars (in .env or shell):
       SMTP_HOST=smtp.gmail.com
       SMTP_PORT=465
       SMTP_USE_SSL=true
       SMTP_USER=you@gmail.com
       SMTP_PASSWORD=<16-char app password>
       SMTP_FROM=you@gmail.com
  When SMTP_HOST is absent, the OTP is returned in the JSON response so the
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
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.database import db
from app.core.dependencies import get_current_user
from app.core.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# ─── Email helper ──────────────────────────────────────────────────────────────

def _send_email(to: str, subject: str, plain: str, html: str | None = None) -> bool:
    """Send an email via SMTP.

    Supports two connection modes selected by SMTP_USE_SSL:
      SMTP_USE_SSL=true  → SMTP_SSL on port 465  (Gmail recommended)
      SMTP_USE_SSL=false → SMTP + STARTTLS on port 587  (default)

    Returns True on success, False on any error or when SMTP is not configured.
    Falls back gracefully — callers surface the OTP in the JSON response when
    this returns False.
    """
    host = os.getenv("SMTP_HOST", "")
    if not host:
        return False
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER", "")
        password = os.getenv("SMTP_PASSWORD", "")
        from_addr = os.getenv("SMTP_FROM", user)
        use_ssl = os.getenv("SMTP_USE_SSL", "false").strip().lower() in ("true", "1", "yes")

        # Build the message — multipart/alternative so clients show HTML when supported
        if html:
            msg: MIMEMultipart | MIMEText = MIMEMultipart("alternative")
            assert isinstance(msg, MIMEMultipart)
            msg.attach(MIMEText(plain, "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))
        else:
            msg = MIMEText(plain, "plain", "utf-8")

        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to

        if use_ssl:
            # Direct SSL connection — Gmail port 465
            with smtplib.SMTP_SSL(host, port) as server:
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [to], msg.as_string())
        else:
            # STARTTLS upgrade — standard port 587
            with smtplib.SMTP(host, port) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if user and password:
                    server.login(user, password)
                server.sendmail(from_addr, [to], msg.as_string())
        return True
    except Exception:
        return False


def _otp_html(otp: str, purpose: str, expiry_minutes: int) -> str:
    """Return a clean HTML email body for an OTP."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:30px">
  <div style="max-width:480px;margin:auto;background:#ffffff;border-radius:8px;
              padding:32px;border:1px solid #e0e0e0">
    <h2 style="color:#1a1a2e;margin-top:0">VERSE — {purpose}</h2>
    <p style="color:#444;font-size:15px">Use the code below to complete your request:</p>
    <div style="font-size:36px;font-weight:bold;letter-spacing:10px;
                color:#3b82d4;text-align:center;padding:20px 0">{otp}</div>
    <p style="color:#888;font-size:13px">
      This code expires in <strong>{expiry_minutes} minutes</strong>.
      If you did not request this, you can safely ignore this email.
    </p>
    <hr style="border:none;border-top:1px solid #eee;margin:24px 0">
    <p style="color:#bbb;font-size:11px;text-align:center;margin:0">
      VERSE — AI-powered film continuity platform
    </p>
  </div>
</body>
</html>"""


def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _token_expired(created_at: str, expiry_minutes: int) -> bool:
    """Return True if the token stored at *created_at* (SQLite datetime string) has expired."""
    from datetime import datetime, timezone
    try:
        issued = datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - issued).total_seconds() / 60
        return age > expiry_minutes
    except Exception:
        # Unparseable timestamp — treat as expired to be safe
        return True


# ─── DB helpers for token tables ──────────────────────────────────────────────

# OTP validity windows — keep short enough to be secure, long enough to be usable
_VERIFY_EMAIL_EXPIRY_MINUTES = 30
_RESET_PASSWORD_EXPIRY_MINUTES = 15

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

@router.post("/register", response_model=AuthResponse, status_code=201)
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
    Sends it via SMTP (Gmail or any provider) when configured; returns it in
    the response body in dev mode so the frontend can prefill the field.
    """
    _ensure_token_tables()
    otp = _generate_otp()
    token_hash = _hash_token(otp)

    conn = db()
    with closing(conn.cursor()) as cur:
        cur.execute(
            "INSERT OR REPLACE INTO email_verify_tokens (user_id, token_hash, created_at) "
            "VALUES (?, ?, datetime('now'))",
            (current_user["id"], token_hash),
        )
    conn.commit()

    plain = (
        f"Your VERSE email verification code is: {otp}\n\n"
        f"This code expires in {_VERIFY_EMAIL_EXPIRY_MINUTES} minutes.\n"
        "If you did not request this, you can safely ignore this email."
    )
    sent = _send_email(
        current_user["email"],
        "VERSE — Verify your email",
        plain,
        _otp_html(otp, "Verify your email", _VERIFY_EMAIL_EXPIRY_MINUTES),
    )
    response: dict = {"message": "Verification code sent to your email."}
    if not sent:
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
            "SELECT token_hash, created_at FROM email_verify_tokens WHERE user_id = ?",
            (current_user["id"],),
        ).fetchone()

    if row is None or row["token_hash"] != _hash_token(req.token):
        raise HTTPException(400, "Invalid or expired verification code.")

    # Enforce expiry window
    if _token_expired(row["created_at"], _VERIFY_EMAIL_EXPIRY_MINUTES):
        raise HTTPException(400, "Verification code has expired. Please request a new one.")

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
            "INSERT OR REPLACE INTO password_reset_tokens (email, token_hash, created_at) "
            "VALUES (?, ?, datetime('now'))",
            (req.email.lower(), token_hash),
        )
    conn.commit()

    plain = (
        f"Your VERSE password reset code is: {otp}\n\n"
        f"This code expires in {_RESET_PASSWORD_EXPIRY_MINUTES} minutes.\n"
        "If you did not request this, you can safely ignore this email."
    )
    sent = _send_email(
        req.email.lower(),
        "VERSE — Password reset code",
        plain,
        _otp_html(otp, "Reset your password", _RESET_PASSWORD_EXPIRY_MINUTES),
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
            "SELECT token_hash, created_at FROM password_reset_tokens WHERE email = ?",
            (req.email.lower(),),
        ).fetchone()

    if row is None or row["token_hash"] != _hash_token(req.token):
        raise HTTPException(400, "Invalid or expired reset code.")

    if _token_expired(row["created_at"], _RESET_PASSWORD_EXPIRY_MINUTES):
        raise HTTPException(400, "Reset code has expired. Please request a new one.")

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


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    role: str | None = None
    organization: str | None = None


@router.patch("/me")
def update_me(
    req: UpdateProfileRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Update the authenticated user's editable profile fields (name, role)."""
    updates: dict[str, object] = {}
    if req.name is not None:
        updates["name"] = req.name.strip()
    if req.role is not None:
        # Validate against the known role IDs used by the frontend
        _VALID_ROLES = {
            "producer", "director", "script-supervisor", "continuity-supervisor",
            "production-manager", "department-member", "film-student",
        }
        if req.role not in _VALID_ROLES:
            raise HTTPException(400, f"Unknown role '{req.role}'.")
        updates["role"] = req.role
    if not updates:
        raise HTTPException(400, "No fields to update.")
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    conn = db()
    with closing(conn.cursor()) as cur:
        cur.execute(
            f"UPDATE users SET {set_clause} WHERE id = ?",
            [*updates.values(), current_user["id"]],
        )
        conn.commit()
        row = dict(cur.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],)).fetchone())
    return {k: v for k, v in row.items() if k != "hashed_pw"}
