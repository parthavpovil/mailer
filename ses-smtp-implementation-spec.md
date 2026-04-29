# Email Service Implementation Spec
## Amazon SES + Postfix + FastAPI + ARQ (Redis Queue)

---

## Project Goal

Set up a production-grade transactional email system for an e-commerce FastAPI backend.
The system must:
- Use Amazon SES as the email delivery provider
- Use Postfix on the same VPS as a local SMTP relay (app never talks to SES directly)
- Queue all outgoing emails via ARQ (async Redis queue) — no inline sending in request handlers
- Handle bounces and complaints from SES via SNS webhook
- Support all standard e-commerce transactional email types
- Be modular — adding a new email type should require minimal code changes

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Email sending | Postfix (SMTP relay on localhost:25) |
| Email provider | Amazon SES (SMTP relay, us-east-1 or your region) |
| Queue | ARQ (async job queue backed by Redis) |
| Queue broker | Redis (already installed on VPS) |
| Templating | Jinja2 |
| Email library | `aiosmtplib` (async SMTP) |

---

## Directory Structure

Implement exactly this structure inside your existing FastAPI project:

```
app/
├── emails/
│   ├── __init__.py
│   ├── mailer.py            # Core async send function (talks to localhost:25)
│   ├── queue.py             # ARQ worker definition and job enqueueing
│   ├── tasks.py             # One async function per email type
│   └── templates/
│       ├── base.html        # Base HTML layout all templates extend
│       ├── order_confirmation.html
│       ├── order_shipped.html
│       ├── order_delivered.html
│       ├── payment_failed.html
│       ├── password_reset.html
│       ├── welcome.html
│       └── refund_initiated.html
├── routers/
│   └── webhooks.py          # SNS bounce/complaint webhook endpoint
└── main.py                  # Register webhook router here
```

---

## Environment Variables

Add these to your `.env` file. Do not hardcode any of these anywhere.

```env
# Email config
MAIL_FROM=no-reply@yourdomain.com
MAIL_FROM_NAME=Your Store Name
MAIL_HOST=127.0.0.1
MAIL_PORT=25

# Redis (ARQ)
REDIS_URL=redis://localhost:6379

# App
FRONTEND_URL=https://yourdomain.com
```

No SES credentials go in the app — those live in Postfix config on the OS level.

---

## System Components

### Component 1 — Postfix (OS level, not Python)

Postfix runs as a system daemon. It receives mail from the app on `localhost:25` and relays it to SES.

**Do not implement this in Python.** This is a sysadmin task. Steps:

1. Install Postfix:
```bash
sudo apt update && sudo apt install -y postfix libsasl2-modules mailutils
# Select "Internet Site" during install
```

2. Write `/etc/postfix/main.cf`:
```ini
myhostname = mail.yourdomain.com
myorigin = /etc/mailname
mydestination = localhost
relayhost = [email-smtp.us-east-1.amazonaws.com]:587

smtp_sasl_auth_enable = yes
smtp_sasl_security_options = noanonymous
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_use_tls = yes
smtp_tls_security_level = encrypt
smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt

inet_interfaces = loopback-only
```

3. Write `/etc/postfix/sasl_passwd`:
```
[email-smtp.us-east-1.amazonaws.com]:587 SES_SMTP_USER:SES_SMTP_PASSWORD
```

4. Secure and apply:
```bash
sudo chmod 600 /etc/postfix/sasl_passwd
sudo postmap /etc/postfix/sasl_passwd
sudo systemctl restart postfix && sudo systemctl enable postfix
```

5. Test:
```bash
echo "Test" | mail -s "Test Subject" -a "From: no-reply@yourdomain.com" verified@youremail.com
sudo tail -f /var/log/mail.log  # Should show status=sent
```

---

### Component 2 — Python Dependencies

Add to `requirements.txt`:
```
aiosmtplib
arq
jinja2
python-dotenv
```

---

### Component 3 — `app/emails/mailer.py`

This is the only place in the codebase that sends email. Everything else calls this.

