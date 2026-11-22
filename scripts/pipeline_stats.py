"""Measure the UZP set in deterministic mode and, with a typed key, hybrid mode.

    python scripts/pipeline_stats.py
    python scripts/pipeline_stats.py --chart-only

The Mistral key is typed at startup and kept in memory only. Hybrid mode does
not read the LLM cache. Writes reports/pipeline_stats.json and
docs/slides/pipeline_flow.png.
"""

from __future__ import annotations

import argparse
import contextvars
import importlib.util
import json
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / "reports" / "pipeline_stats.json"
SLIDE = ROOT / "docs" / "slides" / "pipeline_flow.png"

NAVY = "#1F2A44"
RED = "#C8102E"
BATCH = 150
# Scaleway list price for mistral-small-3.2-24b-instruct-2506, chat and vision.
# https://www.scaleway.com/en/pricing/model-as-a-service/
INPUT_EUR_PER_MILLION = 0.15
OUTPUT_EUR_PER_MILLION = 0.35
# NBP tabela A 226/A/NBP/2026, 2026-11-20. The free tier is not deducted.
EUR_PLN = 4.4559

_VISION = threading.local()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--chart-only", action="store_true")
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
    import vision_fill

    key_ok = accept_key()
    set_skip_cache(True)
    _install_vision_marker(vision_fill)
    dane = task_data_dir() / "dane"
    pdfs = sorted(dane.rglob("*.pdf"))
    if not pdfs:
        print(f"No PDFs in {dane}", file=sys.stderr)
        return 2
    payload = {
        "dataset": str(dane.relative_to(ROOT)).replace("\\", "/"),
        "documents": len(pdfs),
        "cache": "off",
        "price": {
            "provider": "Scaleway Generative APIs",
            "model": "mistral-small-3.2-24b-instruct-2506",
            "input_eur_per_million": INPUT_EUR_PER_MILLION,
            "output_eur_per_million": OUTPUT_EUR_PER_MILLION,
            "eur_pln": EUR_PLN,
            "eur_pln_table": "NBP 226/A/NBP/2026 z 2026-11-20",
            "free_tier": "not applied",
        },
        "modes": {},
    }
    for mode in ("regular", "bielik"):
        if mode == "bielik" and not key_ok:
            continue
        print(f"measuring {len(pdfs)} PDFs  mode {mode}  cache off", flush=True)
        payload["modes"][mode] = _measure(evaluate, pdfs, mode)
        _write(payload)
        _print_mode(mode, payload["modes"][mode])
    try:
        _draw(payload)
    except ImportError:
        print("matplotlib is not installed in this interpreter; redraw with --chart-only.", file=sys.stderr)
    return 0


def _measure(evaluate, pdfs: list[Path], mode: str) -> dict:
    from engine import extract_document
    from odwolania.llm import LLMAuthError, start_usage
    from pdf_reader import _MIN_CHARS_PER_PAGE, read_pdf

    rows: list[dict | None] = [None] * len(pdfs)

    def job(pdf: Path) -> dict:
        start_usage()
        _VISION.paths = []
        started = time.perf_counter()
        try:
            item = extract_document(pdf, pdf.name, mode)
        except LLMAuthError:
            raise
        seconds = time.perf_counter() - started
        document = read_pdf(pdf)
        kind = _read_kind(document, _MIN_CHARS_PER_PAGE)
        payload = item.get("result") if isinstance(item.get("result"), dict) else {}
        sources = item.get("sources") if isinstance(item.get("sources"), dict) else {}
        fields = _fields(payload, sources, list(_VISION.paths))
        tp, fp, fn = _score(evaluate, pdf, payload)
        usage = item.get("llm") if isinstance(item.get("llm"), dict) else {}
        return {
            "kind": kind,
            "type": item.get("document_type") or "unknown",
            "seconds": seconds,
            "ocr_seconds": float(document.ocr_seconds or 0.0),
            "fields": fields,
            "vision": bool(_VISION.paths),
            "calls": int(usage.get("calls") or 0),
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    done = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}
        for index, pdf in enumerate(pdfs):
            ctx = contextvars.copy_context()
            futures[pool.submit(ctx.run, job, pdf)] = index
        for future in as_completed(futures):
            rows[futures[future]] = future.result()
            done += 1
            if done % 20 == 0 or done == len(pdfs):
                print(f"  {done}/{len(pdfs)}", flush=True)
    finished = [row for row in rows if row is not None]
    return _totals(finished)


