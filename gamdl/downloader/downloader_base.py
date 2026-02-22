import uuid
import shutil
from pathlib import Path
from typing import Union, List
from pywidevine import Cdm, Device

from ..interface.enums import CoverFormat
from ..metadata.tagger_mp3 import MP3Tagger
from ..metadata.tagger_mp4 import MP4Tagger
from ..interface.types import MediaTags
from ..naming.provider import NamingProvider
from ..processors.stream_downloader import StreamDownloader
from ..processors.decryptor import Decryptor
from ..processors.remuxer import Remuxer
from .enums import DownloadMode, RemuxMode
from .hardcoded_wvd import HARDCODED_WVD


class AppleMusicBaseDownloader:
    def __init__(
        self,
        output_path: str = "./AppleMusic",
        temp_path: str = ".",
        wvd_path: str = None,
        overwrite: bool = False,
        save_cover: bool = False,
        save_playlist: bool = False,
        nm3u8dlre_path: str = "N_m3u8DL-RE",
        mp4decrypt_path: str = "mp4decrypt",
        ffmpeg_path: str = "ffmpeg",
        mp4box_path: str = "MP4Box",
        amdecrypt_path: str = "amdecrypt",
        use_wrapper: bool = False,
        wrapper_decrypt_ip: str = "127.0.0.1:10020",
        download_mode: DownloadMode = DownloadMode.YTDLP,
        remux_mode: RemuxMode = RemuxMode.FFMPEG,
        cover_format: CoverFormat = CoverFormat.JPG,
        album_folder_template: str = "{album_artist}/{album}",
        compilation_folder_template: str = "Compilations/{album}",
        no_album_folder_template: str = "{artist}/Unknown Album",
        single_disc_file_template: str = "{track:02d} {title}",
        multi_disc_file_template: str = "{disc}-{track:02d} {title}",
        no_album_file_template: str = "{title}",
        playlist_file_template: str = "Playlists/{playlist_artist}/{playlist_title}",
        date_tag_template: str = "%Y-%m-%dT%H:%M:%SZ",
        exclude_tags: list[str] = None,
        cover_size: int = 1200,
        truncate: int = None,
        silent: bool = False,
        remux_to_mp3: bool = False,
        mp3_bitrate: str = "mid",
    ):
        self.output_path = output_path
        self.temp_path = temp_path
        self.wvd_path = wvd_path
        self.overwrite = overwrite
        self.save_cover = save_cover
        self.save_playlist = save_playlist
        self.nm3u8dlre_path = nm3u8dlre_path
        self.mp4decrypt_path = mp4decrypt_path
        self.ffmpeg_path = ffmpeg_path
        self.mp4box_path = mp4box_path
        self.amdecrypt_path = amdecrypt_path
        self.use_wrapper = use_wrapper
        self.wrapper_decrypt_ip = wrapper_decrypt_ip
        self.download_mode = download_mode
        self.remux_mode = remux_mode
        self.cover_format = cover_format
        self.album_folder_template = album_folder_template
        self.compilation_folder_template = compilation_folder_template
        self.no_album_folder_template = no_album_folder_template
        self.single_disc_file_template = single_disc_file_template
        self.multi_disc_file_template = multi_disc_file_template
        self.no_album_file_template = no_album_file_template
        self.playlist_file_template = playlist_file_template
        self.date_tag_template = date_tag_template
        self.exclude_tags = exclude_tags or []
        self.cover_size = cover_size
        self.truncate = truncate
        self.silent = silent
        self.remux_to_mp3 = remux_to_mp3
        self.mp3_bitrate = mp3_bitrate
        
        self.initialize()

    def initialize(self):
        self._initialize_binary_paths()
        self._initialize_cdm()
        self._initialize_services()

    def _initialize_binary_paths(self):
        self.full_nm3u8dlre_path = shutil.which(self.nm3u8dlre_path)
        self.full_mp4decrypt_path = shutil.which(self.mp4decrypt_path)
        self.full_ffmpeg_path = shutil.which(self.ffmpeg_path)
        self.full_mp4box_path = shutil.which(self.mp4box_path)
        self.full_amdecrypt_path = shutil.which(self.amdecrypt_path)

    def _initialize_cdm(self):
        if self.wvd_path:
            self.cdm = Cdm.from_device(Device.load(self.wvd_path))
        else:
            self.cdm = Cdm.from_device(Device.loads(HARDCODED_WVD))
        self.cdm.MAX_NUM_OF_SESSIONS = float("inf")

    def _initialize_services(self):
        self.naming = NamingProvider(
            output_path=self.output_path,
            temp_path=self.temp_path,
            album_folder_template=self.album_folder_template,
            compilation_folder_template=self.compilation_folder_template,
            no_album_folder_template=self.no_album_folder_template,
            single_disc_file_template=self.single_disc_file_template,
            multi_disc_file_template=self.multi_disc_file_template,
            no_album_file_template=self.no_album_file_template,
            playlist_file_template=self.playlist_file_template,
            truncate=self.truncate,
        )
        self.streamer = StreamDownloader(
            download_mode=self.download_mode,
            ffmpeg_path=self.full_ffmpeg_path,
            nm3u8dlre_path=self.full_nm3u8dlre_path,
            silent=self.silent,
        )
        self.decryptor = Decryptor(
            mp4decrypt_path=self.full_mp4decrypt_path,
            amdecrypt_path=self.full_amdecrypt_path,
            silent=self.silent,
        )
        self.remuxer = Remuxer(
            ffmpeg_path=self.full_ffmpeg_path,
            mp4box_path=self.full_mp4box_path,
            silent=self.silent,
        )

    async def apply_tags(
        self,
        media_path: Path,
        tags: MediaTags,
        cover_bytes: bytes | None,
        extra_tags: dict | None = None,
    ):
        skip_tagging = "all" in self.exclude_tags
        if media_path.suffix == ".mp3":
            MP3Tagger.apply(
                media_path,
                tags.as_mp4_tags(self.date_tag_template),
                cover_bytes,
                skip_tagging,
            )
        else:
            MP4Tagger.apply(
                media_path,
                tags.as_mp4_tags(self.date_tag_template),
                cover_bytes,
                skip_tagging,
                extra_tags,
                self.cover_format,
            )

    def get_random_uuid(self) -> str:
        return uuid.uuid4().hex[:8]

    def is_media_streamable(self, media_metadata: dict) -> bool:
        return bool(media_metadata["attributes"].get("playParams"))

    def move_to_final_path(self, stage_path: Union[str, Path], final_path: Union[str, Path]) -> None:
        stage_path = Path(stage_path)
        final_path = Path(final_path)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(stage_path), str(final_path))

    def cleanup_temp(self, folder_tag: str):
        shutil.rmtree(Path(self.temp_path) / f"gamdl_temp_{folder_tag}", ignore_errors=True)

    def write_cover_image(self, cover_bytes: bytes, cover_path: str):
        Path(cover_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cover_path).write_bytes(cover_bytes)

    def update_playlist_file(self, playlist_file_path: str, final_path: str, track_number: int):
        playlist_file_path = Path(playlist_file_path)
        playlist_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Simple M3U8 update logic
        if not playlist_file_path.exists():
            playlist_file_path.write_text("#EXTM3U\n", encoding="utf8")
            
        with open(playlist_file_path, "a", encoding="utf8") as f:
            f.write(f"{final_path}\n")
