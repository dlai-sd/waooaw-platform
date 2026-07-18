"""
Convert light-background logos to dark-background (transparent + white text) variants.
Used for Platform DNA strip which sits on --color-brand-navy (#1E3352).

Logic:
  - White/near-white pixels (background)  → transparent
  - Dark/black pixels (text, dark marks)  → white
  - Coloured pixels (brand marks/icons)   → kept exactly as-is
"""

from PIL import Image
import numpy as np
import os

BRAND_DIR = os.path.join(os.path.dirname(__file__), "..", "architecture", "reference", "ux", "brand")
BRAND_DIR = os.path.abspath(BRAND_DIR)

def make_dark_variant(input_path: str, output_path: str, name: str) -> None:
    img = Image.open(input_path).convert("RGBA")
    data = np.array(img, dtype=np.float32)

    r, g, b, a = data[:,:,0], data[:,:,1], data[:,:,2], data[:,:,3]
    lightness  = (r + g + b) / 3.0
    max_c      = np.maximum(np.maximum(r, g), b)
    min_c      = np.minimum(np.minimum(r, g), b)
    saturation = np.where(max_c > 0, (max_c - min_c) / max_c, 0.0)

    is_bg        = (lightness > 230) & (saturation < 0.12)
    is_dark_text = (lightness <  80) & (saturation < 0.25)

    out = data.copy()
    out[is_bg,        3] = 0
    out[is_dark_text, 0] = 255
    out[is_dark_text, 1] = 255
    out[is_dark_text, 2] = 255
    out[is_dark_text, 3] = 255

    Image.fromarray(out.astype(np.uint8), "RGBA").save(output_path)
    print(f"  {name}: bg removed {int(is_bg.sum()):,}px | dark->white {int(is_dark_text.sum()):,}px -> {output_path}")

print("Generating dark-background logo variants...")
make_dark_variant(
    os.path.join(BRAND_DIR, "dlaisd-logo.png"),
    os.path.join(BRAND_DIR, "dlaisd-logo-dark.png"),
    "DLAISD"
)
make_dark_variant(
    os.path.join(BRAND_DIR, "yashus-logo.png"),
    os.path.join(BRAND_DIR, "yashus-logo-dark.png"),
    "Yashus"
)
print("Done.")
