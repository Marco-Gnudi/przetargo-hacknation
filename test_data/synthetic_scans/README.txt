Degraded scans of the official UZP examples (przyklad_01 to przyklad_60).

Each folder keeps the original PDF names and the reference JSON next to them.
The PDFs are image-only: contrast, blur, noise, a small rotation and JPEG compression,
so they exercise OCR. Regenerate them with:

    python backend/scripts/make_synthetic_scans.py --out /tmp/synth

Score them with:

    python backend/scripts/evaluate.py --data test_data/synthetic_scans --mode regular

Last measured regular-mode F1 on this set: 0.948.
