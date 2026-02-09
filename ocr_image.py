#!/usr/bin/env python3
import sys
from PIL import Image
import pytesseract

if len(sys.argv) < 2:
    print("Usage: python3 ocr_image.py <image_path> [language]")
    sys.exit(1)

image_path = sys.argv[1]
lang = sys.argv[2] if len(sys.argv) > 2 else "eng"

try:
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang=lang)
    print(text.strip())
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
