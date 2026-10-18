"""Download the pinned Open Food Facts challenge photos with hash verification.

The images are CC BY-SA 3.0 per https://world.openfoodfacts.org/data .
Product packaging may contain other protected graphical elements; use for QA.
"""

import hashlib
import json
from pathlib import Path

import httpx
from PIL import Image


ROOT = Path(__file__).resolve().parent
SOURCES = json.loads((ROOT / "sources.json").read_text())
HEADERS = {"User-Agent": "VeriLabel-QA/0.1 (https://github.com/Auth3nticAI/ai-product-label-verification)"}


def main():
    folder = ROOT / "images"
    folder.mkdir(exist_ok=True)
    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30) as client:
        for item in SOURCES:
            image = folder / item["file"]
            if not image.exists():
                response = client.get(item["url"])
                response.raise_for_status()
                if len(response.content) >= 4_500_000:
                    raise ValueError(f"{item['file']}: exceeds upload limit")
                image.write_bytes(response.content)
            data = image.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if len(data) != item["bytes"] or digest != item["sha256"]:
                raise ValueError(f"{item['file']}: source checksum changed")
            with Image.open(image) as decoded:
                decoded.verify()
            print(f"VERIFIED {item['file']} {len(data)} {digest}")


if __name__ == "__main__":
    main()
