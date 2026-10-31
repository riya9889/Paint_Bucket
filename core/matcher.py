"""Text normalisation, fuzzy matching and per-frame evaluation."""
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import List, Optional

import config
from .models import Detection

# Treat commonly confused OCR characters as identical on both sides.
_CONFUSIONS = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5"})


def normalize(text: str) -> str:
    cleaned = re.sub(r"[^A-Z0-9]", "", text.upper())
    return cleaned.translate(_CONFUSIONS)


def partial_ratio(needle: str, haystack: str) -> float:
    """Best similarity of `needle` against any same-sized window of `haystack`."""
    if not needle or not haystack:
        return 0.0
    n = len(needle)
    if len(haystack) <= n:
        return SequenceMatcher(None, needle, haystack).ratio()
    best = 0.0
    for size in {max(1, n - 1), n, n + 1}:
        for i in range(len(haystack) - size + 1):
            best = max(best, SequenceMatcher(None, needle, haystack[i:i + size]).ratio())
            if best == 1.0:
                return 1.0
    return best


def reading_order(detections: List[Detection]) -> List[Detection]:
    """Sort detections into lines (top to bottom), then left to right."""
    lines: List[List[Detection]] = []
    for det in sorted(detections, key=lambda d: d.center_y):
        for line in lines:
            ref = line[0]
            if abs(ref.center_y - det.center_y) <= 0.6 * max(ref.height, det.height):
                line.append(det)
                break
        else:
            lines.append([det])
    ordered: List[Detection] = []
    for line in sorted(lines, key=lambda ln: ln[0].center_y):
        ordered.extend(sorted(line, key=lambda d: d.center_x))
    return ordered


@dataclass
class FrameOutcome:
    kind: str                       # "unclear" | "product" | "unknown"
    product: Optional[str] = None
    score: float = 0.0
    texts: List[str] = field(default_factory=list)
    confidence: float = 0.0


def evaluate_frame(detections: List[Detection], product_names: List[str]) -> FrameOutcome:
    # 1. Drop low-confidence / empty words (handles unclear text)
    usable = [d for d in detections
              if d.confidence >= config.MIN_WORD_CONFIDENCE and normalize(d.text)]
    if not usable:
        return FrameOutcome("unclear")

    ordered = reading_order(usable)
    texts = [d.text for d in ordered]
    avg_conf = sum(d.confidence for d in ordered) / len(ordered)

    combined = normalize(" ".join(texts))
    if len(combined) < config.MIN_TEXT_LENGTH:
        return FrameOutcome("unclear", texts=texts, confidence=avg_conf)

    # 2. Handle multiple results: test the joined text AND each word separately
    haystacks = [combined] + [normalize(t) for t in texts]

    best = None  # ((score, name_length), name)
    for name in product_names:
        needle = normalize(name)
        if not needle:
            continue
        score = max(partial_ratio(needle, h) for h in haystacks)
        if score >= config.MATCH_THRESHOLD:
            key = (score, len(needle))   # ties prefer the longer product name
            if best is None or key > best[0]:
                best = (key, name)

    if best is None:
        return FrameOutcome("unknown", texts=texts, confidence=avg_conf)
    return FrameOutcome("product", product=best[1], score=best[0][0],
                        texts=texts, confidence=avg_conf)