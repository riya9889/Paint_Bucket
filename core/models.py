"""Small shared data structures."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    """One piece of text found by OCR, in original frame coordinates."""
    text: str
    confidence: float
    box: tuple  # four (x, y) corner points

    @property
    def center_x(self) -> float:
        return sum(p[0] for p in self.box) / 4

    @property
    def center_y(self) -> float:
        return sum(p[1] for p in self.box) / 4

    @property
    def height(self) -> float:
        ys = [p[1] for p in self.box]
        return max(ys) - min(ys)


@dataclass(frozen=True)
class Bucket:
    """A reference paint bucket: exact product name + its image file."""
    name: str
    filename: str