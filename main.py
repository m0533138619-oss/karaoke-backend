import os
import shutil
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import yt_dlp
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

class ProcessRequest(BaseModel):
    url: str

@app.get("/")
def home():
    return {"status": "ok", "message": "Karaoke Backend is live"}

@app.post("/process")
async def process_video(req: ProcessRequest):
    url = req.url
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")

    # אם המשתמש הדביק קישור של Radio/Playlist, ניקח רק את הווידאו הבודד
    if "list=" in url or "start_radio=" in url:
        url = url.split("&list=")[0].split("?list=")[0]

    job_id = str(uuid.uuid4())[:8]
    job_dir = os.path.join(BASE_OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    input_audio_path = os.path.join(job_dir, "input")

    ydl_opts = {
        'format': 'ba/b',
        'outtmpl': f"{input_audio_path}.%(ext)s",
        'noplaylist': True,  # מכריח הורדה של שיר בודד בלבד
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'android', 'ios'],
                'skip': ['hls', 'dash']
            }
        },
        'match_filter': yt_dlp.utils.match_filter_func('duration <= 600'),
        'nocheckcertificate': True,
        'quiet': True,
        'no_warnings': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500, 
            detail=f"YouTube Error: {str(e)}"
        )

    downloaded_file = f"{input_audio_path}.mp3"
    if not os.path.exists(downloaded_file):
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Extraction failed")

    try:
        separator = Separator('spleeter:2stems')
        separator.separate_to_file(downloaded_file, job_dir)
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Spleeter Error: {str(e)}")

    return {
        "status": "success",
        "accompaniment": f"/output/{job_id}/input/accompaniment.mp3",
        "vocals": f"/output/{job_id}/input/vocals.mp3"
    }
