import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.emails.queue import (
    queue_order_confirmation,
    queue_order_delivered,
    queue_order_shipped,
    queue_password_reset,
    queue_payment_failed,
    queue_refund_initiated,
    queue_welcome_email,
)

router = APIRouter(prefix="/dev/email-tests", tags=["dev-email-tests"])


class EmailTestRequest(BaseModel):
    to: EmailStr
    username: str = "test-user"


class OrderConfirmationRequest(EmailTestRequest):
    order_id: str = "1001"
    items: list[dict[str, Any]] = [
        {"name": "Sample Product", "qty": 1, "price": "$19.99"},
        {"name": "Second Item", "qty": 2, "price": "$7.50"},
    ]
    total: str = "$34.99"
    estimated_delivery: str = "3-5 business days"


class OrderShippedRequest(EmailTestRequest):
    order_id: str = "1001"
    tracking_number: str = "TRK123456"
    carrier: str = "UPS"
    tracking_url: str = "https://example.com/track/TRK123456"


class OrderDeliveredRequest(EmailTestRequest):
    order_id: str = "1001"
    review_url: str = "https://yourdomain.com/review/1001"


class PaymentFailedRequest(EmailTestRequest):
    order_id: str = "1001"
    retry_url: str = "https://yourdomain.com/payments/retry/1001"


class PasswordResetRequest(EmailTestRequest):
    reset_url: str = "https://yourdomain.com/reset-password/token-123"


class RefundInitiatedRequest(EmailTestRequest):
    order_id: str = "1001"
    amount: str = "$34.99"
    timeline_days: int = 5


def _ensure_enabled() -> None:
    enabled = os.getenv("ENABLE_EMAIL_TEST_ROUTES", "false").lower() == "true"
    if not enabled:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/welcome")
async def test_welcome(payload: EmailTestRequest) -> dict[str, str]:
    _ensure_enabled()
    await queue_welcome_email(to=str(payload.to), username=payload.username)
    return {"status": "queued", "job": "send_welcome_email"}


@router.post("/order-confirmation")
async def test_order_confirmation(payload: OrderConfirmationRequest) -> dict[str, str]:
    _ensure_enabled()
    await queue_order_confirmation(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        items=payload.items,
        total=payload.total,
        estimated_delivery=payload.estimated_delivery,
    )
    return {"status": "queued", "job": "send_order_confirmation"}


@router.post("/order-shipped")
async def test_order_shipped(payload: OrderShippedRequest) -> dict[str, str]:
    _ensure_enabled()
    await queue_order_shipped(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        tracking_number=payload.tracking_number,
        carrier=payload.carrier,
        tracking_url=payload.tracking_url,
    )
    return {"status": "queued", "job": "send_order_shipped"}


@router.post("/order-delivered")
async def test_order_delivered(payload: OrderDeliveredRequest) -> dict[str, str]:
    _ensure_enabled()
    await queue_order_delivered(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        review_url=payload.review_url,
    )
    return {"status": "queued", "job": "send_order_delivered"}


@router.post("/payment-failed")
async def test_payment_failed(payload: PaymentFailedRequest) -> dict[str, str]:
    _ensure_enabled()
    await queue_payment_failed(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        retry_url=payload.retry_url,
    )
    return {"status": "queued", "job": "send_payment_failed"}


@router.post("/password-reset")
async def test_password_reset(payload: PasswordResetRequest) -> dict[str, str]:
    _ensure_enabled()
    await queue_password_reset(
        to=str(payload.to),
        username=payload.username,
        reset_url=payload.reset_url,
    )
    return {"status": "queued", "job": "send_password_reset"}


@router.post("/refund-initiated")
async def test_refund_initiated(payload: RefundInitiatedRequest) -> dict[str, str]:
    _ensure_enabled()
    await queue_refund_initiated(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        amount=payload.amount,
        timeline_days=payload.timeline_days,
    )
    return {"status": "queued", "job": "send_refund_initiated"}
