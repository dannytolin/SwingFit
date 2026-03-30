import pytest
from backend.app.services.auth import hash_password, verify_password, create_token, decode_token

def test_hash_and_verify():
    hashed = hash_password("golf123")
    assert hashed != "golf123"
    assert verify_password("golf123", hashed) is True
    assert verify_password("wrong", hashed) is False

def test_create_and_decode_token():
    token = create_token(user_id=42)
    payload = decode_token(token)
    assert payload["user_id"] == 42

def test_decode_invalid_token():
    with pytest.raises(ValueError, match="Invalid token"):
        decode_token("garbage.token.here")

def test_token_contains_exp():
    token = create_token(user_id=1)
    payload = decode_token(token)
    assert "exp" in payload
