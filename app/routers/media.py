import os
import uuid
import aiofiles
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional
from app.auth import require_admin

router = APIRouter(prefix="/api/media", tags=["Media Upload"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
VEHICLES_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "vehicles")
TRACKING_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "tracking")

os.makedirs(VEHICLES_UPLOAD_DIR, exist_ok=True)
os.makedirs(TRACKING_UPLOAD_DIR, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".avi"}

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form("vehicles"), # "vehicles" or "tracking"
    admin: dict = Depends(require_admin)
):
    """Secure endpoint to upload high-resolution images or videos."""
    original_name = file.filename or "media"
    ext = os.path.splitext(original_name)[1].lower()

    is_image = ext in ALLOWED_IMAGE_EXTENSIONS
    is_video = ext in ALLOWED_VIDEO_EXTENSIONS

    if not is_image and not is_video:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed image formats: jpg, jpeg, png, webp. Allowed videos: mp4, webm, mov."
        )

    media_type = "image" if is_image else "video"
    subfolder = VEHICLES_UPLOAD_DIR if category == "vehicles" else TRACKING_UPLOAD_DIR

    unique_filename = f"{uuid.uuid4().hex[:12]}_{original_name.replace(' ', '_')}"
    file_path = os.path.join(subfolder, unique_filename)

    async with aiofiles.open(file_path, "wb") as buffer:
        while content := await file.read(1024 * 1024): # 1MB chunks
            await buffer.write(content)

    public_url = f"/static/uploads/{category}/{unique_filename}"
    return {
        "success": True,
        "url": public_url,
        "filename": unique_filename,
        "media_type": media_type,
        "category": category
    }

@router.post("/upload-multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    category: str = Form("vehicles"),
    admin: dict = Depends(require_admin)
):
    """Upload multiple photos or videos in batch."""
    results = []
    subfolder = VEHICLES_UPLOAD_DIR if category == "vehicles" else TRACKING_UPLOAD_DIR

    for file in files:
        original_name = file.filename or "media"
        ext = os.path.splitext(original_name)[1].lower()
        is_image = ext in ALLOWED_IMAGE_EXTENSIONS
        is_video = ext in ALLOWED_VIDEO_EXTENSIONS

        if not is_image and not is_video:
            continue

        media_type = "image" if is_image else "video"
        unique_filename = f"{uuid.uuid4().hex[:12]}_{original_name.replace(' ', '_')}"
        file_path = os.path.join(subfolder, unique_filename)

        async with aiofiles.open(file_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):
                await buffer.write(content)

        public_url = f"/static/uploads/{category}/{unique_filename}"
        results.append({
            "url": public_url,
            "filename": unique_filename,
            "media_type": media_type,
            "category": category
        })

    return {"success": True, "files": results}