```python
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
import os

TEMPLATES_DIR = Path(__file__).parent / "templates"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"])
)

MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@yourdomain.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Store")
MAIL_HOST = os.getenv("MAIL_HOST", "127.0.0.1")
MAIL_PORT = int(os.getenv("MAIL_PORT", 25))


def render_template(template_name: str, context: dict) -> str:
    template = jinja_env.get_template(template_name)
    return template.render(**context)


async def send_email(to: str, subject: str, template_name: str, context: dict):
    html_body = render_template(template_name, context)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    await aiosmtplib.send(
        msg,
        hostname=MAIL_HOST,
        port=MAIL_PORT,
        start_tls=False,   # Postfix handles TLS upstream, localhost is plain
    )
```

---

### Component 4 — `app/emails/tasks.py`

One async function per email type. These are the functions ARQ will execute as jobs.
Each function receives only serializable arguments (strings, dicts) — no ORM objects.

```python
from app.emails.mailer import send_email
import os

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://yourdomain.com")


async def send_welcome_email(ctx, *, to: str, username: str):
    await send_email(
        to=to,
        subject="Welcome to the store",
        template_name="welcome.html",
        context={"username": username, "frontend_url": FRONTEND_URL}
    )


async def send_order_confirmation(ctx, *, to: str, username: str, order_id: str,
                                   items: list, total: str, estimated_delivery: str):
    await send_email(
        to=to,
        subject=f"Order #{order_id} Confirmed",
        template_name="order_confirmation.html",
        context={
            "username": username,
            "order_id": order_id,
            "items": items,          # list of dicts: [{name, qty, price}]
            "total": total,
            "estimated_delivery": estimated_delivery,
            "frontend_url": FRONTEND_URL
        }
    )


async def send_order_shipped(ctx, *, to: str, username: str, order_id: str,
                              tracking_number: str, carrier: str, tracking_url: str):
    await send_email(
        to=to,
        subject=f"Order #{order_id} Has Shipped",
        template_name="order_shipped.html",
        context={
            "username": username,
            "order_id": order_id,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "tracking_url": tracking_url
        }
    )


async def send_order_delivered(ctx, *, to: str, username: str, order_id: str,
                                review_url: str):
    await send_email(
        to=to,
        subject=f"Order #{order_id} Delivered",
        template_name="order_delivered.html",
        context={
            "username": username,
            "order_id": order_id,
            "review_url": review_url
        }
    )


async def send_payment_failed(ctx, *, to: str, username: str, order_id: str,
                               retry_url: str):
    await send_email(
        to=to,
        subject=f"Payment Failed for Order #{order_id}",
        template_name="payment_failed.html",
        context={
            "username": username,
            "order_id": order_id,
            "retry_url": retry_url
        }
    )


async def send_password_reset(ctx, *, to: str, username: str, reset_url: str):
    await send_email(
        to=to,
        subject="Reset Your Password",
        template_name="password_reset.html",
        context={
            "username": username,
            "reset_url": reset_url,
            "expiry_minutes": 30
        }
    )


async def send_refund_initiated(ctx, *, to: str, username: str, order_id: str,
                                 amount: str, timeline_days: int):
    await send_email(
        to=to,
        subject=f"Refund Initiated for Order #{order_id}",
        template_name="refund_initiated.html",
        context={
            "username": username,
            "order_id": order_id,
            "amount": amount,
            "timeline_days": timeline_days
        }
    )
```

---

### Component 5 — `app/emails/queue.py`

ARQ worker settings and the enqueue helper your routers will call.

