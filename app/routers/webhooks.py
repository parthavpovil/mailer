import json

import httpx
from fastapi import APIRouter, Request, Response

from app.db import mark_email_bounced, mark_email_unsubscribed

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/ses-notifications")
async def ses_notifications(request: Request) -> Response:
    body = await request.body()
    payload = json.loads(body)

    if payload.get("Type") == "SubscriptionConfirmation":
        confirm_url = payload.get("SubscribeURL")
        if confirm_url:
            async with httpx.AsyncClient() as client:
                await client.get(confirm_url)
        return Response(status_code=200)

    if payload.get("Type") == "Notification":
        message = json.loads(payload.get("Message", "{}"))
        notification_type = message.get("notificationType")

        if notification_type == "Bounce":
            bounce_info = message.get("bounce", {})
            bounce_type = bounce_info.get("bounceType")
            recipients = [r["emailAddress"] for r in bounce_info.get("bouncedRecipients", [])]

            if bounce_type == "Permanent":
                for email in recipients:
                    await mark_email_bounced(email)

        elif notification_type == "Complaint":
            complaint_info = message.get("complaint", {})
            recipients = [r["emailAddress"] for r in complaint_info.get("complainedRecipients", [])]
            for email in recipients:
                await mark_email_unsubscribed(email)

    return Response(status_code=200)
