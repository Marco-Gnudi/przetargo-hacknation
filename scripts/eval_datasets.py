"""Score every data set in deterministic mode and, with a typed key, hybrid mode.

    python scripts/eval_datasets.py
    python scripts/eval_datasets.py --chart-only

Hybrid mode ignores the LLM cache so the seconds are from this run.
The Mistral key is typed at startup and kept in memory only.
Writes reports/stats_datasets.json and docs/slides/datasets_comparison.png.
"""

from __future__ import annotations

import argparse
import contextvars
import importlib.util
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / "reports" / "stats_datasets.json"
SLIDE = ROOT / "docs" / "slides" / "datasets_comparison.png"

NAVY = "#1F2A44"
RED = "#C8102E"

GROUPS = (
    ("uzp_text", "UZP, tekst"),
    ("uzp_scan", "UZP, skany"),
    ("uzp_negative", "UZP, negatywne"),
    ("irregular_easy", "Nieregularne, łatwe"),
    ("irregular_hard", "Nieregularne, trudne"),
    ("synth_odwolanie", "Skany syntetyczne, odwołanie"),
    ("synth_pelnomocnictwo", "Skany syntetyczne, pełnomocnictwo"),
    ("synth_przelew", "Skany syntetyczne, przelew"),
    ("synth_negative", "Skany syntetyczne, negatywne"),
)

MODE_LABELS = {"regular": "Reguły", "mistral": "Reguły + Mistral"}
_NEEDED = threading.local()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chart-only", action="store_true", help="Redraw the slide from stats_datasets.json.")
    args = parser.parse_args(argv)
    if args.chart_only:
        _draw(json.loads(STATS.read_text(encoding="utf-8")))
        return 0

    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    evaluate = _load_evaluate()
    from ask_mistral import accept_key
    from odwolania.config import task_data_dir
    from odwolania.llm import set_skip_cache

    key_ok = accept_key()
    set_skip_cache(True)
    rules = evaluate.load_rules()
    jobs = _jobs(task_data_dir())
    if not jobs:
        print("No PDFs found.", file=sys.stderr)
        return 2

    payload = {
        "cache": "off",
        "scoring": "field exact match, same totals as backend/scripts/evaluate.py",
        "modes": {},
    }
    for mode in ("regular", "mistral"):
        if mode == "mistral" and not key_ok:
            continue
        print(f"scoring {len(jobs)} PDFs  mode {mode}  cache off", flush=True)
        payload["modes"][mode] = _run(evaluate, jobs, rules, mode)
        _write(payload)
        print(MODE_LABELS[mode])
        _print_table(payload["modes"][mode])
    try:
        _draw(payload)
    except ImportError:
        print("matplotlib is not installed in this interpreter; redraw with --chart-only.", file=sys.stderr)
    return 0


def _run(evaluate, jobs: list[tuple[Path, str | None]], rules: dict, mode: str) -> dict:
    from odwolania.llm import current_usage, start_usage
    from odwolania import llm_extractor
    import vision_fill

    _install_need_markers(llm_extractor, vision_fill)
    rows: list[dict | None] = [None] * len(jobs)

    def job(pdf: Path, group: str | None) -> dict:
        start_usage()
        _NEEDED.hit = False
        started = time.perf_counter()
        scored = evaluate._score_pdf(pdf, mode, rules)
        scored["seconds"] = time.perf_counter() - started
        scored["llm"] = bool(getattr(_NEEDED, "hit", False)) or int(current_usage().get("calls", 0)) > 0
        scored["group"] = group or _group_after_score(pdf, scored)
        return scored

    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for index, (pdf, group) in enumerate(jobs):
            ctx = contextvars.copy_context()
            futures[pool.submit(ctx.run, job, pdf, group)] = index
        for future in as_completed(futures):
            rows[futures[future]] = future.result()
            done += 1
            if done % 20 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}", flush=True)
    finished = [row for row in rows if row is not None and row["group"] is not None]
    skipped = len(rows) - len(finished)
    if skipped:
        print(f"skipped {skipped} PDF(s) with no group", file=sys.stderr)
    return _mode_payload(finished)


