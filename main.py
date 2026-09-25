import os
import glob
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

os.makedirs("output", exist_ok=True)
app.mount("/output", StaticFiles(directory="output"), name="output")

class ProcessRequest(BaseModel):
    url: str

@app.get("/")
def home():
    return {"status": "ok", "message": "Karaoke Backend is running"}

@app.post("/process")
async def process_video(req: ProcessRequest):
    url = req.url
    if not url:
        raise HTTPException(status_code=400, detail="Missing URL")
    
    for f in glob.glob("output/*"):
        try:
            os.remove(f)
        except Exception:
            pass

    # הגדרות מתקדמות לעקיפת חסימת 403 ב-YouTube
    out_template = "output/song.%(ext)s"
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'nocheckcertificate': True,
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube Download Error: {str(e)}")

    try:
        separator = Separator('spleeter:2stems')
        separator.separate_to_file('output/song.mp3', 'output/')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spleeter Separation Error: {str(e)}")

    return {
        "status": "success",
        "accompaniment": "/output/song/accompaniment.mp3",
        "vocals": "/output/song/vocals.mp3"
    }
