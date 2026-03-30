import jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def get_current_user(
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Verify a Supabase JWT and return (or auto-create) the backend User."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.split(" ", 1)[1]

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    supabase_uid: str = payload.get("sub", "")
    email: str = payload.get("email", "")
    if not supabase_uid:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    # Look up by supabase_uid first, then fall back to email
    user = db.query(User).filter(User.supabase_uid == supabase_uid).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Link existing email-matched user to Supabase UID
            user.supabase_uid = supabase_uid
            db.commit()
        else:
            # Auto-create a new backend user on first Supabase login
            user = User(
                supabase_uid=supabase_uid,
                email=email,
                username=email.split("@")[0],
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    return user


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "supabase_uid": user.supabase_uid,
        "subscription_tier": user.subscription_tier,
    }
