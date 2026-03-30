import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user

router = APIRouter(prefix="/billing", tags=["billing"])
stripe.api_key = settings.stripe_secret_key


class CheckoutRequest(BaseModel):
    plan: str  # "monthly" or "yearly"


@router.post("/checkout")
def create_checkout_session(req: CheckoutRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    price_id = settings.stripe_price_monthly if req.plan == "monthly" else settings.stripe_price_yearly
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
        user.stripe_customer_id = str(customer.id)
        db.commit()
    checkout = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.frontend_url}/billing?status=success",
        cancel_url=f"{settings.frontend_url}/billing?status=cancelled",
        metadata={"user_id": str(user.id)},
    )
    return {"checkout_url": checkout.url}


@router.get("/status")
def get_subscription_status(user: User = Depends(get_current_user)):
    return {"user_id": user.id, "tier": user.subscription_tier, "stripe_customer_id": user.stripe_customer_id}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = int(session["metadata"]["user_id"])
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.subscription_tier = "pro"
            db.commit()
    elif event["type"] == "customer.subscription.deleted":
        customer_id = event["data"]["object"]["customer"]
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_tier = "free"
            db.commit()
    return {"status": "ok"}
