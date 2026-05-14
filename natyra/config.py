from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from natyra.downloader.enums import DownloadMode, RemuxMode, ArtistAutoSelect, RemuxFormatMusicVideo
from natyra.interface import CoverFormat, SongCodec, SyncedLyricsFormat, MusicVideoCodec, MusicVideoResolution, UploadedVideoQuality

class NatyraSettings(BaseSettings):
    # API & General
    api_username: str | None = None
    api_password: str | None = None
    language: str = "en-US"
    cookies_path: str = "./cookies.txt"
    output_path: str = "./AppleMusic"
    audiobooks_output_path: str | None = None
    music_videos_output_path: str | None = None
    podcasts_output_path: str | None = None
    temp_path: str = "/tmp"
    jobs_path: str = "./jobs"
    wvd_path: str | None = None
    log_level: str = "INFO"

    # Behaviors
    overwrite: bool = False
    save_cover: bool = False
    save_playlist: bool = False
    artist_auto_select: ArtistAutoSelect | None = None

    # Paths to binaries
    nm3u8dlre_path: str = "N_m3u8DL-RE"
    mp4decrypt_path: str = "mp4decrypt"
    ffmpeg_path: str = "ffmpeg"
    mp4box_path: str = "MP4Box"
    amdecrypt_path: str = "amdecrypt"

    # Wrapper
    use_wrapper: bool = False
    wrapper_account_url: str = "http://127.0.0.1:30020"
    wrapper_decrypt_ip: str = "127.0.0.1:10020"

    # Formats & Modes
    download_mode: DownloadMode = DownloadMode.YTDLP
    cover_format: CoverFormat = CoverFormat.JPG
    cover_size: int = 1200
    truncate: int | None = None
    remux_to_mp3: bool = False
    mp3_bitrate: str = "mid"

    # Song settings
    song_codec_priority: list[SongCodec] = [SongCodec.AAC_LEGACY]
    synced_lyrics_format: SyncedLyricsFormat = SyncedLyricsFormat.LRC
    no_synced_lyrics: bool = False
    synced_lyrics_only: bool = False
    use_album_date: bool = False
    fetch_extra_tags: bool = False

    # Music Video settings
    music_video_codec_priority: list[MusicVideoCodec] = [MusicVideoCodec.H264, MusicVideoCodec.H265]
    music_video_remux_mode: RemuxMode = RemuxMode.FFMPEG
    music_video_remux_format: RemuxFormatMusicVideo = RemuxFormatMusicVideo.M4V
    music_video_resolution: MusicVideoResolution = MusicVideoResolution.R1080P
    uploaded_video_quality: UploadedVideoQuality = UploadedVideoQuality.BEST

    # Templates
    album_folder_template: str = "{album_artist}/{album}"
    compilation_folder_template: str = "Compilations/{album}"
    no_album_folder_template: str = "{artist}/Unknown Album"
    single_disc_file_template: str = "{track:02d} {title}"
    multi_disc_file_template: str = "{disc}-{track:02d} {title}"
    no_album_file_template: str = "{title}"
    playlist_file_template: str = "Playlists/{playlist_artist}/{playlist_title}"
    date_tag_template: str = "%Y-%m-%dT%H:%M:%SZ"
    exclude_tags: list[str] = []

    model_config = SettingsConfigDict(
        env_prefix="NATYRA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = NatyraSettings()
