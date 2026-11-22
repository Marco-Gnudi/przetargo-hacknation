"""Score each data set with the same field metric as evaluate.py.

    python scripts/eval_datasets.py
    python scripts/eval_datasets.py --chart-only

Bielik mode, LLM cache on: rules first, then the model fills empty fields.
Writes reports/stats_datasets.json and docs/slides/datasets_comparison.png.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / "reports" / "stats_datasets.json"
SLIDE = ROOT / "docs" / "slides" / "datasets_comparison.png"

NAVY = "#1F2A44"
RED = "#C8102E"

# Chart order. A group with no documents is left out.
GROUPS = (
    ("uzp_text", "UZP, tekst"),
    ("uzp_scan", "UZP, skany"),
    ("uzp_negative", "UZP, negatywne"),
    ("irregular_easy", "Nieregularne, łatwe"),
    ("irregular_mid", "Nieregularne, średnie"),
    ("irregular_hard", "Nieregularne, trudne"),
    ("synth_odwolanie", "Skany syntetyczne, odwołanie"),
    ("synth_pelnomocnictwo", "Skany syntetyczne, pełnomocnictwo"),
    ("synth_przelew", "Skany syntetyczne, przelew"),
    ("synth_negative", "Skany syntetyczne, negatywne"),
)

_NEEDED = threading.local()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chart-only", action="store_true", help="Redraw the slide from stats_datasets.json.")
    args = parser.parse_args(argv)
    if args.chart_only:
        payload = json.loads(STATS.read_text(encoding="utf-8"))
        _draw(payload)
        return 0
    payload = _evaluate()
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {STATS}")
    _print_table(payload)
    try:
        _draw(payload)
    except ImportError:
        print("matplotlib is not installed in this interpreter; redraw with --chart-only.", file=sys.stderr)
    return 0


def _evaluate() -> dict:
    evaluate = _load_evaluate()
    from odwolania.config import task_data_dir
    from odwolania.llm import load_env, set_skip_cache, start_usage, current_usage
    from odwolania import llm_extractor
    import vision_fill

    load_env()
    set_skip_cache(False)
    rules = evaluate.load_rules()
    _install_need_markers(llm_extractor, vision_fill)

    jobs = _jobs(task_data_dir())
    if not jobs:
        print("No PDFs found.", file=sys.stderr)
        raise SystemExit(2)
    print(f"scoring {len(jobs)} PDFs  mode bielik  cache on", flush=True)

    rows: list[dict | None] = [None] * len(jobs)

    def job(pdf: Path, group: str | None) -> dict:
        start_usage()
        _NEEDED.hit = False
        started = time.perf_counter()
        scored = evaluate._score_pdf(pdf, "bielik", rules)
        seconds = time.perf_counter() - started
        needed = bool(getattr(_NEEDED, "hit", False)) or int(current_usage().get("calls", 0)) > 0
        scored["seconds"] = seconds
        scored["llm"] = needed
        scored["group"] = group or _group_after_score(pdf, scored)
        return scored

    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(job, pdf, group): index for index, (pdf, group) in enumerate(jobs)}
        for future in as_completed(futures):
            rows[futures[future]] = future.result()
            done += 1
            if done % 20 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}", flush=True)

    finished = [row for row in rows if row is not None]
    unknown = [row for row in finished if row["group"] is None]
    if unknown:
        names = ", ".join(str(row["file"]) for row in unknown[:8])
        print(f"skipped {len(unknown)} PDF(s) with no group: {names}", file=sys.stderr)
    finished = [row for row in finished if row["group"] is not None]
    return _payload(finished)


def _jobs(task_root: Path) -> list[tuple[Path, str | None]]:
    """PDFs paired with a group id when the file name already decides it."""
    found: list[tuple[Path, str | None]] = []
    dane = task_root / "dane"
    if dane.is_dir():
        found.extend((pdf, None) for pdf in sorted(dane.rglob("*.pdf")))
    irregular = ROOT / "test_data" / "polish_synthetic_test_suite"
    if irregular.is_dir():
        for pdf in sorted(irregular.rglob("*.pdf")):
            found.append((pdf, _irregular_group(pdf)))
    scans = ROOT / "test_data" / "synthetic_scans"
    if scans.is_dir():
        found.extend((pdf, None) for pdf in sorted(scans.rglob("*.pdf")))
    return found


def _irregular_group(pdf: Path) -> str | None:
    stem = pdf.stem.lower()
    if "latw" in stem:
        return "irregular_easy"
    if "sred" in stem:
        return "irregular_mid"
    if "trud" in stem:
        return "irregular_hard"
    return None


def _group_after_score(pdf: Path, row: dict) -> str | None:
    if "synthetic_scans" in pdf.parts:
        return {
            "odwolanie": "synth_odwolanie",
            "pelnomocnictwo": "synth_pelnomocnictwo",
            "przelew": "synth_przelew",
            "negative": "synth_negative",
        }.get(row["type"])
    if "dane" in pdf.parts:
        return {"text": "uzp_text", "scan": "uzp_scan", "negative": "uzp_negative"}.get(row["split"])
    return None


def _install_need_markers(llm_extractor, vision_fill) -> None:
    """A cached reply never increments the call counter, but the document still asked."""
    cached_json = llm_extractor._cached_json
    cached_reply = vision_fill._cached_reply

    def mark_json(*args, **kwargs):
        _NEEDED.hit = True
        return cached_json(*args, **kwargs)

    def mark_reply(*args, **kwargs):
        _NEEDED.hit = True
        return cached_reply(*args, **kwargs)

    llm_extractor._cached_json = mark_json
    vision_fill._cached_reply = mark_reply


def _payload(rows: list[dict]) -> dict:
    labels = dict(GROUPS)
    groups = []
    for key, _label in GROUPS:
        chosen = [row for row in rows if row["group"] == key]
        if not chosen:
            continue
        packed = _pack(chosen)
        needed = sum(1 for row in chosen if row["llm"])
        groups.append({
            "id": key,
            "label": labels[key],
            "n": packed["n"],
            "precision": packed["precision"],
            "recall": packed["recall"],
            "f1": packed["f1"],
            "seconds_per_document": round(sum(row["seconds"] for row in chosen) / len(chosen), 2),
            "llm_percent": round(100 * needed / len(chosen), 1),
        })
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        for item in row["mismatches"]:
            counts[re.sub(r"\[\d+\]", "[]", item["field"])] += 1
    weakest = [
        {"field": field, "misses": count}
        for field, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    return {
        "mode": "bielik",
        "cache": "on",
        "scoring": "field exact match, same totals as backend/scripts/evaluate.py",
        "groups": groups,
        "weakest_fields": weakest,
    }


def _pack(selected: list[dict]) -> dict:
    """Same precision, recall and F1 as evaluate._summarise."""
    tp = sum(row["tp"] for row in selected)
    fp = sum(row["fp"] for row in selected)
    fn = sum(row["fn"] for row in selected)
    if tp == fp == fn == 0:
        precision = recall = f1 = 1.0 if selected else 0.0
    else:
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "n": len(selected),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }


def _print_table(payload: dict) -> None:
    header = ["group", "n", "P", "R", "F1", "s/doc", "LLM%"]
    table = [
        [
            group["label"],
            group["n"],
            _comma(group["precision"], 3),
            _comma(group["recall"], 3),
            _comma(group["f1"], 3),
            _comma(group["seconds_per_document"], 2),
            f"{_comma(group['llm_percent'], 1)}%",
        ]
        for group in payload["groups"]
    ]
    rendered = [[str(cell) for cell in row] for row in table]
    widths = [len(cell) for cell in header]
    for row in rendered:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    print("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(header)))
    print("  ".join("-" * width for width in widths))
    for row in rendered:
        print("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))
    print()
    print("weakest fields")
    for item in payload["weakest_fields"][:3]:
        print(f"  {item['misses']:4d}  {item['field']}")


def _draw(payload: dict) -> None:
    import matplotlib.pyplot as plt

    groups = payload["groups"]
    if not groups:
        raise SystemExit("No groups in stats_datasets.json")
    weakest = min(group["f1"] for group in groups)
    plt.rcParams["font.family"] = "Segoe UI"
    figure, axis = plt.subplots(figsize=(16, 9), dpi=120, facecolor="white")
    axis.set_facecolor("white")
    positions = list(range(len(groups)))
    colours = [RED if group["f1"] == weakest else NAVY for group in groups]
    scores = [group["f1"] for group in groups]
    axis.barh(positions, scores, color=colours, height=0.72, zorder=2)
    axis.set_yticks(positions)
    axis.set_yticklabels(
        [f"{group['label']}    n = {group['n']}" for group in groups],
        fontsize=18,
        color=NAVY,
    )
    axis.invert_yaxis()
    axis.set_xlim(0, 1.08)
    axis.set_ylim(len(groups) - 0.55, -0.65)
    axis.set_xticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.tick_params(axis="y", length=0, pad=8)
    for index, group in enumerate(groups):
        colour = RED if group["f1"] == weakest else NAVY
        score = group["f1"]
        if score >= 0.22:
            axis.text(score - 0.015, index, _comma(score, 2), ha="right", va="center", fontsize=20, color="white")
        else:
            axis.text(score + 0.02, index, _comma(score, 2), ha="left", va="center", fontsize=20, color=colour)
    axis.set_title("F1 według zestawu", loc="left", fontsize=28, color=NAVY, pad=12)
    figure.subplots_adjust(left=0.40, right=0.98, top=0.90, bottom=0.04)
    SLIDE.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(SLIDE, dpi=120, facecolor="white")
    plt.close(figure)
    print(SLIDE)


def _comma(value: float, digits: int) -> str:
    return f"{float(value):.{digits}f}".replace(".", ",")


def _load_evaluate():
    spec = importlib.util.spec_from_file_location("uzp_evaluate", ROOT / "backend" / "scripts" / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())
