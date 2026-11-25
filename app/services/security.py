import secrets

import bcrypt
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ..config import get_settings

settings = get_settings()

_serializer = URLSafeTimedSerializer(
    settings.session_secret,
    salt="torre-control-session",
)


def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(
        pin.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.pin_rounds),
    ).decode("utf-8")


def verify_pin(pin: str, pin_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pin.encode("utf-8"), pin_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_session_token(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})


def read_session_token(token: str | None) -> int | None:
    if not token:
        return None
    try:
        data = _serializer.loads(token, max_age=settings.session_max_age)
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    user_id = data.get("uid")
    return user_id if isinstance(user_id, int) else None


def generate_secret() -> str:
    return secrets.token_urlsafe(48)
