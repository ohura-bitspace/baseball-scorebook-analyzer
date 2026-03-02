import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from schemas import Scorebook
from analyzer import analyze_scorebook_image

load_dotenv()

app = FastAPI(
    title="Baseball Scorebook Analyzer",
    description="Analyzes Japanese baseball scorebook images using Claude Vision API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten for production (e.g. ["http://localhost:3000"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.post("/api/analyze", response_model=Scorebook)
async def analyze(file: UploadFile = File(...)):
    """
    Accept a scorebook image, forward to Claude Vision API, return structured JSON.
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Use JPEG, PNG, or WEBP.",
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum 20 MB.")

    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="ANTHROPIC_API_KEY is not set. Copy backend/.env.example to backend/.env and add your key.",
        )

    result = await analyze_scorebook_image(image_bytes, file.content_type)
    return result