def _read_kind(document, minimum: int) -> str:
    """Split mixed reads. The reader stores them as text_source 'ocr'."""
    pages = list(document.pages or [])
    if not pages:
        return document.text_source if document.text_source in ("text", "ocr") else "text"
    short = sum(1 for page in pages if int(page.get("char_count") or 0) < minimum)
    if short == 0:
        return "text"
    if short == len(pages):
        return "ocr"
    return "mixed"


def _install_vision_marker(vision_fill) -> None:
    if getattr(vision_fill.merge_vision, "_przetargo_marked", False):
        return
    original = vision_fill.merge_vision

    def marked(base, incoming):
        before = _leaves(base)
        result = original(base, incoming)
        bucket = getattr(_VISION, "paths", None)
        if bucket is not None:
            after = _leaves(result)
            for path, value in after.items():
                if value in (None, "") or before.get(path) == value:
                    continue
                bucket.append(path)
        return result

    marked._przetargo_marked = True
    vision_fill.merge_vision = marked


def _fields(payload: dict, sources: dict, vision_paths: list[str]) -> dict:
    filled = {path: value for path, value in _leaves(payload).items() if value not in (None, "")}
    vision = set(vision_paths)
    counts = {"rules": 0, "mistral": 0, "vision": 0}
    for path in filled:
        if path in vision:
            counts["vision"] += 1
        elif sources.get(path) == "llm":
            counts["mistral"] += 1
        else:
            counts["rules"] += 1
    return counts