def _jobs(task_root: Path) -> list[tuple[Path, str | None]]:
    found: list[tuple[Path, str | None]] = []
    dane = task_root / "dane"
    if dane.is_dir():
        found.extend((pdf, None) for pdf in sorted(dane.rglob("*.pdf")))
    irregular = ROOT / "test_data" / "polish_synthetic_test_suite"
    if irregular.is_dir():
        for pdf in sorted(irregular.rglob("*.pdf")):
            if "archive" in pdf.parts:
                continue
            found.append((pdf, _irregular_group(pdf)))
    scans = ROOT / "test_data" / "synthetic_scans"
    if scans.is_dir():
        found.extend((pdf, None) for pdf in sorted(scans.rglob("*.pdf")))
    return found


def _irregular_group(pdf: Path) -> str | None:
    stem = pdf.stem.lower()
    if "latw" in stem:
        return "irregular_easy"
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
    if getattr(llm_extractor._cached_json, "_przetargo_marked", False):
        return
    cached_json = llm_extractor._cached_json
    cached_reply = vision_fill._cached_reply

    def mark_json(*args, **kwargs):
        _NEEDED.hit = True
        return cached_json(*args, **kwargs)

    def mark_reply(*args, **kwargs):
        _NEEDED.hit = True
        return cached_reply(*args, **kwargs)

    mark_json._przetargo_marked = True
    llm_extractor._cached_json = mark_json
    vision_fill._cached_reply = mark_reply


def _mode_payload(rows: list[dict]) -> dict:
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
    return {"label": None, "groups": groups}


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


def _write(payload: dict) -> None:
    for mode, body in payload["modes"].items():
        body["label"] = MODE_LABELS[mode]
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {STATS}")


def _print_table(mode_body: dict) -> None:
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
        for group in mode_body["groups"]
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


def _draw(payload: dict) -> None:
    import matplotlib.pyplot as plt

    modes = payload.get("modes") or {}
    series = [(key, MODE_LABELS[key], NAVY if key == "regular" else RED) for key in ("regular", "mistral") if key in modes]
    if not series:
        raise SystemExit("No modes in stats_datasets.json")
    present = []
    for key, label in GROUPS:
        if any(group["id"] == key for body in modes.values() for group in body["groups"]):
            present.append((key, label))
    plt.rcParams["font.family"] = "Segoe UI"
    figure, axis = plt.subplots(figsize=(16, 9), dpi=120, facecolor="white")
    axis.set_facecolor("white")
    count = len(series)
    height = 0.78 / count
    positions = list(range(len(present)))
    lookup = {
        mode: {group["id"]: group for group in modes[mode]["groups"]}
        for mode, _label, _color in series
    }
    for index, (mode, label, color) in enumerate(series):
        offset = (index - (count - 1) / 2) * height
        scores = [lookup[mode][key]["f1"] for key, _label in present]
        axis.barh([pos + offset for pos in positions], scores, height=height * 0.92, color=color, label=label, zorder=2)
        for pos, (key, _label) in enumerate(present):
            score = lookup[mode][key]["f1"]
            text = _comma(score, 2)
            if score >= 0.28:
                axis.text(score - 0.012, pos + offset, text, ha="right", va="center", fontsize=13, color="white")
            else:
                axis.text(score + 0.012, pos + offset, text, ha="left", va="center", fontsize=13, color=color)
    names = []
    for key, label in present:
        sample = next(lookup[mode][key] for mode, _label, _color in series if key in lookup[mode])
        names.append(f"{label}    n = {sample['n']}")
    axis.set_yticks(positions)
    axis.set_yticklabels(names, fontsize=16, color=NAVY)
    axis.invert_yaxis()
    axis.set_xlim(0, 1.12)
    axis.set_ylim(len(present) - 0.55, -0.62)
    axis.set_xticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)
    axis.tick_params(axis="y", length=0, pad=6)
    axis.legend(
        frameon=False, fontsize=16, loc="lower left", bbox_to_anchor=(0.0, 1.02), ncol=2, borderaxespad=0,
    )
    figure.subplots_adjust(left=0.36, right=0.98, top=0.90, bottom=0.04)
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
