import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from dotenv import load_dotenv

from app.db import is_email_suppressed

load_dotenv()

TEMPLATES_DIR = Path(__file__).parent / "templates"

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@yourdomain.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Your Store")
MAIL_HOST = os.getenv("MAIL_HOST", "127.0.0.1")
MAIL_PORT = int(os.getenv("MAIL_PORT", "25"))


def render_template(template_name: str, context: dict[str, Any]) -> str:
    template = jinja_env.get_template(template_name)
    return template.render(**context)


async def send_email(to: str, subject: str, template_name: str, context: dict[str, Any]) -> None:
    if await is_email_suppressed(to):
        return

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
        start_tls=False,
    )
