import re
from pathlib import Path
from ..interface.types import MediaTags, PlaylistTags
from .formatter import CustomStringFormatter
from ..downloader.constants import ILLEGAL_CHAR_REPLACEMENT, ILLEGAL_CHARS_RE, TEMP_PATH_TEMPLATE


class NamingProvider:
    def __init__(
        self,
        output_path: str,
        temp_path: str,
        album_folder_template: str,
        compilation_folder_template: str,
        no_album_folder_template: str,
        single_disc_file_template: str,
        multi_disc_file_template: str,
        no_album_file_template: str,
        playlist_file_template: str,
        truncate: int = None,
    ):
        self.output_path = Path(output_path)
        self.temp_path = Path(temp_path)
        self.album_folder_template = album_folder_template
        self.compilation_folder_template = compilation_folder_template
        self.no_album_folder_template = no_album_folder_template
        self.single_disc_file_template = single_disc_file_template
        self.multi_disc_file_template = multi_disc_file_template
        self.no_album_file_template = no_album_file_template
        self.playlist_file_template = playlist_file_template
        self.truncate = truncate
        self.formatter = CustomStringFormatter()

    def sanitize_string(self, dirty_string: str, file_ext: str = None) -> str:
        sanitized_string = re.sub(
            ILLEGAL_CHARS_RE,
            ILLEGAL_CHAR_REPLACEMENT,
            dirty_string,
        )

        if file_ext is None:
            sanitized_string = sanitized_string[: self.truncate]
            if sanitized_string.endswith("."):
                sanitized_string = sanitized_string[:-1] + ILLEGAL_CHAR_REPLACEMENT
        else:
            if self.truncate is not None:
                sanitized_string = sanitized_string[: self.truncate - len(file_ext)]
            sanitized_string += file_ext

        return sanitized_string.strip()

    def get_playlist_tags(
        self,
        playlist_metadata: dict,
        media_metadata: dict,
    ) -> PlaylistTags:
        playlist_track = (
            playlist_metadata["relationships"]["tracks"]["data"].index(media_metadata)
            + 1
        )

        return PlaylistTags(
            playlist_artist=playlist_metadata["attributes"].get(
                "curatorName", "Unknown"
            ),
            playlist_id=playlist_metadata["attributes"]["playParams"]["id"],
            playlist_title=playlist_metadata["attributes"]["name"],
            playlist_track=playlist_track,
        )

    def get_final_path(
        self,
        tags: MediaTags,
        file_extension: str,
        playlist_tags: PlaylistTags | None = None,
    ) -> Path:
        if tags.album:
            template_folder_parts = (
                self.compilation_folder_template.split("/")
                if tags.compilation
                else self.album_folder_template.split("/")
            )
            template_file_parts = (
                self.multi_disc_file_template.split("/")
                if isinstance(tags.disc_total, int) and tags.disc_total > 1
                else self.single_disc_file_template.split("/")
            )
        else:
            template_folder_parts = self.no_album_folder_template.split("/")
            template_file_parts = self.no_album_file_template.split("/")

        template_parts = template_folder_parts + template_file_parts
        formatted_parts = []

        for i, part in enumerate(template_parts):
            is_folder = i < len(template_parts) - 1
            formatted_part = self.formatter.format(
                part,
                album=(tags.album, "Unknown Album"),
                album_artist=(tags.album_artist, "Unknown Artist"),
                album_id=(tags.album_id, "Unknown Album ID"),
                artist=(tags.artist, "Unknown Artist"),
                artist_id=(tags.artist_id, "Unknown Artist ID"),
                composer=(tags.composer, "Unknown Composer"),
                composer_id=(tags.composer_id, "Unknown Composer ID"),
                date=(tags.date, "Unknown Date"),
                disc=(tags.disc, ""),
                disc_total=(tags.disc_total, ""),
                media_type=(tags.media_type, "Unknown Media Type"),
                playlist_artist=(
                    (playlist_tags.playlist_artist if playlist_tags else None),
                    "Unknown Playlist Artist",
                ),
                playlist_id=(
                    (playlist_tags.playlist_id if playlist_tags else None),
                    "Unknown Playlist ID",
                ),
                playlist_title=(
                    (playlist_tags.playlist_title if playlist_tags else None),
                    "Unknown Playlist Title",
                ),
                playlist_track=(
                    (playlist_tags.playlist_track if playlist_tags else None),
                    "",
                ),
                title=(tags.title, "Unknown Title"),
                title_id=(tags.title_id, "Unknown Title ID"),
                track=(tags.track, ""),
                track_total=(tags.track_total, ""),
            )
            sanitized_formatted_part = self.sanitize_string(
                formatted_part,
                file_extension if not is_folder else None,
            )
            formatted_parts.append(sanitized_formatted_part)

        return self.output_path.joinpath(*formatted_parts)

    def get_temp_path(
        self,
        media_id: str,
        folder_tag: str,
        file_tag: str,
        file_extension: str,
    ) -> Path:
        return (
            self.temp_path
            / TEMP_PATH_TEMPLATE.format(folder_tag)
            / (f"{media_id}_{file_tag}" + file_extension)
        )

    def get_cover_path(self, final_path: Path, file_extension: str) -> Path:
        return final_path.parent / ("Cover" + file_extension)

    def get_lyrics_synced_path(self, final_path: Path, extension: str) -> Path:
        return final_path.with_suffix("." + extension)

    def get_playlist_file_path(self, tags: PlaylistTags) -> Path:
        template_file_parts = self.playlist_file_template.split("/")
        formatted_parts = []

        for i, part in enumerate(template_file_parts):
            is_folder = i < len(template_file_parts) - 1
            formatted_part = self.formatter.format(
                part,
                playlist_artist=(tags.playlist_artist, "Unknown Playlist Artist"),
                playlist_id=(tags.playlist_id, "Unknown Playlist ID"),
                playlist_title=(tags.playlist_title, "Unknown Playlist Title"),
                playlist_track=(tags.playlist_track, ""),
            )
            sanitized_formatted_part = self.sanitize_string(
                formatted_part,
                ".m3u8" if not is_folder else None, # Assuming .m3u8 for playlists
            )
            formatted_parts.append(sanitized_formatted_part)

        return self.output_path.joinpath(*formatted_parts)
