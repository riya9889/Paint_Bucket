"""Reads the Images folder and exposes the list of known paint buckets.

Rule: the image file name (without extension) is the exact product name.
    Images/Bison Glow.jpg  -> "Bison Glow"
    Images/Silk_Blend.png  -> "Silk Blend"   (underscores become spaces)
The folder is re-scanned on every call, so new images appear without a restart.
"""
import re
from pathlib import Path
from typing import List, Optional

from .models import Bucket


class BucketCatalog:
    def __init__(self, images_dir: Path, allowed_extensions: set):
        self._dir = Path(images_dir)
        self._exts = {e.lower() for e in allowed_extensions}
        self._dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _name_from_file(path: Path) -> str:
        return re.sub(r"\s+", " ", path.stem.replace("_", " ")).strip()

    def scan(self) -> List[Bucket]:
        buckets = []
        for path in sorted(self._dir.iterdir(), key=lambda p: p.name.lower()):
            if path.is_file() and path.suffix.lower() in self._exts:
                name = self._name_from_file(path)
                if name:
                    buckets.append(Bucket(name=name, filename=path.name))
        return buckets

    def names(self) -> List[str]:
        return [b.name for b in self.scan()]

    def get(self, name: str) -> Optional[Bucket]:
        for bucket in self.scan():
            if bucket.name == name:
                return bucket
        return None

    @property
    def directory(self) -> Path:
        return self._dir