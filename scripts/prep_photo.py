#!/usr/bin/env python3
"""
prep_photo.py — turn a raw photo into a high-contrast, white-background
grayscale image that converts cleanly to ASCII art.

    python scripts/prep_photo.py source-photo.jpg

Pipeline:
  1. rembg      -> cut the subject out of its background
  2. CLAHE      -> contrast-limited adaptive histogram equalization, so a
                   flatly-lit face gains real highlights and shadows
  3. composite  -> flatten onto pure white, because white maps to the blank
                   (space) end of the ASCII ramp

Writes: source-prepped.png

opencv / rembg are optional. If either is missing the script falls back to a
pure-Pillow path (autocontrast + local equalization approximation) so you can
still get a usable result.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, ImageEnhance

OUT = Path("source-prepped.png")
MASK = Path("source-mask.png")
MAX_SIDE = 1200


def cutout(img: Image.Image) -> Image.Image:
    """Remove the background with rembg; returns RGBA."""
    try:
        from rembg import remove  # type: ignore

        print("  - removing background (rembg)")
        return remove(img).convert("RGBA")
    except Exception as exc:
        print(f"  ! rembg unavailable ({type(exc).__name__}) - keeping background")
        return img.convert("RGBA")


def head_crop(img: Image.Image) -> Image.Image:
    """Crop to head-and-shoulders.

    ASCII has ~100 columns of detail to spend. Spending them on a full torso
    (especially a patterned shirt, which becomes noise) leaves too few for the
    face. Detect the face and frame it; fall back to the upper portion.
    """
    w, h = img.size
    box = None
    try:
        import cv2  # type: ignore

        gray = np.asarray(img.convert("L"), dtype=np.uint8)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(gray, 1.08, 5, minSize=(w // 12, h // 12))
        if len(faces):
            fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            print(f"  - face detected at {fw}x{fh}")
            cx = fx + fw / 2
            # frame: ~0.85 face-heights above, ~1.75 below -> head + a little shoulder
            top = fy - fh * 0.85
            bottom = fy + fh * 1.75
            half = (bottom - top) * 0.44
            box = (cx - half, top, cx + half, bottom)
    except Exception as exc:
        print(f"  ! face detect unavailable ({type(exc).__name__})")

    if box is None:
        print("  - no face found, cropping upper 62%")
        box = (w * 0.08, 0, w * 0.92, h * 0.62)

    x0, y0, x1, y1 = (int(max(0, box[0])), int(max(0, box[1])),
                      int(min(w, box[2])), int(min(h, box[3])))
    if x1 - x0 < 40 or y1 - y0 < 40:
        return img
    print(f"  - head crop {x1-x0}x{y1-y0}")
    return img.crop((x0, y0, x1, y1))


def clahe(gray: np.ndarray) -> np.ndarray:
    """Contrast-limited adaptive histogram equalization."""
    try:
        import cv2  # type: ignore
    except Exception:
        print("  ! opencv unavailable - using global autocontrast fallback")
        pil = ImageOps.autocontrast(Image.fromarray(gray), cutoff=2)
        return np.asarray(ImageEnhance.Contrast(pil).enhance(1.35), dtype=np.uint8)
    print("  - boosting local contrast (CLAHE)")
    op = cv2.createCLAHE(clipLimit=float(os.environ.get("CLIP", "3.6")),
                         tileGridSize=(8, 8))
    out = op.apply(gray)
    # unsharp mask: a small/soft source loses its edges when downsampled to a
    # ~100-column character grid, so put them back before sampling
    blur = cv2.GaussianBlur(out, (0, 0), 3.0)
    return cv2.addWeighted(out, 1.55, blur, -0.55, 0)


def main(src: str) -> None:
    path = Path(src)
    if not path.exists():
        sys.exit(f"no such file: {path}")

    print(f"prepping {path}")
    img = Image.open(path).convert("RGBA")
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

    cut = cutout(img)

    # crop to the subject so the ASCII grid isn't mostly empty margin
    alpha = cut.split()[-1]
    box = alpha.getbbox()
    if box:
        pad_x = int((box[2] - box[0]) * 0.04)
        pad_y = int((box[3] - box[1]) * 0.04)
        box = (
            max(0, box[0] - pad_x),
            max(0, box[1] - pad_y),
            min(cut.width, box[2] + pad_x),
            min(cut.height, box[3] + pad_y),
        )
        cut = cut.crop(box)
        print(f"  - cropped to subject {cut.width}x{cut.height}")

    if os.environ.get("NO_HEAD_CROP") != "1":
        cut = head_crop(cut)

    # flatten onto pure white so the background becomes ASCII whitespace
    white = Image.new("RGBA", cut.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, cut).convert("L")

    arr = clahe(np.asarray(flat, dtype=np.uint8))

    # persist the subject mask so the ASCII step can normalize tones over the
    # subject alone instead of letting the white background skew the histogram
    a = np.asarray(cut.split()[-1], dtype=np.uint8)
    Image.fromarray((a > 128).astype(np.uint8) * 255).save(MASK)
    print(f"  - wrote {MASK} ({int((a > 128).mean() * 100)}% subject)")

    # push the very brightest tones all the way to paper white
    arr = np.where(arr > 238, 255, arr).astype(np.uint8)

    Image.fromarray(arr).save(OUT)
    print(f"wrote {OUT}  ({Image.fromarray(arr).size[0]}x{Image.fromarray(arr).size[1]})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "source-photo.jpg")
