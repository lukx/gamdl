# natyra leech - Configuration Guide

Configuration for `natyra leech` is managed natively via **Environment Variables** or a **`.env`** file. All variables must be prefixed with `NATYRA_`.

This document describes each configuration option and valid choices for those that behave like enums.

---

## General & Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `NATYRA_API_USERNAME` | *None* | HTTP Basic Auth Username. Leave empty to disable authentication. |
| `NATYRA_API_PASSWORD` | *None* | HTTP Basic Auth Password. |
| `NATYRA_COOKIES_PATH` | `./cookies.txt` | Path to your Apple Music Netscape cookies file. Required for authentication with Apple servers. |
| `NATYRA_OUTPUT_PATH` | `./AppleMusic` | Default directory for completed media downloads. |
| `NATYRA_AUDIOBOOKS_OUTPUT_PATH` | *None* | Override directory specifically for `audiobook` jobs. Falls back to `OUTPUT_PATH` if unset. |
| `NATYRA_MUSIC_VIDEOS_OUTPUT_PATH`| *None* | Override directory specifically for `music-video` jobs. Falls back to `OUTPUT_PATH` if unset. |
| `NATYRA_PODCASTS_OUTPUT_PATH` | *None* | Override directory specifically for `podcast` jobs. Falls back to `OUTPUT_PATH` if unset. |
| `NATYRA_TEMP_PATH` | `/tmp` | Directory for staging remuxes, encrypted streams, and intermediate files. |
| `NATYRA_JOBS_PATH` | `./jobs` | Directory to save the flat-file JSON job tracking files. |
| `NATYRA_LOG_LEVEL` | `INFO` | Logging verbosity. Options: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |

---

## Download Execution

| Variable | Default | Description |
|----------|---------|-------------|
| `NATYRA_DOWNLOAD_MODE` | `ytdlp` / `nm3u8dlre` | Mode used to download streaming media segments. |
| `NATYRA_USE_WRAPPER` | `false` | Whether to use the experimental proxy wrapper to bypass DRM on ALAC and other restricted formats. |
| `NATYRA_WRAPPER_ACCOUNT_URL` | `http://127.0.0.1:30020` | URL for the experimental proxy wrapper API. |

### Download Modes Supported:
- `ytdlp` — The default Python-native downloader.
- `nm3u8dlre` — Highly recommended and much faster downloader (uses `N_m3u8DL-RE` binary). Defaults to this automatically if using the official Docker image.

---

## Song Options

| Variable | Default | Description |
|----------|---------|-------------|
| `NATYRA_SONG_CODEC_PRIORITY` | `aac-legacy` | Comma-separated list of codecs to attempt downloading, in order of priority. |
| `NATYRA_REMUX_TO_MP3` | `false` | If `true`, the downloaded AAC files will be automatically converted to MP3. |
| `NATYRA_MP3_BITRATE` | `mid` | Target bitrate quality if `REMUX_TO_MP3` is enabled. |
| `NATYRA_SYNCED_LYRICS_FORMAT` | `lrc` | Format for synced lyrics sidecar files. |
| `NATYRA_NO_SYNCED_LYRICS` | `false` | If `true`, do not download synced lyrics at all. |
| `NATYRA_SYNCED_LYRICS_ONLY` | `false` | If `true`, only download lyrics and skip downloading the actual audio track. |

### Song Codec Priorities (`NATYRA_SONG_CODEC_PRIORITY`):
**Stable (DRM-Free natively):**
- `aac-legacy` - AAC 256kbps 44.1kHz (Recommended)
- `aac-he-legacy` - AAC-HE 64kbps 44.1kHz

**Experimental (May require `NATYRA_USE_WRAPPER`):**
- `aac`, `aac-he`, `aac-binaural`, `aac-downmix`, `aac-he-binaural`, `aac-he-downmix`
- `atmos` - Dolby Atmos 768kbps
- `ac3` - AC3 640kbps
- `alac` - ALAC up to 24-bit/192kHz

### MP3 Bitrates (`NATYRA_MP3_BITRATE`):
- `low` - 128 kbps
- `mid` - 160 kbps *(Default)*
- `high` - 192 kbps
- `best` - 320 kbps

### Synced Lyrics Formats (`NATYRA_SYNCED_LYRICS_FORMAT`):
- `lrc` - Standard LRC lyrics format. *(Default)*
- `srt` - SubRip subtitle format (highly accurate timing).
- `ttml` - Native Apple Music XML format (not compatible with most offline media players).

---

## Video Options (Music & Post Videos)

| Variable | Default | Description |
|----------|---------|-------------|
| `NATYRA_MUSIC_VIDEO_CODEC_PRIORITY`| `h264,h265` | Comma-separated list of video codecs to prioritize. |
| `NATYRA_MUSIC_VIDEO_RESOLUTION` | `1080p` | Maximum resolution to target for music videos. |
| `NATYRA_MUSIC_VIDEO_REMUX_MODE` | `ffmpeg` | Binary to use for remuxing video streams. |
| `NATYRA_MUSIC_VIDEO_REMUX_FORMAT`| `m4v` | Container format for downloaded videos. |
| `NATYRA_UPLOADED_VIDEO_QUALITY` | `best` | Quality for Artist uploaded/post videos. |

### Music Video Codecs (`NATYRA_MUSIC_VIDEO_CODEC_PRIORITY`):
- `h264` - Broadly compatible AVC
- `h265` - High efficiency HEVC

### Music Video Resolutions (`NATYRA_MUSIC_VIDEO_RESOLUTION`):
- For H.264: `240p`, `360p`, `480p`, `540p`, `720p`, `1080p`
- For H.265 only: `1440p`, `2160p`

### Video Remux Modes (`NATYRA_MUSIC_VIDEO_REMUX_MODE`):
- `ffmpeg` - Standard ffmpeg remuxing *(Default)*
- `mp4box` - Alternative remuxing that preserves native closed-caption tracks in music videos.

### Video Remux Formats (`NATYRA_MUSIC_VIDEO_REMUX_FORMAT`):
- `m4v` *(Default)*
- `mp4`

---

## Metadata & Templating

| Variable | Default | Description |
|----------|---------|-------------|
| `NATYRA_COVER_FORMAT` | `jpg` | Format for embedded and sidecar cover art. |
| `NATYRA_COVER_SIZE` | `1200` | Resolution (width/height in pixels) of the cover art. |
| `NATYRA_SAVE_COVER` | `false` | Save the cover art as an independent `cover.jpg` file in the folder. |

### Cover Formats (`NATYRA_COVER_FORMAT`):
- `jpg` *(Default)*
- `png`
- `raw` - Raw format provided by the upstream server (Note: You MUST enable `NATYRA_SAVE_COVER=true` as raw covers cannot be embedded directly into audio files).

### Tagging Exclusions (`NATYRA_EXCLUDE_TAGS`):
You can provide a comma-separated list of tags to strip from the final media file.
*Available tags:* `album`, `album_artist`, `album_id`, `artist`, `artist_id`, `composer`, `composer_id`, `date`, `disc`, `disc_total`, `media_type`, `playlist_artist`, `playlist_id`, `playlist_title`, `playlist_track`, `title`, `title_id`, `track`, `track_total`, `album_sort`, `artist_sort`, `composer_sort`, `title_sort`, `comment`, `compilation`, `copyright`, `cover`, `gapless`, `genre`, `genre_id`, `lyrics`, `rating`, `storefront`, `xid`, `all` (Special: strips absolutely all metadata).