```python
import os
from arq import create_pool
from arq.connections import RedisSettings
from app.emails.tasks import (
    send_welcome_email,
    send_order_confirmation,
    send_order_shipped,
    send_order_delivered,
    send_payment_failed,
    send_password_reset,
    send_refund_initiated,
)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def get_redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(REDIS_URL)


# ARQ WorkerSettings — used when running the worker process
class WorkerSettings:
    functions = [
        send_welcome_email,
        send_order_confirmation,
        send_order_shipped,
        send_order_delivered,
        send_payment_failed,
        send_password_reset,
        send_refund_initiated,
    ]
    redis_settings = get_redis_settings()
    max_tries = 3
    job_timeout = 30


# Call this once at app startup to create the Redis pool
_pool = None

async def get_email_queue():
    global _pool
    if _pool is None:
        _pool = await create_pool(get_redis_settings())
    return _pool


# Enqueue helpers — call these from your routers/services
async def queue_welcome_email(to: str, username: str):
    pool = await get_email_queue()
    await pool.enqueue_job("send_welcome_email", to=to, username=username)


async def queue_order_confirmation(to: str, username: str, order_id: str,
                                    items: list, total: str, estimated_delivery: str):
    pool = await get_email_queue()
    await pool.enqueue_job("send_order_confirmation", to=to, username=username,
                           order_id=order_id, items=items, total=total,
                           estimated_delivery=estimated_delivery)


async def queue_order_shipped(to: str, username: str, order_id: str,
                               tracking_number: str, carrier: str, tracking_url: str):
    pool = await get_email_queue()
    await pool.enqueue_job("send_order_shipped", to=to, username=username,
                           order_id=order_id, tracking_number=tracking_number,
                           carrier=carrier, tracking_url=tracking_url)


async def queue_order_delivered(to: str, username: str, order_id: str, review_url: str):
    pool = await get_email_queue()
    await pool.enqueue_job("send_order_delivered", to=to, username=username,
                           order_id=order_id, review_url=review_url)


async def queue_payment_failed(to: str, username: str, order_id: str, retry_url: str):
    pool = await get_email_queue()
    await pool.enqueue_job("send_payment_failed", to=to, username=username,
                           order_id=order_id, retry_url=retry_url)


async def queue_password_reset(to: str, username: str, reset_url: str):
    pool = await get_email_queue()
    await pool.enqueue_job("send_password_reset", to=to, username=username,
                           reset_url=reset_url)


async def queue_refund_initiated(to: str, username: str, order_id: str,
                                  amount: str, timeline_days: int):
    pool = await get_email_queue()
    await pool.enqueue_job("send_refund_initiated", to=to, username=username,
                           order_id=order_id, amount=amount, timeline_days=timeline_days)
```

---

### Component 6 — Usage in Routers

This is how you call the queue from your existing FastAPI route handlers.
**Never call `send_email` directly from a router.**

```python
# Example: inside your orders router
from app.emails.queue import queue_order_confirmation

@router.post("/orders")
async def create_order(payload: OrderCreate, current_user: User = Depends(get_current_user)):
    order = await Order.create(payload)

    await queue_order_confirmation(
        to=current_user.email,
        username=current_user.username,
        order_id=str(order.id),
        items=[{"name": i.name, "qty": i.quantity, "price": str(i.price)} for i in order.items],
        total=str(order.total),
        estimated_delivery="3-5 business days"
    )

    return order
```

---

### Component 7 — `app/routers/webhooks.py`

SNS will POST here for every bounce and complaint SES receives.
You must suppress bounced/complained emails in your DB — implement `mark_email_bounced`
and `mark_email_unsubscribed` against your actual User model.

```python
import json
import httpx
from fastapi import APIRouter, Request, Response
from app.db import mark_email_bounced, mark_email_unsubscribed  # implement these

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/ses-notifications")
async def ses_notifications(request: Request):
    body = await request.body()
    payload = json.loads(body)

    # SNS sends this once when you first subscribe your endpoint
    if payload.get("Type") == "SubscriptionConfirmation":
        confirm_url = payload.get("SubscribeURL")
        async with httpx.AsyncClient() as client:
            await client.get(confirm_url)
        return Response(status_code=200)

    if payload.get("Type") == "Notification":
        message = json.loads(payload.get("Message", "{}"))
        notification_type = message.get("notificationType")

        if notification_type == "Bounce":
            bounce_type = message["bounce"]["bounceType"]
            recipients = [r["emailAddress"] for r in message["bounce"]["bouncedRecipients"]]

            if bounce_type == "Permanent":
                # Hard bounce — address doesn't exist, stop sending forever
                for email in recipients:
                    await mark_email_bounced(email)

        elif notification_type == "Complaint":
            recipients = [r["emailAddress"] for r in message["complaint"]["complainedRecipients"]]
            # User marked as spam — unsubscribe immediately
            for email in recipients:
                await mark_email_unsubscribed(email)

    return Response(status_code=200)
```

Register in `main.py`:
```python
from app.routers.webhooks import router as webhooks_router
app.include_router(webhooks_router)
```

---

### Component 8 — Jinja2 Templates

