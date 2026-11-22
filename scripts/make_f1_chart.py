"""Draw the pitch F1 overview from reports/stats.json.

    python scripts/make_f1_chart.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / "reports" / "stats.json"
FALLBACK_STATS = ROOT / "front-end" / "assets" / "stats" / "stats.json"
OUTPUT = ROOT / "reports" / "charts" / "f1_overview.png"
SLIDE = ROOT / "docs" / "slides" / "f1_overview.png"

NAVY = "#1F2A44"
GREY = "#E6E8EC"
RED = "#C8102E"
INK = "#5C6570"

TYPES = (
    ("odwolanie", "Odwołanie"),
    ("pelnomocnictwo", "Pełnomocnictwo"),
    ("przelew", "Przelew"),
)


def main() -> None:
    source = STATS if STATS.is_file() else FALLBACK_STATS
    stats = json.loads(source.read_text(encoding="utf-8"))
    plt.rcParams["font.family"] = "Segoe UI"
    figure = plt.figure(figsize=(16, 9), dpi=120, facecolor="white")
    grid = figure.add_gridspec(1, 4, width_ratios=[1.45, 1, 1, 1])
    _headline(figure.add_subplot(grid[0, 0]), stats)
    for index, (key, label) in enumerate(TYPES, start=1):
        _donut(figure.add_subplot(grid[0, index]), stats["types"][key], label)
    figure.subplots_adjust(left=0.03, right=0.98, top=0.92, bottom=0.08, wspace=0.05)
    for path in (OUTPUT, SLIDE):
        path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(path, dpi=120, facecolor="white")
        print(path)
    plt.close(figure)


def _headline(axis, stats: dict) -> None:
    axis.set_axis_off()
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.text(0.5, 0.58, _comma(stats["f1"]), ha="center", va="center", fontsize=88, color=NAVY)
    axis.plot([0.30, 0.70], [0.43, 0.43], color=RED, linewidth=2.5, solid_capstyle="butt")
    axis.text(0.5, 0.33, "F1 (całość)", ha="center", va="center", fontsize=22, color=NAVY)
    detail = f"precyzja {_comma(stats['precision'])}  ·  czułość {_comma(stats['recall'])}"
    axis.text(0.5, 0.23, detail, ha="center", va="center", fontsize=14, color=INK)


def _donut(axis, bucket: dict, label: str) -> None:
    score = float(bucket["f1"])
    axis.set_aspect("equal")
    axis.pie(
        [score, max(0.0, 1.0 - score)],
        startangle=90,
        colors=[NAVY, GREY],
        wedgeprops={"width": 0.28, "linewidth": 0},
    )
    axis.text(0, 0.02, _comma(score), ha="center", va="center", fontsize=22, color=NAVY)
    axis.text(0, -1.35, label, ha="center", va="center", fontsize=16, color=NAVY)
    axis.text(0, -1.58, f"n = {bucket['documents']}", ha="center", va="center", fontsize=12, color=INK)


def _comma(value: float) -> str:
    return f"{float(value):.2f}".replace(".", ",")


if __name__ == "__main__":
    main()
