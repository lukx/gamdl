from pathlib import Path

from ..interface.enums import SongCodec, SyncedLyricsFormat
from ..interface.interface_song import AppleMusicSongInterface
from ..interface.types import DecryptionKeyAv
from .downloader_base import AppleMusicBaseDownloader
from .enums import RemuxMode
from .types import DownloadItem


class AppleMusicSongDownloader(AppleMusicBaseDownloader):
    def __init__(
        self,
        base_downloader: AppleMusicBaseDownloader,
        interface: AppleMusicSongInterface,
        codec: SongCodec = SongCodec.AAC_LEGACY,
        synced_lyrics_format: SyncedLyricsFormat = SyncedLyricsFormat.LRC,
        no_synced_lyrics: bool = False,
        synced_lyrics_only: bool = False,
        use_album_date: bool = False,
        fetch_extra_tags: bool = False,
    ):
        self.__dict__.update(base_downloader.__dict__)
        self.interface = interface
        self.codec = codec
        self.synced_lyrics_format = synced_lyrics_format
        self.no_synced_lyrics = no_synced_lyrics
        self.synced_lyrics_only = synced_lyrics_only
        self.use_album_date = use_album_date
        self.fetch_extra_tags = fetch_extra_tags

    async def get_download_item(
        self,
        song_metadata: dict,
        playlist_metadata: dict = None,
    ) -> DownloadItem:
        download_item = DownloadItem()

        download_item.media_metadata = song_metadata
        download_item.playlist_metadata = playlist_metadata

        song_id = self.interface.get_media_id_of_library_media(song_metadata)

        download_item.lyrics = await self.interface.get_lyrics(
            song_metadata,
            self.synced_lyrics_format,
        )

        webplayback = await self.interface.apple_music_api.get_webplayback(song_id)
        download_item.media_tags = await self.interface.get_tags(
            webplayback,
            download_item.lyrics.unsynced if download_item.lyrics else None,
            self.use_album_date,
        )
        if self.fetch_extra_tags:
            download_item.extra_tags = await self.interface.get_extra_tags(
                song_metadata,
            )

        if playlist_metadata:
            download_item.playlist_tags = self.naming.get_playlist_tags(
                playlist_metadata,
                song_metadata,
            )
            download_item.playlist_file_path = str(self.naming.get_playlist_file_path(
                download_item.playlist_tags,
            ))

        download_item.final_path = str(self.naming.get_final_path(
            download_item.media_tags,
            ".mp3" if self.remux_to_mp3 else ".m4a",
            download_item.playlist_tags,
        ))
        download_item.synced_lyrics_path = str(self.naming.get_lyrics_synced_path(
            Path(download_item.final_path),
            self.synced_lyrics_format.value,
        ))

        if self.synced_lyrics_only:
            return download_item

        if self.codec.is_legacy():
            download_item.stream_info = await self.interface.get_stream_info_legacy(
                webplayback,
                self.codec,
            )
            download_item.decryption_key = (
                await self.interface.get_decryption_key_legacy(
                    download_item.stream_info,
                    self.cdm,
                )
            )
        else:
            download_item.stream_info = await self.interface.get_stream_info(
                song_metadata,
                self.codec,
            )
            if (
                not self.use_wrapper
                and download_item.stream_info.audio_track.widevine_pssh
            ):
                download_item.decryption_key = (
                    await self.interface.get_decryption_key(
                        download_item.stream_info,
                        self.cdm,
                    )
                )

        download_item.cover_url_template = self.interface.get_cover_url_template(
            song_metadata,
            self.cover_format,
        )
        download_item.cover_url = self.interface.get_cover_url(
            download_item.cover_url_template,
            self.cover_size,
            self.cover_format,
        )

        download_item.random_uuid = self.get_random_uuid()
        if download_item.stream_info and download_item.stream_info.file_format:
            staged_extension = (
                ".mp3"
                if self.remux_to_mp3
                else "." + download_item.stream_info.file_format.value
            )
            download_item.staged_path = str(self.naming.get_temp_path(
                song_id,
                download_item.random_uuid,
                "staged",
                staged_extension,
            ))
        else:
            download_item.staged_path = None

        cover_file_extension = await self.interface.get_cover_file_extension(
            download_item.cover_url,
            self.cover_format,
        )
        if cover_file_extension:
            download_item.cover_path = str(self.naming.get_cover_path(
                Path(download_item.final_path),
                cover_file_extension,
            ))

        return download_item

    async def stage(
        self,
        encrypted_path: str,
        decrypted_path: str,
        staged_path: str,
        decryption_key: DecryptionKeyAv,
        codec: SongCodec,
        media_id: str,
        fairplay_key: str,
    ):
        if self.remux_to_mp3:
            if codec.is_legacy() and self.remux_mode == RemuxMode.FFMPEG:
                await self.remuxer.remux_ffmpeg(
                    [encrypted_path],
                    decrypted_path,
                    decryption_key.audio_track.key,
                )
            elif codec.is_legacy() or not self.use_wrapper:
                await self.decryptor.decrypt_mp4decrypt(
                    encrypted_path,
                    decrypted_path,
                    decryption_key.audio_track.key,
                    codec.is_legacy(),
                )
            else:
                await self.decryptor.decrypt_amdecrypt(
                    encrypted_path,
                    decrypted_path,
                    media_id,
                    fairplay_key,
                )
            bitrate_map = {"low": "128k", "mid": "160k", "high": "192k", "best": "320k"}
            await self.remuxer.remux_mp3(
                decrypted_path, 
                staged_path, 
                bitrate_map.get(self.mp3_bitrate, "160k")
            )
            return

        if codec.is_legacy() and self.remux_mode == RemuxMode.FFMPEG:
            await self.remuxer.remux_ffmpeg(
                [encrypted_path],
                staged_path,
                decryption_key.audio_track.key,
            )
        elif codec.is_legacy() or not self.use_wrapper:
            await self.decryptor.decrypt_mp4decrypt(
                encrypted_path,
                decrypted_path,
                decryption_key.audio_track.key,
                codec.is_legacy(),
            )
            if self.remux_mode == RemuxMode.FFMPEG:
                await self.remuxer.remux_ffmpeg(
                    [decrypted_path],
                    staged_path,
                )
            else:
                await self.remuxer.remux_mp4box(
                    [decrypted_path],
                    staged_path,
                )
        else:
            await self.decryptor.decrypt_amdecrypt(
                encrypted_path,
                staged_path,
                media_id,
                fairplay_key,
            )

    def write_synced_lyrics(
        self,
        synced_lyrics: str,
        lyrics_synced_path: str,
    ):
        Path(lyrics_synced_path).parent.mkdir(parents=True, exist_ok=True)
        Path(lyrics_synced_path).write_text(synced_lyrics, encoding="utf8")

    async def download(
        self,
        download_item: DownloadItem,
    ) -> None:
        if self.synced_lyrics_only:
            return

        encrypted_path = str(self.naming.get_temp_path(
            download_item.media_metadata["id"],
            download_item.random_uuid,
            "encrypted",
            ".m4a",
        ))
        await self.streamer.download(
            download_item.stream_info.audio_track.stream_url,
            Path(encrypted_path),
        )

        decrypted_path = str(self.naming.get_temp_path(
            download_item.media_metadata["id"],
            download_item.random_uuid,
            "decrypted",
            ".m4a",
        ))
        await self.stage(
            encrypted_path,
            decrypted_path,
            download_item.staged_path,
            download_item.decryption_key,
            self.codec,
            download_item.media_metadata["id"],
            download_item.stream_info.audio_track.fairplay_key,
        )

        cover_bytes = await self.interface.get_cover_bytes(download_item.cover_url)
        await self.apply_tags(
            Path(download_item.staged_path),
            download_item.media_tags,
            cover_bytes,
            download_item.extra_tags,
        )