Create `app/emails/templates/base.html` — all other templates extend this:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}{% endblock %}</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }
    .container { max-width: 600px; margin: 40px auto; background: #fff; padding: 32px; border-radius: 6px; }
    .footer { margin-top: 32px; font-size: 12px; color: #999; text-align: center; }
  </style>
</head>
<body>
  <div class="container">
    {% block content %}{% endblock %}
    <div class="footer">© Your Store. You're receiving this because you have an account with us.</div>
  </div>
</body>
</html>
```

Example `order_confirmation.html`:
```html
{% extends "base.html" %}
{% block title %}Order Confirmed{% endblock %}
{% block content %}
  <h2>Hi {{ username }}, your order is confirmed.</h2>
  <p>Order ID: <strong>{{ order_id }}</strong></p>
  <table width="100%" cellpadding="8">
    <tr><th align="left">Item</th><th>Qty</th><th>Price</th></tr>
    {% for item in items %}
    <tr>
      <td>{{ item.name }}</td>
      <td>{{ item.qty }}</td>
      <td>{{ item.price }}</td>
    </tr>
    {% endfor %}
  </table>
  <p><strong>Total: {{ total }}</strong></p>
  <p>Estimated delivery: {{ estimated_delivery }}</p>
  <p><a href="{{ frontend_url }}/orders/{{ order_id }}">View Order</a></p>
{% endblock %}
```

Implement the remaining templates (`order_shipped.html`, `order_delivered.html`, `payment_failed.html`, `password_reset.html`, `welcome.html`, `refund_initiated.html`) following the same pattern with their respective context variables as defined in `tasks.py`.

---

### Component 9 — Running the ARQ Worker

The ARQ worker is a **separate process** from your FastAPI app. Run it alongside your app on the VPS.

```bash
# Run the worker
arq app.emails.queue.WorkerSettings

# In production, run via systemd. Create /etc/systemd/system/arq-email-worker.service:
```

```ini
[Unit]
Description=ARQ Email Worker
After=network.target redis.service

[Service]
User=www-data
WorkingDirectory=/path/to/your/project
ExecStart=/path/to/venv/bin/arq app.emails.queue.WorkerSettings
Restart=always
RestartSec=5
EnvironmentFile=/path/to/your/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable arq-email-worker
sudo systemctl start arq-email-worker
sudo systemctl status arq-email-worker
```

---

## AWS Setup Checklist (Manual Steps)

These cannot be automated — do them in the AWS console:

- [ ] Go to SES → Verified Identities → Create Identity → Domain → add your domain
- [ ] Add all DNS records SES gives you (3x DKIM CNAMEs, MX, SPF TXT)
- [ ] Go to SES → SMTP Settings → Create SMTP Credentials → save the username/password
- [ ] Go to SES → Account Dashboard → Request Production Access (gets you out of sandbox)
- [ ] Create SNS topic: SNS → Create Topic → Standard → name `ses-notifications`
- [ ] Go to SES → Verified Identity → your domain → Notifications → set Bounce + Complaint → your SNS topic
- [ ] Deploy your app with the `/webhooks/ses-notifications` endpoint live
- [ ] Go to SNS → your topic → Create Subscription → Protocol: HTTPS → URL: `https://yourdomain.com/webhooks/ses-notifications`
- [ ] SNS will hit your endpoint automatically to confirm — check your app logs to verify

---

## Implementation Order

Do these in sequence. Each step depends on the previous.

1. Postfix install + config on VPS — verify with a test mail before touching Python
2. Install Python dependencies
3. Implement `mailer.py`
4. Implement `tasks.py`
5. Implement `queue.py`
6. Write all 7 Jinja2 templates
7. Implement `webhooks.py` and register the router
8. Implement `mark_email_bounced` and `mark_email_unsubscribed` in your DB layer
9. Wire `queue_*` calls into existing routers (orders, auth, etc.)
10. Set up systemd service for ARQ worker
11. Do the AWS console steps above
12. End-to-end test: place an order, confirm email arrives

---

## Constraints & Rules

- **Never call `send_email` directly from a router.** Always go through `queue_*` helpers.
- **Never pass ORM model objects into queue jobs.** ARQ serializes args to JSON. Pass strings, ints, dicts only.
- **Never put SES credentials in Python code or `.env`.** They live in `/etc/postfix/sasl_passwd` only.
- **Every email type must have its own task function in `tasks.py` and its own template.** No generic "send any template" god function.
- **`mark_email_bounced` must prevent future sends.** Before sending any email, check that the address is not in the bounced/unsubscribed list.
