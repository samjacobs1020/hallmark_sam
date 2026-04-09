import shutil
from pathlib     import Path

class Cache:
    def __init__(self, path):
        self.root = Path(path) / "cache"

    def _split_checksum(self, sha1: str) -> Path:
        return self.root / sha1[:2] / sha1[2:]

    def store(self, src: Path, sha1: str) -> Path:
        stored_checksum = self._split_checksum(sha1)
        if not stored_checksum.exists():
            stored_checksum.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, stored_checksum)
        return stored_checksum