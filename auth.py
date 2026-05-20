# ============================================================
# auth.py — Authentication & JWT Token Management
# ============================================================
# Handles:
#   • Password hashing with bcrypt (never store plain passwords!)
#   • JWT token creation and validation
#   • User registration and login logic
#   • Session state management for Streamlit
# ============================================================

import os
import bcrypt
from datetime import datetime, timedelta, timezone
from pathlib import Path
from jose import JWTError, jwt
from dotenv import load_dotenv
import streamlit as st
from database import db_create_user, db_get_user_by_email, db_log_login

load_dotenv(dotenv_path=Path(__file__).with_name('.env'))

# ── JWT Configuration ─────────────────────────────────────────
JWT_SECRET   = (os.getenv("JWT_SECRET_KEY", "fallback-secret-change-me") or "fallback-secret-change-me").strip()
JWT_ALGO     = (os.getenv("JWT_ALGORITHM", "HS256") or "HS256").strip()
JWT_EXPIRY_H = int((os.getenv("JWT_EXPIRY_HOURS", 24) or 24))


# ── Password Utilities ─────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.
    bcrypt automatically adds a 'salt' (random data) so two identical
    passwords produce different hashes — much more secure than MD5/SHA!
    Returns the hash as a string.
    """
    salt = bcrypt.gensalt(rounds=12)          # 12 rounds = strong but fast enough
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Check if a plain-text password matches the stored hash.
    Returns True if they match, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


# ── JWT Token Utilities ────────────────────────────────────────

def create_jwt_token(user_id: str, email: str) -> str:
    """
    Create a JWT (JSON Web Token) containing user identity.
    JWT = Header.Payload.Signature  (3 parts separated by dots)
    The payload includes:
      • sub  = subject (user ID)
      • email
      • exp  = expiration timestamp (auto-invalidates token)
      • iat  = issued-at timestamp
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRY_H)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    return token


def decode_jwt_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.
    Returns the payload dict if valid, or None if expired/invalid.
    JWTError is raised if the token has been tampered with.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        return payload
    except JWTError:
        return None


# ── Registration ───────────────────────────────────────────────

def register_user(email: str, username: str, password: str) -> tuple[bool, str]:
    """
    Register a new user account.
    Steps:
      1. Check if email is already taken
      2. Hash the password (never save plain text!)
      3. Insert user into database
      4. Return (success, message) tuple
    """
    email = email.strip().lower()
    username = username.strip()

    # Basic validation
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if len(username) < 3:
        return False, "Username must be at least 3 characters."

    # Check for existing account
    existing = db_get_user_by_email(email)
    if existing:
        return False, "An account with this email already exists. Please login."

    # Hash and store
    password_hash = hash_password(password)

    try:
        user = db_create_user(email, username, password_hash)
        if user:
            return True, "Account created successfully! You can now login. 🎉"
        return False, "Registration failed. Please try again."
    except Exception as e:
        error_msg = str(e)
        if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
            return False, "Email already registered. Please login instead."
        return False, f"Registration error: {error_msg}"


# ── Login ──────────────────────────────────────────────────────

def login_user(email: str, password: str, user_agent: str = "unknown") -> tuple[bool, str, dict | None]:
    """
    Authenticate a user and create a JWT session.
    Steps:
      1. Look up user by email
      2. Verify password hash
      3. Generate JWT token
      4. Log the login event
      5. Return (success, message, user_data) tuple
    """
    email = email.strip().lower()

    # Find user
    user = db_get_user_by_email(email)
    if not user:
        return False, "No account found with this email address.", None

    # Check password
    if not verify_password(password, user["password_hash"]):
        return False, "Incorrect password. Please try again.", None

    # Generate JWT token
    token = create_jwt_token(user["id"], user["email"])

    # Record login in history (fire-and-forget, non-blocking)
    db_log_login(user["id"], ip_address="session", user_agent=user_agent)

    return True, f"Welcome back, {user['username']}! 👋", {
        "user_id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "token": token
    }


# ── Session State Helpers ──────────────────────────────────────

def init_session_state() -> None:
    """
    Initialize all Streamlit session state variables.
    session_state persists values across page rerenders within
    the same browser tab session.
    Call this once at the top of app.py.
    """
    defaults = {
        "authenticated": False,
        "user_id": None,
        "email": None,
        "username": None,
        "jwt_token": None,
        "current_page": "home",
        "edit_expense_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def set_session(user_data: dict) -> None:
    """Store logged-in user info into Streamlit session state."""
    st.session_state.authenticated = True
    st.session_state.user_id       = user_data["user_id"]
    st.session_state.email         = user_data["email"]
    st.session_state.username      = user_data["username"]
    st.session_state.jwt_token     = user_data["token"]
    st.session_state.current_page  = "dashboard"


def clear_session() -> None:
    """Log out: clear all session state variables."""
    for key in ["authenticated", "user_id", "email", "username", "jwt_token"]:
        st.session_state[key] = None
    st.session_state.authenticated = False
    st.session_state.current_page  = "home"


def is_authenticated() -> bool:
    """
    Check if the current user is logged in AND their JWT is still valid.
    This double-checks the token hasn't expired.
    """
    if not st.session_state.get("authenticated"):
        return False

    token = st.session_state.get("jwt_token")
    if not token:
        return False

    payload = decode_jwt_token(token)
    if not payload:
        # Token expired or invalid → force logout
        clear_session()
        return False

    return True


def require_auth() -> None:
    """
    Gate function: if user is not authenticated, stop rendering and
    show login prompt. Use this at the top of protected pages.
    """
    if not is_authenticated():
        st.warning("🔒 Please login to access this page.")
        st.stop()
