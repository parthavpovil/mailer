import os
from typing import Any

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings
from dotenv import load_dotenv

from app.emails.tasks import (
    send_bulk_announcement_email,
    send_order_confirmation,
    send_order_delivered,
    send_order_shipped,
    send_password_reset,
    send_payment_failed,
    send_refund_initiated,
    send_welcome_email,
)

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def get_redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(REDIS_URL)


class WorkerSettings:
    functions = [
        send_welcome_email,
        send_order_confirmation,
        send_order_shipped,
        send_order_delivered,
        send_payment_failed,
        send_password_reset,
        send_refund_initiated,
        send_bulk_announcement_email,
    ]
    redis_settings = get_redis_settings()
    max_tries = 3
    job_timeout = 30


_pool: ArqRedis | None = None


async def get_email_queue() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(get_redis_settings())
    return _pool


async def close_email_queue() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


async def queue_welcome_email(to: str, username: str) -> None:
    pool = await get_email_queue()
    await pool.enqueue_job("send_welcome_email", to=to, username=username)


async def queue_order_confirmation(
    to: str,
    username: str,
    order_id: str,
    items: list[dict[str, Any]],
    total: str,
    estimated_delivery: str,
) -> None:
    pool = await get_email_queue()
    await pool.enqueue_job(
        "send_order_confirmation",
        to=to,
        username=username,
        order_id=order_id,
        items=items,
        total=total,
        estimated_delivery=estimated_delivery,
    )


async def queue_order_shipped(
    to: str,
    username: str,
    order_id: str,
    tracking_number: str,
    carrier: str,
    tracking_url: str,
) -> None:
    pool = await get_email_queue()
    await pool.enqueue_job(
        "send_order_shipped",
        to=to,
        username=username,
        order_id=order_id,
        tracking_number=tracking_number,
        carrier=carrier,
        tracking_url=tracking_url,
    )


async def queue_order_delivered(to: str, username: str, order_id: str, review_url: str) -> None:
    pool = await get_email_queue()
    await pool.enqueue_job(
        "send_order_delivered",
        to=to,
        username=username,
        order_id=order_id,
        review_url=review_url,
    )


async def queue_payment_failed(to: str, username: str, order_id: str, retry_url: str) -> None:
    pool = await get_email_queue()
    await pool.enqueue_job(
        "send_payment_failed",
        to=to,
        username=username,
        order_id=order_id,
        retry_url=retry_url,
    )


async def queue_password_reset(to: str, username: str, reset_url: str) -> None:
    pool = await get_email_queue()
    await pool.enqueue_job("send_password_reset", to=to, username=username, reset_url=reset_url)


async def queue_refund_initiated(
    to: str,
    username: str,
    order_id: str,
    amount: str,
    timeline_days: int,
) -> None:
    pool = await get_email_queue()
    await pool.enqueue_job(
        "send_refund_initiated",
        to=to,
        username=username,
        order_id=order_id,
        amount=amount,
        timeline_days=timeline_days,
    )


async def queue_bulk_announcement(to: str, username: str) -> None:
    pool = await get_email_queue()
    await pool.enqueue_job("send_bulk_announcement_email", to=to, username=username)
