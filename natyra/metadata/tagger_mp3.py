from pathlib import Path
from mutagen.id3 import (
    APIC,
    COMM,
    ID3,
    TALB,
    TCMP,
    TCOM,
    TCON,
    TDRC,
    TIT2,
    TPOS,
    TPE1,
    TPE2,
    TRCK,
)


class MP3Tagger:
    @staticmethod
    def apply(
        media_path: Path,
        tags: dict,
        cover_bytes: bytes | None,
        skip_tagging: bool,
    ):
        try:
            id3 = ID3(media_path)
        except:
            id3 = ID3()

        id3.delete(media_path)

        if not skip_tagging:
            if cover_bytes is not None:
                id3.add(
                    APIC(
                        encoding=1,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=cover_bytes,
                    )
                )

            tag_map = {
                "TALB": (TALB, tags.get("\xa9alb")),
                "TPE2": (TPE2, tags.get("aART")),
                "TPE1": (TPE1, tags.get("\xa9ART")),
                "COMM": (COMM, tags.get("\xa9cmt")),
                "TCOM": (TCOM, tags.get("\xa9wrt")),
                "TDRC": (TDRC, tags.get("\xa9day")),
                "TCON": (TCON, tags.get("\xa9gen")),
                "TIT2": (TIT2, tags.get("\xa9nam")),
                "TRCK": (TRCK, tags.get("trkn")),
                "TPOS": (TPOS, tags.get("disk")),
                "TCMP": (TCMP, tags.get("cpil")),
            }

            for frame_id, (frame_class, value) in tag_map.items():
                if value is not None:
                    if frame_id == "TRCK":
                        id3.add(
                            TRCK(encoding=1, text=[f"{value[0][0]}/{value[0][1]}"])
                        )
                    elif frame_id == "TPOS":
                        id3.add(
                            TPOS(encoding=1, text=[f"{value[0][0]}/{value[0][1]}"])
                        )
                    elif frame_id == "TCMP":
                        id3.add(TCMP(encoding=1, text=["1" if value else "0"]))
                    elif frame_id == "COMM":
                        id3.add(
                            COMM(encoding=1, lang="eng", desc="", text=[str(value[0])])
                        )
                    else:
                        id3.add(frame_class(encoding=1, text=[str(value[0])]))

            id3.save(media_path, v2_version=3)
