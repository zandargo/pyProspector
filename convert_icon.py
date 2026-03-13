"""convert_icon.py

Convert the PNG application icon to ICO format for PyInstaller and Inno Setup.
Run this script once before building the installer.

Usage:
    python convert_icon.py
"""

import os
import sys

from PIL import Image


def convert_icon() -> str:
    base = os.path.dirname(os.path.abspath(__file__))
    icon_dir = os.path.join(base, "assets", "icon")
    png_path = os.path.join(icon_dir, "pyProspector01.png")
    ico_path = os.path.join(icon_dir, "pyProspector01.ico")

    if not os.path.exists(png_path):
        print(f"ERROR: PNG icon not found: {png_path}", file=sys.stderr)
        sys.exit(1)

    img = Image.open(png_path).convert("RGBA")

    # Multi-resolution ICO required by Windows (16 → 256 px)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    frames = [img.resize(s, Image.LANCZOS) for s in sizes]

    frames[0].save(
        ico_path,
        format="ICO",
        sizes=sizes,
        append_images=frames[1:],
    )
    print(f"  [OK] ICO  -> {ico_path}")
    return ico_path


if __name__ == "__main__":
    print("Generating icon files...")
    convert_icon()
    print("Done.")
