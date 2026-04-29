import csv
import io

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.emails.queue import queue_bulk_announcement

router = APIRouter()


@router.post("/upload/csv")
async def upload_csv(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))

    # Normalise headers to lowercase for case-insensitive matching
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV has no headers")

    headers = [h.strip().lower() for h in reader.fieldnames]
    if "email" not in headers or "name" not in headers:
        raise HTTPException(status_code=400, detail="CSV must have 'email' and 'name' columns")

    queued = 0
    skipped = 0
    errors: list[str] = []

    for row_num, row in enumerate(reader, start=2):
        normalised = {k.strip().lower(): (v or "").strip() for k, v in row.items()}
        email = normalised.get("email", "")
        name = normalised.get("name", "")

        if not email:
            errors.append(f"row {row_num}: missing email")
            skipped += 1
            continue

        if "@" not in email or "." not in email.split("@")[-1]:
            errors.append(f"row {row_num}: invalid email '{email}'")
            skipped += 1
            continue

        username = name if name else email.split("@")[0]
        await queue_bulk_announcement(to=email, username=username)
        queued += 1

    return {"queued": queued, "skipped": skipped, "errors": errors}
