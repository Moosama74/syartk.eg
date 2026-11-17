import hashlib
import hmac
import base64
import json
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse

# Secret key for signing session tokens (in production, loaded from env)
SECRET_KEY = "motora-super-secret-luxury-automotive-key-2026-cairo"

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash a password using SHA-256 with a unique salt."""
    if not salt:
        salt = base64.b64encode(hashlib.sha256(str(time.time()).encode()).digest()[:16]).decode('utf-8')
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${base64.b64encode(key).decode('utf-8')}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify a plain password against the stored salt$hash."""
    try:
        parts = hashed.split('$')
        if len(parts) != 2:
            return False
        salt, _ = parts
        candidate = hash_password(password, salt)
        return hmac.compare_digest(candidate, hashed)
    except Exception:
        return False

def create_session_token(user_id: int, username: str, expires_days: int = 7) -> str:
    """Create a signed tamper-proof JSON session token."""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": int(time.time()) + (expires_days * 86400)
    }
    raw_payload = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    b64_payload = base64.urlsafe_b64encode(raw_payload).decode('utf-8')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), b64_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{sig}"

def verify_session_token(token: str) -> Optional[dict]:
    """Verify session token signature and check expiration."""
    if not token or '.' not in token:
        return None
    try:
        b64_payload, sig = token.split('.', 1)
        expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), b64_payload.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload_bytes = base64.urlsafe_b64decode(b64_payload.encode('utf-8'))
        payload = json.loads(payload_bytes.decode('utf-8'))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None

def get_current_admin(request: Request) -> Optional[dict]:
    """Retrieve authenticated admin session from cookie, or return None."""
    token = request.cookies.get("motora_admin_session")
    if not token:
        return None
    return verify_session_token(token)

def require_admin(request: Request) -> dict:
    """Dependency that ensures admin is logged in, else raises 303 Redirect to login."""
    admin = get_current_admin(request)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/admin/login"}
        )
    return admin

# ----------------- CUSTOMER AUTHENTICATION -----------------

def create_customer_token(user_id: int, email: str, name: str, expires_days: int = 30) -> str:
    """Create a signed session token for customers/visitors."""
    payload = {
        "user_id": user_id,
        "email": email,
        "name": name,
        "exp": int(time.time()) + (expires_days * 86400)
    }
    raw_payload = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    b64_payload = base64.urlsafe_b64encode(raw_payload).decode('utf-8')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), b64_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{b64_payload}.{sig}"

def get_current_user(request: Request) -> Optional[dict]:
    """Retrieve logged-in customer user from cookie or None."""
    token = request.cookies.get("syartk_user_session")
    if not token:
        return None
    return verify_session_token(token)

def require_user(request: Request) -> dict:
    """Dependency that ensures customer is logged in, else redirects to /login."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login"}
        )
    return user
