import asyncio
from pathlib import Path
from yt_dlp import YoutubeDL
from ..utils import async_subprocess
from ..downloader.enums import DownloadMode


class StreamDownloader:
    def __init__(
        self,
        download_mode: DownloadMode,
        ffmpeg_path: str,
        nm3u8dlre_path: str,
        silent: bool = False,
    ):
        self.download_mode = download_mode
        self.ffmpeg_path = ffmpeg_path
        self.nm3u8dlre_path = nm3u8dlre_path
        self.silent = silent

    async def download(self, stream_url: str, download_path: Path):
        if self.download_mode == DownloadMode.YTDLP:
            await self.download_ytdlp(stream_url, download_path)
        elif self.download_mode == DownloadMode.NM3U8DLRE:
            await self.download_nm3u8dlre(stream_url, download_path)

    async def download_ytdlp(self, stream_url: str, download_path: Path) -> None:
        await asyncio.to_thread(
            self._download_ytdlp,
            stream_url,
            str(download_path),
        )

    def _download_ytdlp(self, stream_url: str, download_path: str) -> None:
        with YoutubeDL(
            {
                "quiet": True,
                "no_warnings": True,
                "outtmpl": download_path,
                "allow_unplayable_formats": True,
                "overwrites": True,
                "fixup": "never",
                "noprogress": self.silent,
                "allowed_extractors": ["generic"],
            }
        ) as ydl:
            ydl.download(stream_url)

    async def download_nm3u8dlre(self, stream_url: str, download_path: Path):
        download_path.parent.mkdir(parents=True, exist_ok=True)
        await async_subprocess(
            self.nm3u8dlre_path,
            stream_url,
            "--binary-merge",
            "--no-log",
            "--log-level",
            "off",
            "--ffmpeg-binary-path",
            self.ffmpeg_path,
            "--save-name",
            download_path.stem,
            "--save-dir",
            str(download_path.parent),
            "--tmp-dir",
            str(download_path.parent),
            silent=self.silent,
        )