def _leaves(value, prefix=""):
    found = {}
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            found.update(_leaves(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.update(_leaves(item, f"{prefix}[{index}]"))
    elif prefix:
        found[prefix] = value
    return found


def _score(evaluate, pdf: Path, payload: dict) -> tuple[int, int, int]:
    gold_path = evaluate._gold_path(pdf)
    gold = {}
    if gold_path.is_file():
        loaded = json.loads(gold_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            gold = loaded
    expected = dict(evaluate._leaves(gold))
    got = dict(evaluate._leaves(payload))
    tp = fp = fn = 0
    for path in list(expected) + [path for path in got if path not in expected]:
        left, right = expected.get(path), got.get(path)
        match = evaluate._same(path, left, right)
        if match and evaluate._present(left):
            tp += 1
        elif not match:
            if evaluate._present(left):
                fn += 1
            if evaluate._present(right):
                fp += 1
    return tp, fp, fn


def _totals(rows: list[dict]) -> dict:
    n = len(rows)
    kinds = Counter(row["kind"] for row in rows)
    types = Counter(row["type"] or "unknown" for row in rows)
    fields = Counter()
    for row in rows:
        fields.update(row["fields"])
    packed = _pack(rows)
    calls = sum(row["calls"] for row in rows)
    prompt = sum(row["prompt_tokens"] for row in rows)
    completion = sum(row["completion_tokens"] for row in rows)
    scale = BATCH / n if n else 0
    prompt_150 = prompt * scale
    completion_150 = completion * scale
    eur = prompt_150 / 1_000_000 * INPUT_EUR_PER_MILLION + completion_150 / 1_000_000 * OUTPUT_EUR_PER_MILLION
    return {
        "n": n,
        "f1": packed["f1"],
        "precision": packed["precision"],
        "recall": packed["recall"],
        "text_source_percent": _percent(kinds, ("text", "ocr", "mixed")),
        "type_percent": _percent(types, ("odwolanie", "pelnomocnictwo", "przelew", "unknown")),
        "field_percent": _percent(fields, ("rules", "mistral", "vision")),
        "vision_percent": round(100 * sum(1 for row in rows if row["vision"]) / n, 1) if n else 0.0,
        "seconds_per_document": {
            "all": _mean(rows, None),
            "text": _mean(rows, "text"),
            "scan": _mean(rows, ("ocr", "mixed")),
            "ocr": _mean(rows, "ocr"),
            "mixed": _mean(rows, "mixed"),
        },
        "per_150": {
            "mistral_calls": round(calls * scale, 1),
            "prompt_tokens": round(prompt_150),
            "completion_tokens": round(completion_150),
            "cost_eur": round(eur, 4),
            "cost_pln": round(eur * EUR_PLN, 2),
        },
    }


def _percent(counts: Counter, keys: tuple[str, ...]) -> dict:
    total = sum(counts.values())
    shares = {}
    for key in keys:
        shares[key] = round(100 * counts.get(key, 0) / total, 1) if total else 0.0
    for key, value in counts.items():
        if key not in shares:
            shares[key] = round(100 * value / total, 1) if total else 0.0
    return shares


def _mean(rows: list[dict], kinds) -> float | None:
    if kinds is None:
        chosen = rows
    elif isinstance(kinds, str):
        chosen = [row for row in rows if row["kind"] == kinds]
    else:
        chosen = [row for row in rows if row["kind"] in kinds]
    if not chosen:
        return None
    return round(sum(row["seconds"] for row in chosen) / len(chosen), 2)


def _pack(rows: list[dict]) -> dict:
    tp = sum(row["tp"] for row in rows)
    fp = sum(row["fp"] for row in rows)
    fn = sum(row["fn"] for row in rows)
    if tp == fp == fn == 0:
        precision = recall = f1 = 1.0 if rows else 0.0
    else:
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def _write(payload: dict) -> None:
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {STATS}")


def _print_mode(mode: str, body: dict) -> None:
    name = "Reguły" if mode == "regular" else "Reguły + Mistral"
    print(name)
    print(
        f"  F1 {_comma(body['f1'], 3)}   P {_comma(body['precision'], 3)}   "
        f"R {_comma(body['recall'], 3)}   n {body['n']}"
    )
    source = body["text_source_percent"]
    print(
        f"  tekst {_comma(source.get('text', 0), 1)}%   "
        f"OCR {_comma(source.get('ocr', 0), 1)}%   "
        f"mieszane {_comma(source.get('mixed', 0), 1)}%"
    )
    fields = body["field_percent"]
    print(
        f"  pola  reguły {_comma(fields.get('rules', 0), 1)}%   "
        f"Mistral {_comma(fields.get('mistral', 0), 1)}%   "
        f"vision {_comma(fields.get('vision', 0), 1)}%   "
        f"dokumenty z vision {_comma(body['vision_percent'], 1)}%"
    )
    seconds = body["seconds_per_document"]
    print(f"  czas  tekst {_seconds(seconds.get('text'))}   skan {_seconds(seconds.get('scan'))}")
    batch = body["per_150"]
    print(
        f"  na 150  wywołania {batch['mistral_calls']}   "
        f"tokeny {batch['prompt_tokens']}+{batch['completion_tokens']}   "
        f"{_comma(batch['cost_pln'], 2)} zł"
    )
    print()


def _draw(payload: dict) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    regular = (payload.get("modes") or {}).get("regular")
    hybrid = (payload.get("modes") or {}).get("bielik")
    source = (regular or hybrid or {}).get("text_source_percent") or {}
    types = (regular or hybrid or {}).get("type_percent") or {}
    rules = regular or {}
    plt.rcParams["font.family"] = "Segoe UI"
    figure, axis = plt.subplots(figsize=(16, 9), dpi=120, facecolor="white")
    axis.set_xlim(0, 160)
    axis.set_ylim(0, 90)
    axis.axis("off")
    figure.subplots_adjust(0, 0, 1, 1)

    def box(x, y, w, h, lines, edge, dashed=False):
        axis.add_patch(FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.3,rounding_size=1.1",
            linewidth=2.4,
            edgecolor=edge,
            facecolor="white",
            linestyle=(0, (5, 3)) if dashed else "solid",
        ))
        cursor = y + h - 2.6
        for index, line in enumerate(lines):
            axis.text(
                x + w / 2, cursor, line,
                ha="center", va="top", fontsize=15 if index == 0 else 12,
                color=edge, fontweight="bold" if index == 0 else "regular",
            )
            cursor -= 3.35

    def arrow(x1, y1, x2, y2, color=NAVY, dashed=False):
        axis.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2),
            arrowstyle="-|>", mutation_scale=18, linewidth=2.2, color=color,
            linestyle=(0, (5, 3)) if dashed else "solid",
        ))

    read_lines = [
        "Odczyt tekstu",
        "PyMuPDF",
        "strona < 50 znaków → OCR pol",
        "obrót i deskew",
        f"{_comma(source.get('text', 0), 1)}% z warstwy tekstu",
        f"{_comma(source.get('ocr', 0), 1)}% przez OCR",
        f"{_comma(source.get('mixed', 0), 1)}% mieszane",
    ]
    class_lines = [
        "Klasyfikacja",
        "po treści dokumentu",
        "inny dokument → {}",
        f"odwołanie {_comma(types.get('odwolanie', 0), 1)}%",
        f"pełnomocnictwo {_comma(types.get('pelnomocnictwo', 0), 1)}%",
        f"przelew {_comma(types.get('przelew', 0), 1)}%",
        f"inne {_comma(types.get('unknown', 0), 1)}%",
    ]
    rule_seconds = (rules.get("seconds_per_document") or {})
    rule_fields = (rules.get("field_percent") or {})
    rule_lines = [
        "Reguły",
        "ekstraktory, daty, kwoty",
        "NIP, REGON, PESEL, NRB",
        f"{_comma(rule_fields.get('rules', 0), 1)}% pól z reguł",
        f"tekst {_seconds(rule_seconds.get('text'))}",
        f"skan {_seconds(rule_seconds.get('scan'))}",
        f"F1 {_comma(rules.get('f1', 0), 2)}" if rules else "F1 —",
    ]
    json_lines = ["JSON", "schemat UZP", "1 plik na PDF"]
    if rules:
        json_lines.append(f"F1 reguły {_comma(rules.get('f1', 0), 2)}")
    if hybrid:
        json_lines.append(f"F1 + Mistral {_comma(hybrid.get('f1', 0), 2)}")
    box(2, 46, 16, 22, ["PDF"], NAVY)
    box(24, 40, 40, 40, read_lines, NAVY)
    box(70, 40, 32, 40, class_lines, NAVY)
    box(108, 40, 28, 40, rule_lines, NAVY)
    box(140, 44, 18, 34, json_lines, NAVY)
    arrow(18.4, 58, 23.6, 58)
    arrow(64.4, 58, 69.6, 58)
    arrow(102.4, 58, 107.6, 58)
    arrow(136.4, 58, 139.6, 58)

    hybrid_fields = (hybrid or {}).get("field_percent") or {}
    hybrid_seconds = (hybrid or {}).get("seconds_per_document") or {}
    batch = (hybrid or {}).get("per_150") or {}
    if hybrid:
        mistral_lines = [
            "Mistral Small",
            "tylko puste pola",
            "wartości reguł zostają",
            f"{_comma(hybrid_fields.get('mistral', 0), 1)}% pól",
        ]
        vision_lines = [
            "Vision",
            "tylko słabe skany",
            f"{_comma(hybrid_fields.get('vision', 0), 1)}% pól",
            f"{_comma(hybrid.get('vision_percent', 0), 1)}% dokumentów",
        ]
        footer = (
            f"na 150 dok.: {batch.get('mistral_calls', 0)} wywołań, "
            f"{_comma(batch.get('cost_pln', 0), 2)} zł"
        )
        timing = f"tekst {_seconds(hybrid_seconds.get('text'))} · skan {_seconds(hybrid_seconds.get('scan'))}"
    else:
        mistral_lines = ["Mistral Small", "tylko puste pola", "wartości reguł zostają", "nie zmierzono"]
        vision_lines = ["Vision", "tylko słabe skany", "nie zmierzono"]
        footer = "brak klucza — tryb nie zmierzony"
        timing = ""
    box(70, 3, 86, 32, ["Tryb Mistral (z kluczem API)"], RED, dashed=True)
    axis.text(92, 28.2, mistral_lines[0], ha="center", va="top", fontsize=14, color=RED, fontweight="bold")
    for index, line in enumerate(mistral_lines[1:], start=1):
        axis.text(92, 28.2 - index * 3.3, line, ha="center", va="top", fontsize=12, color=RED)
    axis.text(132, 28.2, vision_lines[0], ha="center", va="top", fontsize=14, color=RED, fontweight="bold")
    for index, line in enumerate(vision_lines[1:], start=1):
        axis.text(132, 28.2 - index * 3.3, line, ha="center", va="top", fontsize=12, color=RED)
    axis.text(113, 6.2, footer, ha="center", va="bottom", fontsize=12, color=RED)
    if timing:
        axis.text(113, 9.4, timing, ha="center", va="bottom", fontsize=12, color=RED)
    arrow(149, 35.2, 149, 43.6, color=RED, dashed=True)

    SLIDE.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(SLIDE, dpi=120, facecolor="white")
    plt.close(figure)
    print(SLIDE)


def _seconds(value) -> str:
    if value is None:
        return "—"
    return f"{_comma(value, 2)} s"


def _comma(value: float, digits: int) -> str:
    return f"{float(value):.{digits}f}".replace(".", ",")


def _load_evaluate():
    spec = importlib.util.spec_from_file_location("uzp_evaluate", ROOT / "backend" / "scripts" / "evaluate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())
