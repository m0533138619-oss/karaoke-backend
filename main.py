import os
import shutil
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from spleeter.separator import Separator

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_OUTPUT_DIR = "output"
os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=BASE_OUTPUT_DIR), name="output")

@app.get("/")
def home():
    return {"status": "ok", "message": "Karaoke Backend File Receiver is live"}

@app.post("/process-file")
async def process_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing file")

    # יצירת תיקייה ייחודית לקובץ
    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(BASE_OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    input_path = os.path.join(job_dir, "input.mp3")

    # שמירת הקובץ שהתקבל מהלקוח
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"File save error: {str(e)}")

    # הפרדת קולות ב-Spleeter
    try:
        separator = Separator('spleeter:2stems')
        separator.separate_to_file(input_path, job_dir)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Separation Error: {str(e)}")

    return {
        "status": "success",
        "accompaniment": f"/output/{job_id}/input/accompaniment.mp3",
        "vocals": f"/output/{job_id}/input/vocals.mp3"
    }
