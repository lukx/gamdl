import asyncio
import json
import logging
import uuid
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime, timezone

import secrets
from fastapi import BackgroundTasks, FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from natyra.api import AppleMusicApi, ItunesApi
from natyra.config import settings
from natyra.downloader import (
    AppleMusicBaseDownloader,
    AppleMusicDownloader,
    AppleMusicMusicVideoDownloader,
    AppleMusicSongDownloader,
    AppleMusicUploadedVideoDownloader,
)
from natyra.downloader.constants import VALID_URL_PATTERN
from natyra.downloader.exceptions import MediaFileExists
from natyra.interface import (
    AppleMusicInterface,
    AppleMusicMusicVideoInterface,
    AppleMusicSongInterface,
    AppleMusicUploadedVideoInterface,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Natyra API Server", description="Background queue for Apple Music downloads")

security = HTTPBasic(auto_error=False)

def verify_credentials(credentials: HTTPBasicCredentials | None = Depends(security)):
    if not settings.api_username or not settings.api_password:
        return True # Auth not configured, allow access
        
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic"},
        )
        
    correct_username = secrets.compare_digest(credentials.username, settings.api_username)
    correct_password = secrets.compare_digest(credentials.password, settings.api_password)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials

JOBS_DIR = Path(settings.jobs_path)
JOBS_DIR.mkdir(parents=True, exist_ok=True)

class DownloadRequest(BaseModel):
    url: str
    type: str | None = None

def write_job_state(job_id: str, state: dict):
    file_path = JOBS_DIR / f"{job_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

def read_job_state(job_id: str) -> dict | None:
    file_path = JOBS_DIR / f"{job_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

async def _init_downloader():
    if settings.use_wrapper:
        apple_music_api = await AppleMusicApi.create_from_wrapper(
            wrapper_account_url=settings.wrapper_account_url,
            language=settings.language,
        )
    else:
        apple_music_api = await AppleMusicApi.create_from_netscape_cookies(
            cookies_path=settings.cookies_path,
            language=settings.language,
        )

    itunes_api = ItunesApi(apple_music_api.storefront, apple_music_api.language)
    interface = AppleMusicInterface(apple_music_api, itunes_api)
    song_interface = AppleMusicSongInterface(interface)
    music_video_interface = AppleMusicMusicVideoInterface(interface)
    uploaded_video_interface = AppleMusicUploadedVideoInterface(interface)

    base_downloader = AppleMusicBaseDownloader(
        output_path=settings.output_path,
        temp_path=settings.temp_path,
        wvd_path=settings.wvd_path,
        overwrite=settings.overwrite,
        save_cover=settings.save_cover,
        save_playlist=settings.save_playlist,
        nm3u8dlre_path=settings.nm3u8dlre_path,
        mp4decrypt_path=settings.mp4decrypt_path,
        ffmpeg_path=settings.ffmpeg_path,
        mp4box_path=settings.mp4box_path,
        amdecrypt_path=settings.amdecrypt_path,
        use_wrapper=settings.use_wrapper,
        wrapper_decrypt_ip=settings.wrapper_decrypt_ip,
        download_mode=settings.download_mode,
        cover_format=settings.cover_format,
        album_folder_template=settings.album_folder_template,
        compilation_folder_template=settings.compilation_folder_template,
        no_album_folder_template=settings.no_album_folder_template,
        single_disc_file_template=settings.single_disc_file_template,
        multi_disc_file_template=settings.multi_disc_file_template,
        no_album_file_template=settings.no_album_file_template,
        playlist_file_template=settings.playlist_file_template,
        date_tag_template=settings.date_tag_template,
        exclude_tags=settings.exclude_tags,
        cover_size=settings.cover_size,
        truncate=settings.truncate,
        remux_to_mp3=settings.remux_to_mp3,
        mp3_bitrate=settings.mp3_bitrate,
    )
    song_downloader = AppleMusicSongDownloader(
        base_downloader=base_downloader,
        interface=song_interface,
        codec_priority=settings.song_codec_priority,
        synced_lyrics_format=settings.synced_lyrics_format,
        no_synced_lyrics=settings.no_synced_lyrics,
        synced_lyrics_only=settings.synced_lyrics_only,
        use_album_date=settings.use_album_date,
        fetch_extra_tags=settings.fetch_extra_tags,
        remux_mode=settings.music_video_remux_mode,
    )
    music_video_downloader = AppleMusicMusicVideoDownloader(
        base_downloader=base_downloader,
        interface=music_video_interface,
        codec_priority=settings.music_video_codec_priority,
        remux_mode=settings.music_video_remux_mode,
        remux_format=settings.music_video_remux_format,
        resolution=settings.music_video_resolution,
    )
    uploaded_video_downloader = AppleMusicUploadedVideoDownloader(
        base_downloader=base_downloader,
        interface=uploaded_video_interface,
        quality=settings.uploaded_video_quality,
    )
    downloader = AppleMusicDownloader(
        interface=interface,
        base_downloader=base_downloader,
        song_downloader=song_downloader,
        music_video_downloader=music_video_downloader,
        uploaded_video_downloader=uploaded_video_downloader,
        artist_auto_select=settings.artist_auto_select,
    )
    return downloader

