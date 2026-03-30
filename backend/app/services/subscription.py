from fastapi import Depends, HTTPException
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user

FREE_SESSION_LIMIT = 1
FREE_CLUB_TYPES = {"driver"}

def require_pro(user: User = Depends(get_current_user)) -> User:
    if user.subscription_tier != "pro":
        raise HTTPException(status_code=403, detail="Pro subscription required. Upgrade to access this feature.")
    return user

def check_free_tier_limits(user: User, club_type: str) -> None:
    if user.subscription_tier == "pro":
        return
    if club_type not in FREE_CLUB_TYPES:
        raise HTTPException(status_code=403, detail=f"Free tier only supports driver recommendations. Upgrade to Pro for {club_type}.")
