from pathlib import Path

from ..interface.enums import MusicVideoCodec, MusicVideoResolution
from ..interface.interface_music_video import AppleMusicMusicVideoInterface
from ..interface.types import DecryptionKeyAv
from .downloader_base import AppleMusicBaseDownloader
from .enums import RemuxFormatMusicVideo, RemuxMode
from .types import DownloadItem


class AppleMusicMusicVideoDownloader(AppleMusicBaseDownloader):
    def __init__(
        self,
        base_downloader: AppleMusicBaseDownloader,
        interface: AppleMusicMusicVideoInterface,
        codec_priority: list[MusicVideoCodec] = [
            MusicVideoCodec.H264,
            MusicVideoCodec.H265,
        ],
        remux_format: RemuxFormatMusicVideo = RemuxFormatMusicVideo.M4V,
        resolution: MusicVideoResolution = MusicVideoResolution.R1080P,
    ):
        self.__dict__.update(base_downloader.__dict__)
        self.interface = interface
        self.codec_priority = codec_priority
        self.remux_format = remux_format
        self.resolution = resolution

    async def stage(
        self,
        encrypted_path_video: str,
        encrypted_path_audio: str,
        decrypted_path_video: str,
        decrypted_path_audio: str,
        staged_path: str,
        decryption_key: DecryptionKeyAv,
    ):
        await self.decryptor.decrypt_mp4decrypt(
            encrypted_path_video,
            decrypted_path_video,
            decryption_key.video_track.key,
            legacy=True,
        )
        await self.decryptor.decrypt_mp4decrypt(
            encrypted_path_audio,
            decrypted_path_audio,
            decryption_key.audio_track.key,
            legacy=True,
        )

        if self.remux_mode == RemuxMode.MP4BOX:
            await self.remuxer.remux_mp4box(
                [decrypted_path_audio, decrypted_path_video],
                staged_path,
            )
        else:
            await self.remuxer.remux_ffmpeg(
                [decrypted_path_video, decrypted_path_audio],
                staged_path,
                copy_subtitles=True,
            )

    async def get_download_item(
        self,
        music_video_metadata: dict,
        playlist_metadata: dict = None,
    ) -> DownloadItem:
        download_item = DownloadItem()

        download_item.media_metadata = music_video_metadata
        download_item.playlist_metadata = playlist_metadata

        music_video_id = self.interface.get_media_id_of_library_media(
            music_video_metadata,
        )

        itunes_page_metadata = await self.interface.get_itunes_page_metadata(
            music_video_metadata,
        )
        download_item.media_tags = await self.interface.get_tags(
            music_video_metadata,
            itunes_page_metadata,
        )

        if playlist_metadata:
            download_item.playlist_tags = self.naming.get_playlist_tags(
                playlist_metadata,
                music_video_metadata,
            )
            download_item.playlist_file_path = str(self.naming.get_playlist_file_path(
                download_item.playlist_tags,
            ))

        download_item.stream_info = await self.interface.get_stream_info(
            music_video_metadata,
            itunes_page_metadata,
            self.codec_priority,
            self.resolution,
        )

        download_item.decryption_key = await self.interface.get_decryption_key(
            download_item.stream_info,
            self.cdm,
        )

        download_item.random_uuid = self.get_random_uuid()
        staged_extension = (
            "."
            + (
                "mp4"
                if self.remux_format == RemuxFormatMusicVideo.MP4
                else download_item.stream_info.file_format.value
            )
        )
        download_item.staged_path = str(self.naming.get_temp_path(
            music_video_id,
            download_item.random_uuid,
            "staged",
            staged_extension,
        ))
        download_item.final_path = str(self.naming.get_final_path(
            download_item.media_tags,
            Path(download_item.staged_path).suffix,
            download_item.playlist_tags,
        ))

        download_item.cover_url_template = self.interface.get_cover_url_template(
            music_video_metadata,
            self.cover_format,
        )
        download_item.cover_url = self.interface.get_cover_url(
            download_item.cover_url_template,
            self.cover_size,
            self.cover_format,
        )

        cover_file_extension = await self.interface.get_cover_file_extension(
            download_item.cover_url,
            self.cover_format,
        )
        if cover_file_extension:
            # Music videos often save cover as the same name as video but with image extension
            download_item.cover_path = str(Path(download_item.final_path).with_suffix(cover_file_extension))

        return download_item

    async def download(
        self,
        download_item: DownloadItem,
    ) -> None:
        encrypted_path_video = str(self.naming.get_temp_path(
            download_item.media_metadata["id"],
            download_item.random_uuid,
            "encrypted_video",
            ".mp4",
        ))
        encrypted_path_audio = str(self.naming.get_temp_path(
            download_item.media_metadata["id"],
            download_item.random_uuid,
            "encrypted_audio",
            ".m4a",
        ))

        await self.streamer.download(
            download_item.stream_info.video_track.stream_url,
            Path(encrypted_path_video),
        )
        await self.streamer.download(
            download_item.stream_info.audio_track.stream_url,
            Path(encrypted_path_audio),
        )

        decrypted_path_video = str(self.naming.get_temp_path(
            download_item.media_metadata["id"],
            download_item.random_uuid,
            "decrypted_video",
            ".mp4",
        ))
        decrypted_path_audio = str(self.naming.get_temp_path(
            download_item.media_metadata["id"],
            download_item.random_uuid,
            "decrypted_audio",
            ".m4a",
        ))

        await self.stage(
            encrypted_path_video,
            encrypted_path_audio,
            decrypted_path_video,
            decrypted_path_audio,
            download_item.staged_path,
            download_item.decryption_key,
        )

        cover_bytes = await self.interface.get_cover_bytes(download_item.cover_url)
        await self.apply_tags(
            Path(download_item.staged_path),
            download_item.media_tags,
            cover_bytes,
        )
