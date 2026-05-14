from pathlib import Path
from typing import List, Union
from ..utils import async_subprocess


class Remuxer:
    def __init__(
        self,
        ffmpeg_path: str,
        mp4box_path: str,
        silent: bool = False,
    ):
        self.ffmpeg_path = ffmpeg_path
        self.mp4box_path = mp4box_path
        self.silent = silent

    async def remux_mp3(self, input_path: Union[str, Path], output_path: Union[str, Path], bitrate: str):
        await async_subprocess(
            self.ffmpeg_path,
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(input_path),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            "-id3v2_version",
            "3",
            str(output_path),
            silent=self.silent,
        )

    async def remux_ffmpeg(
        self,
        input_paths: List[Union[str, Path]],
        output_path: Union[str, Path],
        decryption_key: str = None,
        movflags: str = "+faststart",
        copy_subtitles: bool = False,
    ):
        key_args = ["-decryption_key", decryption_key] if decryption_key else []
        
        inputs = []
        for p in input_paths:
            inputs.extend(["-i", str(p)])
            
        subtitle_args = ["-c:s", "mov_text"] if copy_subtitles else []

        await async_subprocess(
            self.ffmpeg_path,
            "-loglevel",
            "error",
            "-y",
            *key_args,
            *inputs,
            "-c",
            "copy",
            *subtitle_args,
            "-movflags",
            movflags,
            str(output_path),
            silent=self.silent,
        )

    async def remux_mp4box(self, input_paths: List[Union[str, Path]], output_path: Union[str, Path], silent: bool = False):
        inputs = []
        for p in input_paths:
            inputs.extend(["-add", str(p)])
            
        await async_subprocess(
            self.mp4box_path,
            "-quiet",
            *inputs,
            "-itags",
            "keep",
            "-new",
            str(output_path),
            silent=self.silent or silent,
        )
