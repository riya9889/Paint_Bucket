"""Central configuration. Tweak values here, not in the code."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "Images"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Server
HOST = "127.0.0.1"
PORT = 5000

# Camera
CAMERA_INDEX = 0          # try 1 if you have several cameras
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
JPEG_QUALITY = 80

# OCR
OCR_LANGUAGES = ["en"]
OCR_USE_GPU = False
OCR_MAX_WIDTH = 960           # frames are downscaled to this width before OCR
OCR_INTERVAL_SECONDS = 0.4    # pause between OCR runs

# Matching / decision logic
MIN_WORD_CONFIDENCE = 0.35    # ignore OCR words below this confidence
MIN_TEXT_LENGTH = 3           # ignore results with fewer characters than this
MATCH_THRESHOLD = 0.80        # fuzzy similarity (0-1) needed to accept a match
HISTORY_SIZE = 4              # number of recent frames considered
REQUIRED_AGREEMENT = 2        # frames that must agree before showing PASS/REJECT