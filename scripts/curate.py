#!/usr/bin/env python3
"""Config-driven dictionary curation pipeline.

Reads config/settings.yaml, applies built-in and custom filters,
and outputs a clean dictionary plus review/reject files.
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_frequencies(path: Path) -> dict[str, int]:
    freqs = {}
    with open(path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                freqs[parts[0].lower()] = int(parts[1])
    return freqs


def load_wordlist(path: Path) -> set[str]:
    with open(path) as f:
        return {line.strip().lower() for line in f if line.strip()}


def load_lines(path: Path) -> list[str]:
    """Load non-empty, non-comment lines from a text file."""
    lines = []
    with open(path) as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line:
                lines.append(line)
    return lines


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Filter result tracking
# ---------------------------------------------------------------------------

class FilterResult:
    """Tracks what a single filter did."""

    def __init__(self, name: str, mode: str):
        self.name = name
        self.mode = mode
        self.acted: dict[str, str] = {}   # word -> reason

    def add(self, word: str, reason: str):
        self.acted[word] = reason

    @property
    def count(self) -> int:
        return len(self.acted)


# ---------------------------------------------------------------------------
# Built-in filters
# ---------------------------------------------------------------------------

def run_frequency_filter(words: set[str], freqs: dict[str, int],
                         cfg: dict, threshold: int) -> FilterResult:
    result = FilterResult("frequency", cfg["mode"])
    whitelist: set[str] = set()
    wl_path = cfg.get("whitelist")
    if wl_path:
        p = BASE_DIR / wl_path
        if p.exists():
            whitelist = load_wordlist(p)

    for w in sorted(words):
        if w in whitelist:
            continue
        freq = freqs.get(w, 0)
        if freq < threshold:
            result.add(w, f"frequency {freq:,} < threshold {threshold:,}")
    return result


def run_blocklist_filter(words: set[str], cfg: dict) -> FilterResult:
    result = FilterResult("blocklist", cfg["mode"])
    directory = BASE_DIR / cfg["directory"]
    if not directory.is_dir():
        return result

    blocked: set[str] = set()
    for txt in sorted(directory.glob("*.txt")):
        blocked |= load_wordlist(txt)

    for w in sorted(words):
        if w in blocked:
            result.add(w, f"in blocklist")
    return result


def run_uk_spelling_filter(words: set[str], cfg: dict) -> FilterResult:
    result = FilterResult("uk_spelling", cfg["mode"])
    pf = BASE_DIR / cfg["patterns_file"]
    if not pf.exists():
        return result

    uk_words: set[str] = set()
    with open(pf) as f:
        for line in f:
            line = line.strip()
            if "|" in line:
                uk, _us = line.split("|", 1)
                uk_words.add(uk.strip().lower())

    for w in sorted(words):
        if w in uk_words:
            result.add(w, "UK spelling variant")
    return result


def run_agent_nouns_filter(words: set[str], freqs: dict[str, int],
                           cfg: dict, threshold: int) -> FilterResult:
    result = FilterResult("agent_nouns", cfg["mode"])
    multiplier = cfg.get("frequency_multiplier", 3)
    cutoff = threshold * multiplier

    for w in sorted(words):
        if w.endswith("er") and len(w) >= 4:
            freq = freqs.get(w, 0)
            if freq < cutoff:
                result.add(w, f"-er noun, frequency {freq:,} < {cutoff:,}")
    return result


def run_dialect_filter(words: set[str], cfg: dict) -> FilterResult:
    result = FilterResult("dialect", cfg["mode"])
    pf = BASE_DIR / cfg["patterns_file"]
    if not pf.exists():
        return result

    patterns = []
    for line in load_lines(pf):
        patterns.append(re.compile(line))

    for w in sorted(words):
        for pat in patterns:
            if pat.fullmatch(w):
                result.add(w, f"matches dialect pattern /{pat.pattern}/")
                break
    return result


def run_scientific_filter(words: set[str], freqs: dict[str, int],
                          cfg: dict, threshold: int) -> FilterResult:
    result = FilterResult("scientific", cfg["mode"])
    multiplier = cfg.get("frequency_multiplier", 2)
    min_length = cfg.get("min_length", 14)
    cutoff = threshold * multiplier

    forms: list[str] = []
    ff = cfg.get("forms_file")
    if ff:
        p = BASE_DIR / ff
        if p.exists():
            forms = load_lines(p)

    prefixes = [f.lstrip("-") for f in forms if f.startswith("-") is False and f.endswith("-")]
    suffixes = [f.lstrip("-").rstrip("-") for f in forms if f.startswith("-")]
    # Re-parse: prefix ends with -, suffix starts with -
    prefixes = []
    suffixes = []
    for f in forms:
        f = f.strip()
        if f.endswith("-"):
            prefixes.append(f[:-1].lower())
        elif f.startswith("-"):
            suffixes.append(f[1:].lower())

    for w in sorted(words):
        if len(w) < min_length:
            continue
        freq = freqs.get(w, 0)
        if freq >= cutoff:
            continue
        for sfx in suffixes:
            if w.endswith(sfx):
                result.add(w, f"scientific suffix -{sfx}, frequency {freq:,} < {cutoff:,}")
                break
        if w in result.acted:
            continue
        for pfx in prefixes:
            if w.startswith(pfx):
                result.add(w, f"scientific prefix {pfx}-, frequency {freq:,} < {cutoff:,}")
                break
    return result


BUILTIN_RUNNERS = {
    "frequency": lambda words, freqs, cfg, thr, _all: run_frequency_filter(words, freqs, cfg, thr),
    "blocklist": lambda words, freqs, cfg, thr, _all: run_blocklist_filter(words, cfg),
    "uk_spelling": lambda words, freqs, cfg, thr, _all: run_uk_spelling_filter(words, cfg),
    "agent_nouns": lambda words, freqs, cfg, thr, _all: run_agent_nouns_filter(words, freqs, cfg, thr),
    "dialect": lambda words, freqs, cfg, thr, _all: run_dialect_filter(words, cfg),
    "scientific": lambda words, freqs, cfg, thr, _all: run_scientific_filter(words, freqs, cfg, thr),
}


# ---------------------------------------------------------------------------
# Custom filter runner
# ---------------------------------------------------------------------------

def run_custom_filter(words: set[str], freqs: dict[str, int],
                      filt: dict, threshold: int, all_words: set[str]) -> FilterResult:
    name = filt["name"]
    mode = filt.get("mode", "flag")
    ftype = filt["type"]
    result = FilterResult(name, mode)

    if ftype == "blocklist":
        wf = BASE_DIR / filt["words_file"]
        if not wf.exists():
            return result
        blocked = load_wordlist(wf)
        for w in sorted(words):
            if w in blocked:
                result.add(w, "custom blocklist match")

    elif ftype == "pattern":
        patterns = [re.compile(p) for p in filt.get("patterns", [])]
        exclude = set(filt.get("exclude", []))
        for w in sorted(words):
            if w in exclude:
                continue
            for pat in patterns:
                if pat.fullmatch(w):
                    result.add(w, f"matches pattern /{pat.pattern}/")
                    break

    elif ftype == "frequency_gate":
        if "max_frequency" in filt:
            cutoff = filt["max_frequency"]
        else:
            cutoff = threshold * filt.get("frequency_multiplier", 1)
        patterns = [re.compile(p) for p in filt.get("patterns", [])]
        for w in sorted(words):
            freq = freqs.get(w, 0)
            if freq >= cutoff:
                continue
            if patterns:
                if not any(p.fullmatch(w) for p in patterns):
                    continue
            result.add(w, f"frequency {freq:,} < {cutoff:,}")

    elif ftype == "suffix":
        suffix = filt["suffix"]
        require_base = filt.get("require_base_in_list", False)
        multiplier = filt.get("frequency_multiplier")
        cutoff = threshold * multiplier if multiplier else None
        for w in sorted(words):
            if not w.endswith(suffix):
                continue
            base = w[: -len(suffix)]
            if require_base and base not in all_words:
                continue
            if cutoff is not None:
                freq = freqs.get(w, 0)
                if freq >= cutoff:
                    continue
            result.add(w, f"suffix -{suffix}" + (f", base '{base}' in list" if require_base else ""))

    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Config-driven dictionary curation.")
    parser.add_argument("--config", type=str, default="config/settings.yaml",
                        help="Path to settings YAML (default: config/settings.yaml)")
    parser.add_argument("--threshold", type=int, default=None,
                        help="Override frequency_threshold from config")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print filter actions without writing output files")
    args = parser.parse_args()

    config = load_config(BASE_DIR / args.config)
    threshold = args.threshold if args.threshold is not None else config["frequency_threshold"]

    # Load data
    freqs = load_frequencies(BASE_DIR / config["frequency_data"])
    all_words = load_wordlist(BASE_DIR / config["source_dictionary"])
    remaining = set(all_words)

    output_dir = BASE_DIR / config["output_dir"]
    review_dir = BASE_DIR / config["review_dir"]

    results: list[FilterResult] = []
    total_input = len(all_words)

    # --- Run built-in filters in config order ---
    for fname, fcfg in config.get("filters", {}).items():
        if not fcfg.get("enabled", True):
            continue
        runner = BUILTIN_RUNNERS.get(fname)
        if not runner:
            print(f"Warning: unknown built-in filter '{fname}', skipping", file=sys.stderr)
            continue

        res = runner(remaining, freqs, fcfg, threshold, all_words)
        results.append(res)

        if res.mode == "reject":
            remaining -= set(res.acted.keys())
        # flag mode: words stay in remaining (they still appear in clean output
        # unless also rejected by another filter)

    # --- Run custom filters ---
    custom_dir = BASE_DIR / config.get("custom_filters_dir", "config/custom_filters")
    if custom_dir.is_dir():
        for yf in sorted(custom_dir.glob("*.yaml")):
            filt = load_config(yf)
            if not filt:
                continue
            res = run_custom_filter(remaining, freqs, filt, threshold, all_words)
            results.append(res)
            if res.mode == "reject":
                remaining -= set(res.acted.keys())

    # --- Build report ---
    report_lines = []
    report_lines.append(f"Curation Report")
    report_lines.append(f"=" * 70)
    report_lines.append(f"Source:              {config['source_dictionary']}")
    report_lines.append(f"Frequency threshold: {threshold:,}")
    report_lines.append(f"Total input words:   {total_input:,}")
    report_lines.append(f"")

    total_rejected = 0
    total_flagged = 0

    report_lines.append(f"{'Filter':<20s} {'Mode':<8s} {'Acted':>8s} {'Remaining':>10s}")
    report_lines.append(f"{'-'*20} {'-'*8} {'-'*8} {'-'*10}")

    running_remaining = total_input
    for res in results:
        if res.mode == "reject":
            running_remaining -= res.count
            total_rejected += res.count
        else:
            total_flagged += res.count
        report_lines.append(
            f"{res.name:<20s} {res.mode:<8s} {res.count:>8,} {running_remaining:>10,}"
        )

    report_lines.append(f"")
    report_lines.append(f"{'Summary':=^70}")
    report_lines.append(f"Total rejected:      {total_rejected:,}")
    report_lines.append(f"Total flagged:       {total_flagged:,}")
    report_lines.append(f"Clean dictionary:    {len(remaining):,}")

    report = "\n".join(report_lines)
    print(report)

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return

    # --- Write output files ---
    output_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    # Clean dictionary
    with open(output_dir / "clean_dictionary.txt", "w") as f:
        f.write("\n".join(sorted(remaining)) + "\n")

    # Rejected file
    rejected_lines = []
    for res in results:
        if res.mode == "reject":
            for w, reason in sorted(res.acted.items()):
                rejected_lines.append(f"{w} | {res.name} | {reason}")
    with open(output_dir / "rejected.txt", "w") as f:
        f.write("\n".join(rejected_lines) + "\n")

    # Flagged files — per filter and combined
    all_flagged_lines = []
    for res in results:
        if res.mode == "flag" and res.count > 0:
            per_filter = []
            for w, reason in sorted(res.acted.items()):
                per_filter.append(w)
                all_flagged_lines.append(f"{w} | {res.name} | {reason}")
            with open(review_dir / f"flagged_{res.name}.txt", "w") as f:
                f.write("\n".join(per_filter) + "\n")

    with open(review_dir / "all_flagged.txt", "w") as f:
        f.write("\n".join(sorted(all_flagged_lines)) + "\n")

    # Report
    with open(output_dir / "curation_report.txt", "w") as f:
        f.write(report + "\n")


if __name__ == "__main__":
    main()
