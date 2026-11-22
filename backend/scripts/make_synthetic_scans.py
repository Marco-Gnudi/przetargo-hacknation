"""Turn the text PDFs in dane/ into degraded image-only scans for a held-out OCR test.

The reference JSONs are copied next to each scan, so evaluate.py can score them.
The set this script produced is committed at test_data/synthetic_scans (184 scans).

    python backend/scripts/make_synthetic_scans.py --out /tmp/synth
    python backend/scripts/evaluate.py --data test_data/synthetic_scans --mode regular
"""

from __future__ import annotations

import argparse
import io
import random
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "UZP-hacknation-task" / "dane"


def degrade(image: Image.Image, rng: random.Random) -> Image.Image:
    gray = image.convert("L")
    gray = ImageEnhance.Contrast(gray).enhance(rng.uniform(0.6, 0.9))
    gray = ImageEnhance.Brightness(gray).enhance(rng.uniform(0.9, 1.05))
    gray = gray.rotate(rng.uniform(-1.8, 1.8), fillcolor=235, expand=True, resample=Image.Resampling.BICUBIC)
    gray = gray.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 1.0)))
    noise = Image.effect_noise(gray.size, rng.uniform(12, 28))
    gray = Image.blend(gray, noise, rng.uniform(0.06, 0.12))
    buffer = io.BytesIO()
    gray.save(buffer, "JPEG", quality=rng.randint(35, 60))
    return Image.open(io.BytesIO(buffer.getvalue()))


def scan_pdf(source: Path, target: Path, seed: int) -> None:
    rng = random.Random(seed)
    dpi = rng.choice((150, 200, 200, 300))
    with pymupdf.open(source) as pdf, pymupdf.open() as out:
        for page in pdf:
            pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY, alpha=False)
            image = degrade(Image.open(io.BytesIO(pixmap.tobytes("png"))), rng)
            buffer = io.BytesIO()
            image.save(buffer, "JPEG", quality=90)
            new = out.new_page(width=page.rect.width, height=page.rect.height)
            new.insert_image(new.rect, stream=buffer.getvalue())
        out.save(target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0, help="Only the first N example folders.")
    args = parser.parse_args()
    folders = sorted(path for path in args.data.glob("przyklad_*") if path.is_dir())
    if args.limit:
        folders = folders[: args.limit]
    count = 0
    for index, folder in enumerate(folders):
        target_dir = args.out / folder.name
        target_dir.mkdir(parents=True, exist_ok=True)
        for item in folder.iterdir():
            if item.suffix == ".json":
                shutil.copy2(item, target_dir / item.name)
            elif item.suffix == ".pdf" and item.stat().st_size > 0:
                scan_pdf(item, target_dir / item.name, seed=index * 31 + len(item.name))
                count += 1
    print(f"wrote {count} scans to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
