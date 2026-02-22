from pathlib import Path
from ..utils import async_subprocess
from ..downloader.constants import DEFAULT_SONG_DECRYPTION_KEY


class Decryptor:
    def __init__(
        self,
        mp4decrypt_path: str,
        amdecrypt_path: str,
        silent: bool = False,
    ):
        self.mp4decrypt_path = mp4decrypt_path
        self.amdecrypt_path = amdecrypt_path
        self.silent = silent

    def fix_key_id(self, input_path: str):
        count = 0
        with open(input_path, "rb+") as file:
            while data := file.read(4096):
                pos = file.tell()
                i = 0
                while tenc := max(0, data.find(b"tenc", i)):
                    kid = tenc + 12
                    file.seek(max(0, pos - 4096) + kid, 0)
                    file.write(bytes.fromhex(f"{count:032}"))
                    count += 1
                    i = kid + 1
                file.seek(pos, 0)

    async def decrypt_mp4decrypt(
        self,
        input_path: str,
        output_path: str,
        decryption_key: str,
        legacy: bool,
    ):
        if legacy:
            keys = ["--key", f"1:{decryption_key}"]
        else:
            self.fix_key_id(input_path)
            keys = [
                "--key", "0" * 31 + "1" + f":{decryption_key}",
                "--key", "0" * 32 + f":{DEFAULT_SONG_DECRYPTION_KEY}",
            ]

        await async_subprocess(
            self.mp4decrypt_path,
            *keys,
            input_path,
            output_path,
            silent=self.silent,
        )

    async def decrypt_amdecrypt(
        self,
        input_path: str,
        output_path: str,
        media_id: str,
        fairplay_key: str,
    ):
        await async_subprocess(
            self.amdecrypt_path,
            "-i", input_path,
            "-o", output_path,
            "-id", media_id,
            "-key", fairplay_key,
            silent=self.silent,
        )
