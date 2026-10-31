"""Creates two placeholder bucket images so you can test immediately.
Open an image full-screen on a phone/monitor and show it to the webcam."""
import cv2
import numpy as np

import config

SAMPLES = {"Bison Glow": (60, 140, 230), "Silk Blend": (140, 90, 200)}

config.IMAGES_DIR.mkdir(exist_ok=True)
for name, color in SAMPLES.items():
    img = np.full((600, 900, 3), 255, np.uint8)
    cv2.rectangle(img, (40, 40), (860, 560), color, -1)
    cv2.rectangle(img, (40, 40), (860, 560), (30, 30, 30), 6)
    for i, word in enumerate(name.split()):
        cv2.putText(img, word.upper(), (120, 250 + i * 140),
                    cv2.FONT_HERSHEY_DUPLEX, 4, (255, 255, 255), 8, cv2.LINE_AA)
    cv2.imwrite(str(config.IMAGES_DIR / f"{name}.png"), img)
    print("Created", f"{name}.png")