from typing import Any

from fastapi import APIRouter
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

router = APIRouter(prefix="/queue", tags=["queue"])


class WelcomePayload(BaseModel):
    to: EmailStr
    username: str


class OrderConfirmationPayload(BaseModel):
    to: EmailStr
    username: str
    order_id: str
    items: list[dict[str, Any]]
    total: str
    estimated_delivery: str


class OrderShippedPayload(BaseModel):
    to: EmailStr
    username: str
    order_id: str
    tracking_number: str
    carrier: str
    tracking_url: str


class OrderDeliveredPayload(BaseModel):
    to: EmailStr
    username: str
    order_id: str
    review_url: str


class PaymentFailedPayload(BaseModel):
    to: EmailStr
    username: str
    order_id: str
    retry_url: str


class PasswordResetPayload(BaseModel):
    to: EmailStr
    username: str
    reset_url: str


class RefundInitiatedPayload(BaseModel):
    to: EmailStr
    username: str
    order_id: str
    amount: str
    timeline_days: int


@router.post("/welcome")
async def enqueue_welcome(payload: WelcomePayload) -> dict[str, str]:
    await queue_welcome_email(to=str(payload.to), username=payload.username)
    return {"status": "queued"}


@router.post("/order-confirmation")
async def enqueue_order_confirmation(payload: OrderConfirmationPayload) -> dict[str, str]:
    await queue_order_confirmation(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        items=payload.items,
        total=payload.total,
        estimated_delivery=payload.estimated_delivery,
    )
    return {"status": "queued"}


@router.post("/order-shipped")
async def enqueue_order_shipped(payload: OrderShippedPayload) -> dict[str, str]:
    await queue_order_shipped(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        tracking_number=payload.tracking_number,
        carrier=payload.carrier,
        tracking_url=payload.tracking_url,
    )
    return {"status": "queued"}


@router.post("/order-delivered")
async def enqueue_order_delivered(payload: OrderDeliveredPayload) -> dict[str, str]:
    await queue_order_delivered(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        review_url=payload.review_url,
    )
    return {"status": "queued"}


@router.post("/payment-failed")
async def enqueue_payment_failed(payload: PaymentFailedPayload) -> dict[str, str]:
    await queue_payment_failed(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        retry_url=payload.retry_url,
    )
    return {"status": "queued"}


@router.post("/password-reset")
async def enqueue_password_reset(payload: PasswordResetPayload) -> dict[str, str]:
    await queue_password_reset(
        to=str(payload.to),
        username=payload.username,
        reset_url=payload.reset_url,
    )
    return {"status": "queued"}


@router.post("/refund-initiated")
async def enqueue_refund_initiated(payload: RefundInitiatedPayload) -> dict[str, str]:
    await queue_refund_initiated(
        to=str(payload.to),
        username=payload.username,
        order_id=payload.order_id,
        amount=payload.amount,
        timeline_days=payload.timeline_days,
    )
    return {"status": "queued"}
