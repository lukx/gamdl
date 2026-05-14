from pathlib import Path


class CoverManager:
    def __init__(self, interface):
        self.interface = interface

    async def get_cover_bytes(self, url: str) -> bytes | None:
        return await self.interface.get_cover_bytes(url)

    def save_cover(self, cover_bytes: bytes, cover_path: Path):
        cover_path.parent.mkdir(parents=True, exist_ok=True)
        cover_path.write_bytes(cover_bytes)
