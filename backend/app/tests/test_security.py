import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _legacy_hs256_token(payload: dict) -> str:
    """Build the same RFC 7519/HS256 wire format used by python-jose."""
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _urlsafe_b64encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    encoded_payload = _urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        settings.JWT_SECRET.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    return f"{encoded_header}.{encoded_payload}.{_urlsafe_b64encode(signature)}"


def test_password_hash_round_trip_and_wrong_password():
    hashed = hash_password("Test12345!")

    assert hashed.startswith(("$2a$", "$2b$", "$2y$"))
    assert verify_password("Test12345!", hashed) is True
    assert verify_password("Wrong12345!", hashed) is False


def test_verify_password_rejects_corrupted_hash():
    assert verify_password("Test12345!", "not-a-bcrypt-hash") is False


def test_access_and_refresh_token_claims_are_preserved():
    access = decode_token(create_access_token("user-123"))
    refresh = decode_token(create_refresh_token("user-123"))

    assert access is not None
    assert access["sub"] == "user-123"
    assert access["type"] == "access"
    assert "exp" in access

    assert refresh is not None
    assert refresh["sub"] == "user-123"
    assert refresh["type"] == "refresh"
    assert "exp" in refresh


def test_decode_token_rejects_expired_and_invalid_tokens():
    expired = create_access_token("user-123", expires_delta=timedelta(seconds=-1))

    assert decode_token(expired) is None
    assert decode_token("not-a-jwt") is None


def test_decode_token_accepts_legacy_hs256_wire_format():
    token = _legacy_hs256_token(
        {
            "sub": "legacy-user",
            "type": "access",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
        }
    )

    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == "legacy-user"
    assert payload["type"] == "access"
