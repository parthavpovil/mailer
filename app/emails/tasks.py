import os
from typing import Any

from app.emails.mailer import send_email

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://yourdomain.com")


async def send_welcome_email(ctx: dict[str, Any], *, to: str, username: str) -> None:
    await send_email(
        to=to,
        subject="Welcome to the store",
        template_name="welcome.html",
        context={"username": username, "frontend_url": FRONTEND_URL},
    )


async def send_order_confirmation(
    ctx: dict[str, Any],
    *,
    to: str,
    username: str,
    order_id: str,
    items: list[dict[str, Any]],
    total: str,
    estimated_delivery: str,
) -> None:
    await send_email(
        to=to,
        subject=f"Order #{order_id} Confirmed",
        template_name="order_confirmation.html",
        context={
            "username": username,
            "order_id": order_id,
            "items": items,
            "total": total,
            "estimated_delivery": estimated_delivery,
            "frontend_url": FRONTEND_URL,
        },
    )


async def send_order_shipped(
    ctx: dict[str, Any],
    *,
    to: str,
    username: str,
    order_id: str,
    tracking_number: str,
    carrier: str,
    tracking_url: str,
) -> None:
    await send_email(
        to=to,
        subject=f"Order #{order_id} Has Shipped",
        template_name="order_shipped.html",
        context={
            "username": username,
            "order_id": order_id,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "tracking_url": tracking_url,
            "frontend_url": FRONTEND_URL,
        },
    )


async def send_order_delivered(
    ctx: dict[str, Any],
    *,
    to: str,
    username: str,
    order_id: str,
    review_url: str,
) -> None:
    await send_email(
        to=to,
        subject=f"Order #{order_id} Delivered",
        template_name="order_delivered.html",
        context={
            "username": username,
            "order_id": order_id,
            "review_url": review_url,
            "frontend_url": FRONTEND_URL,
        },
    )


async def send_payment_failed(
    ctx: dict[str, Any],
    *,
    to: str,
    username: str,
    order_id: str,
    retry_url: str,
) -> None:
    await send_email(
        to=to,
        subject=f"Payment Failed for Order #{order_id}",
        template_name="payment_failed.html",
        context={
            "username": username,
            "order_id": order_id,
            "retry_url": retry_url,
            "frontend_url": FRONTEND_URL,
        },
    )


async def send_password_reset(
    ctx: dict[str, Any],
    *,
    to: str,
    username: str,
    reset_url: str,
) -> None:
    await send_email(
        to=to,
        subject="Reset Your Password",
        template_name="password_reset.html",
        context={
            "username": username,
            "reset_url": reset_url,
            "expiry_minutes": 30,
            "frontend_url": FRONTEND_URL,
        },
    )


async def send_refund_initiated(
    ctx: dict[str, Any],
    *,
    to: str,
    username: str,
    order_id: str,
    amount: str,
    timeline_days: int,
) -> None:
    await send_email(
        to=to,
        subject=f"Refund Initiated for Order #{order_id}",
        template_name="refund_initiated.html",
        context={
            "username": username,
            "order_id": order_id,
            "amount": amount,
            "timeline_days": timeline_days,
            "frontend_url": FRONTEND_URL,
        },
    )


async def send_bulk_announcement_email(ctx: dict[str, Any], *, to: str, username: str) -> None:
    await send_email(
        to=to,
        subject="A Message from Booknitive",
        template_name="bulk_announcement.html",
        context={"username": username, "frontend_url": FRONTEND_URL},
    )
