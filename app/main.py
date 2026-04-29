import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from dotenv import load_dotenv

from app.emails.queue import close_email_queue
from app.routers.csv_upload import router as csv_upload_router
from app.routers.dev_email_test import router as dev_email_test_router
from app.routers.queue_api import router as queue_api_router
from app.routers.webhooks import router as webhooks_router

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await close_email_queue()


app = FastAPI(title="Mailer Service", lifespan=lifespan)
app.include_router(webhooks_router)
app.include_router(queue_api_router)
app.include_router(csv_upload_router)

if os.getenv("ENABLE_EMAIL_TEST_ROUTES", "false").lower() == "true":
    app.include_router(dev_email_test_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
