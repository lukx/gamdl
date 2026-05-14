# natyra leech

A **headless HTTP API Server** for queueing and managing Apple Music song, music video, and post video downloads in the background.

---

## ✨ Features

- **Asynchronous API** - Fire-and-forget download queueing via simple HTTP requests.
- **Granular Status Tracking** - Track overall job state and individual track progress in real-time.
- **High-Quality Songs** - Download songs in AAC 256kbps and other codecs, or remux to MP3.
- **Rich Metadata** - Automatic tagging with comprehensive metadata and synced lyrics.
- **Stateless & Database-free** - Relies on simple flat-file JSON state persistence.

## 📋 Prerequisites

**Required:**
- **Apple Music Cookies** - Export your browser cookies in Netscape format (`cookies.txt`) while logged in with an active subscription.
- **Docker** or **Python 3.10+**.

---

## 🐳 Running via Docker (Recommended)

Running natyra leech via Docker is the intended way, as it comes pre-installed with all necessary external binaries (`ffmpeg`, `mp4decrypt`, `MP4Box`, `N_m3u8DL-RE`).

### Using `docker-compose.yml`

This is the easiest way to configure environment variables, auth, and mounts.

```yaml
version: '3.8'

services:
  natyra:
    image: ghcr.io/lukx/natyra:latest
    container_name: NATYRA_server
    ports:
      - "8000:8000"
    volumes:
      - ./cookies.txt:/app/cookies.txt:ro
      - ./AppleMusic:/app/AppleMusic      # Final Output Directory
      - ./jobs:/app/jobs                  # Flat-file job states
    environment:
      # Optional: Enable Basic Auth
      - NATYRA_API_USERNAME=admin
      - NATYRA_API_PASSWORD=secret
      # Standard settings
      - NATYRA_OUTPUT_PATH=/app/AppleMusic
      - NATYRA_JOBS_PATH=/app/jobs
      - NATYRA_TEMP_PATH=/tmp
      - NATYRA_REMUX_TO_MP3=false
```

Start the server:
```bash
docker-compose up -d
```

---

## 💻 Running Natively via `uv`

If you prefer to run the API server natively without Docker, follow these steps:

1. **Install dependencies using `uv`:**
   ```bash
   uv sync
   ```

2. **Set up your environment:**
   Create a `.env` file in the root directory mapping to your paths and `cookies.txt`:
   ```ini
   NATYRA_COOKIES_PATH=./cookies.txt
   NATYRA_OUTPUT_PATH=./AppleMusic
   NATYRA_TEMP_PATH=/tmp
   NATYRA_API_USERNAME=admin
   NATYRA_API_PASSWORD=secret
   ```

3. **Start the server:**
   ```bash
   uv run python -m natyra leech
   ```
   *The server will start locally on `http://0.0.0.0:8000`.*

---

## ⚙️ Configuration

Configuration is managed natively via **Environment Variables** or a **`.env`** file via Pydantic. 
All variables must be prefixed with `NATYRA_`.

| Variable | Default | Description |
|----------|---------|-------------|
| `NATYRA_API_USERNAME` | *None* | HTTP Basic Auth Username (leave empty to disable auth). |
| `NATYRA_API_PASSWORD` | *None* | HTTP Basic Auth Password. |
| `NATYRA_COOKIES_PATH` | `./cookies.txt` | Path to Apple Music Netscape cookies file. |
| `NATYRA_OUTPUT_PATH` | `./AppleMusic` | Default directory for completed media downloads. |
| `NATYRA_AUDIOBOOKS_OUTPUT_PATH` | *None* | Override directory specifically for 'audiobook' jobs. |
| `NATYRA_MUSIC_VIDEOS_OUTPUT_PATH`| *None* | Override directory specifically for 'music-video' jobs. |
| `NATYRA_PODCASTS_OUTPUT_PATH` | *None* | Override directory specifically for 'podcast' jobs. |
| `NATYRA_TEMP_PATH` | `/tmp` | Directory for staging remuxes and encrypted streams. |
| `NATYRA_JOBS_PATH` | `./jobs` | Directory to save flat-file JSON job tracking files. |
| `NATYRA_REMUX_TO_MP3` | `false` | Convert AAC downloads to high-quality MP3. |
| `NATYRA_DOWNLOAD_MODE` | `ytdlp` (in uv) or `nm3u8dlre` (in docker) | Mode to download segments (e.g. `nm3u8dlre`). |
| `NATYRA_SONG_CODEC_PRIORITY`| `aac-legacy` | Comma-separated list of codecs. |

---

## 🌐 API Endpoints

Once the server is running, you can interact with it via its HTTP REST endpoints.

### 1. `POST /download`
Enqueue an Apple Music URL (Song, Album, Playlist, or Artist) for background download.

*Note: The `type` property is optional, but if you want the downloaded files to be routed to specific directories (e.g., `NATYRA_AUDIOBOOKS_OUTPUT_PATH`), you must explicitly pass `"type": "audiobook"`, `"type": "music-video"`, or `"type": "podcast"`.*

**Request:**
```bash
curl -X POST http://localhost:8000/download \
  -u admin:secret \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://music.apple.com/de/album/whenever-you-need-somebody-2022-remaster/1624945511",
    "type": "audiobook"
  }'
```

**Response:**
```json
{
  "job_id": "c9dd056b-2785-408e-b575-2913f341cc3b",
  "status": "enqueued",
  "url": "https://music.apple.com/de/album/whenever-you-need-somebody-2022-remaster/1624945511"
}
```

### 2. `GET /jobs/{job_id}`
Get real-time tracking for a specific background job, including individual track states (`pending`, `running`, `done`, `skipped`, `failed`).

**Request:**
```bash
curl -X GET http://localhost:8000/jobs/c9dd056b-2785-408e-b575-2913f341cc3b \
  -u admin:secret
```

**Response:**
```json
{
  "job_id": "c9dd056b-2785-408e-b575-2913f341cc3b",
  "url": "https://music.apple.com/...",
  "type": "album",
  "status": "running",
  "enqueued_at": "2026-05-14T19:20:00+00:00",
  "started_at": "2026-05-14T19:20:05+00:00",
  "finished_at": null,
  "tracks": {
    "Never Gonna Give You Up": "done",
    "Whenever You Need Somebody": "skipped",
    "Together Forever": "running"
  }
}
```

### 3. `GET /jobs`
Fetch a list of all known background jobs and their high-level statuses.

**Request:**
```bash
curl -X GET http://localhost:8000/jobs \
  -u admin:secret
```

**Response:**
```json
[
  {
    "job_id": "fba0471b-0396-4428-a23e-4b8b7a2a2cf6",
    "url": "https://music.apple.com/...",
    "status": "done"
  },
  {
    "job_id": "c9dd056b-2785-408e-b575-2913f341cc3b",
    "url": "https://music.apple.com/...",
    "status": "running"
  }
]
```

## 📄 License
MIT License - see [LICENSE](LICENSE) file for details.

---

## 🍏 Why Natyra?

You might be wondering, why "natyra leech"? 
Natyra is an incredibly delicious, organic-only apple variety known for its crisp, juicy bite and balanced sweet-tart flavor. By choosing a name that celebrates one of nature's finest fruits, we aim to bring that same refreshing, robust quality to this software!

---

## 👏 Credits

This project is a massive, API-first refactoring of the original **gamdl** project.
All credit for the underlying decryption logic, Apple Music API interactions, and heavy lifting goes to the original authors. 

Check out the original project here: [https://github.com/glomatico/gamdl](https://github.com/glomatico/gamdl)
