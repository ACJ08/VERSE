from fastapi import FastAPI, UploadFile, File
from app.scene_splitter import split_into_scenes
from app.call_sheet import parse_call_sheet
from app.parser import extract_text

import os
import shutil


app = FastAPI(
    title="ContinuityAI Script Intelligence API",
    version="1.0.0"
)

# Mount the structured API router (api.py) under /api/v1
# This activates: /api/v1/health, /api/v1/analyse-script,
#                 /api/v1/analyse-scene, and all other VERSE endpoints.
from app.api import router as verse_router  # noqa: E402
app.include_router(verse_router, prefix="/api/v1")


# Upload locations
SCRIPT_UPLOAD_DIR = "uploads/scripts"
CALL_SHEET_UPLOAD_DIR = "uploads/call_sheets"


# Extracted text locations
SCRIPT_EXTRACT_DIR = "extracted/scripts"
CALL_SHEET_EXTRACT_DIR = "extracted/call_sheets"


# Create folders
for folder in [
    SCRIPT_UPLOAD_DIR,
    CALL_SHEET_UPLOAD_DIR,
    SCRIPT_EXTRACT_DIR,
    CALL_SHEET_EXTRACT_DIR
]:
    os.makedirs(folder, exist_ok=True)



@app.get("/")
def root():
    return {
        "status": "running",
        "message": "ContinuityAI Script Intelligence API"
    }



# -----------------------------
# Upload Script
# -----------------------------

@app.post("/upload-script")
async def upload_script(file: UploadFile = File(...)):

    file_path = os.path.join(
        SCRIPT_UPLOAD_DIR,
        file.filename
    )

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )


    return {
        "message": "Script uploaded successfully",
        "filename": file.filename,
        "path": file_path
    }



# -----------------------------
# Parse Script
# -----------------------------

@app.post("/parse-script")
async def parse_script(file: UploadFile = File(...)):

    file_path = os.path.join(
        SCRIPT_UPLOAD_DIR,
        file.filename
    )


    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )


    text = extract_text(file_path)


    # Save extracted text
    txt_name = file.filename + ".txt"

    extracted_path = os.path.join(
        SCRIPT_EXTRACT_DIR,
        txt_name
    )


    with open(
        extracted_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(text)


    scenes = split_into_scenes(text)


    return {
        "filename": file.filename,
        "scene_count": len(scenes),
        "extracted_text": extracted_path,
        "first_scene": scenes[0] if scenes else ""
    }




# -----------------------------
# Parse Call Sheet
# -----------------------------

@app.post("/parse-call-sheet")
async def parse_call_sheet_api(file: UploadFile = File(...)):

    file_path = os.path.join(
        CALL_SHEET_UPLOAD_DIR,
        file.filename
    )


    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )


    text = extract_text(file_path)


    # Save extracted call sheet text

    txt_name = file.filename + ".txt"

    extracted_path = os.path.join(
        CALL_SHEET_EXTRACT_DIR,
        txt_name
    )


    with open(
        extracted_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(text)


    data = parse_call_sheet(text)


    return {
        "filename": file.filename,
        "uploaded_path": file_path,
        "extracted_path": extracted_path,
        "call_sheet": data
    }
    