async def background_download_task(job_id: str, request: DownloadRequest):
    state = read_job_state(job_id) or {
        "job_id": job_id,
        "url": request.url,
        "type": request.type,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
        "tracks": {}
    }
    state["status"] = "running"
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    state["finished_at"] = None
    write_job_state(job_id, state)

    # Allow request override of output path
    if request.type == "audiobook" and settings.audiobooks_output_path:
        settings.output_path = settings.audiobooks_output_path
    elif request.type in ["music-video", "music_video"] and settings.music_videos_output_path:
        settings.output_path = settings.music_videos_output_path
    elif request.type == "podcast" and settings.podcasts_output_path:
        settings.output_path = settings.podcasts_output_path

    try:
        downloader = await _init_downloader()
        url_info = downloader.get_url_info(request.url)
        if not url_info:
            raise ValueError("Invalid URL info parsed")

        download_queue = await downloader.get_download_queue(url_info)
        if not download_queue:
            state["status"] = "failed"
            state["error"] = "No download items found"
            return

        failed_count = 0
        success_count = 0
        skipped_count = 0

        for i, item in enumerate(download_queue, start=1):
            track_name = item.media_metadata.get("attributes", {}).get("name", f"Track {i}")
            track_id = item.media_metadata.get("id", str(i))
            
            state["tracks"][track_id] = {
                "name": track_name,
                "status": "running"
            }
            write_job_state(job_id, state)

            try:
                await downloader.download(item)
                state["tracks"][track_id]["status"] = "done"
                success_count += 1
            except MediaFileExists:
                state["tracks"][track_id]["status"] = "skipped"
                state["tracks"][track_id]["error"] = "File already exists"
                skipped_count += 1
            except Exception as e:
                state["tracks"][track_id]["status"] = "failed"
                state["tracks"][track_id]["error"] = str(e)
                failed_count += 1
            
            write_job_state(job_id, state)

        if failed_count == 0:
            state["status"] = "done"
        elif success_count == 0 and skipped_count == 0:
            state["status"] = "failed"
            state["error"] = "All tracks failed to download"
        else:
            state["status"] = "partly failed"

    except Exception as e:
        state["status"] = "failed"
        state["error"] = str(e)
    finally:
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_job_state(job_id, state)


@app.post("/download")
async def enqueue_download(request: DownloadRequest, background_tasks: BackgroundTasks, _ = Depends(verify_credentials)):
    match = VALID_URL_PATTERN.match(request.url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid or unresolvable Apple Music URL")
        
    job_id = str(uuid.uuid4())
    
    state = {
        "job_id": job_id,
        "url": request.url,
        "type": request.type,
        "status": "pending",
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "tracks": {}
    }
    write_job_state(job_id, state)
    
    background_tasks.add_task(background_download_task, job_id, request)
    return {"job_id": job_id, "status": "enqueued", "url": request.url}

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str, _ = Depends(verify_credentials)):
    """
    Story 2: Get job status by UUID.
    Provides real-time visibility on the overall job and track-level progress.
    """
    state = read_job_state(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")
    return state    
    

@app.get("/jobs")
async def list_jobs(_ = Depends(verify_credentials)):
    """
    Story 3: List all known jobs and their high-level statuses.
    Reads the flat-file storage directory to fetch the summaries.
    """
    jobs = []
    if JOBS_DIR.exists():
        for file_path in JOBS_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    job_data = json.load(f)
                    
                    # Return a high-level summary (excluding heavy track details)
                    jobs.append({
                        "job_id": job_data.get("job_id", file_path.stem),
                        "url": job_data.get("url"),
                        "type": job_data.get("type"),
                        "status": job_data.get("status", "unknown")
                    })
            except Exception as e:
                logger.error(f"Failed to read job file {file_path}: {e}")
                
    return {"jobs": jobs}

