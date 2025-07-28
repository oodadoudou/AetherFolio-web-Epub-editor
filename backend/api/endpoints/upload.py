# Upload endpoint
# Handles EPUB file upload and session creation

from fastapi import APIRouter, UploadFile, File
from typing import Dict, Any

router = APIRouter(prefix="/upload", tags=["upload"])

# TODO: Implement upload endpoint
# @router.post("/epub")
# async def upload_epub(file: UploadFile = File(...)) -> Dict[str, Any]:
#     pass