from pathlib import Path
from mutagen.mp4 import MP4, MP4Cover
from ..interface.enums import CoverFormat


class MP4Tagger:
    @staticmethod
    def apply(
        media_path: Path,
        tags: dict,
        cover_bytes: bytes | None,
        skip_tagging: bool,
        extra_tags: dict | None,
        cover_format: CoverFormat,
    ):
        mp4 = MP4(media_path)
        mp4.clear()

        if not skip_tagging:
            if cover_bytes is not None:
                mp4["covr"] = [
                    MP4Cover(
                        data=cover_bytes,
                        imageformat=(
                            MP4Cover.FORMAT_JPEG
                            if cover_format == CoverFormat.JPG
                            else MP4Cover.FORMAT_PNG
                        ),
                    )
                ]

            for key, value in tags.items():
                if value is not None:
                    mp4[key] = value

            if extra_tags:
                mp4.update(extra_tags)

        mp4.save()
