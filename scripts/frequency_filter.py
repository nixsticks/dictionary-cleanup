#!/usr/bin/env python3
"""Filter ENABLE2K word list by frequency using Norvig's count_1w.txt data."""

import argparse
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "output"

BUCKETS = [
    ("0 (not found)", lambda f: f == 0),
    ("1–100", lambda f: 1 <= f <= 100),
    ("101–1,000", lambda f: 101 <= f <= 1000),
    ("1,001–10,000", lambda f: 1001 <= f <= 10000),
    ("10,001–100,000", lambda f: 10001 <= f <= 100000),
    ("100,001+", lambda f: f >= 100001),
]


def load_frequencies(path: Path) -> dict[str, int]:
    freqs = {}
    with open(path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                freqs[parts[0].lower()] = int(parts[1])
    return freqs


def load_wordlist(path: Path) -> list[str]:
    with open(path) as f:
        return [line.strip().lower() for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Filter words by frequency.")
    parser.add_argument(
        "--threshold", type=int, default=5000,
        help="Minimum frequency count to keep a word (default: 5000)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    args = parser.parse_args()

    freqs = load_frequencies(RAW_DIR / "count_1w.txt")
    words = load_wordlist(RAW_DIR / "enable2k.txt")

    # Look up frequency for each word
    word_freqs = {w: freqs.get(w, 0) for w in words}

    above = sorted(w for w, f in word_freqs.items() if f >= args.threshold)
    below = sorted(w for w, f in word_freqs.items() if f < args.threshold)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_DIR / "words_above_threshold.txt", "w") as f:
        f.write("\n".join(above) + "\n")

    with open(OUTPUT_DIR / "words_below_threshold.txt", "w") as f:
        f.write("\n".join(below) + "\n")

    # Build report
    rng = random.Random(args.seed)
    lines = []
    lines.append(f"Frequency Filter Report (threshold: {args.threshold:,})")
    lines.append("=" * 60)
    lines.append(f"Total words in ENABLE2K:        {len(words):,}")
    lines.append(f"Words above threshold:           {len(above):,}")
    lines.append(f"Words below threshold:           {len(below):,}")
    lines.append("")
    lines.append("Distribution by frequency bucket:")
    lines.append("-" * 60)

    for label, test in BUCKETS:
        bucket_words = [w for w, f in word_freqs.items() if test(f)]
        count = len(bucket_words)
        pct = 100 * count / len(words) if words else 0
        lines.append(f"  {label:20s}  {count:>7,} words  ({pct:5.1f}%)")
        sample = rng.sample(bucket_words, min(10, len(bucket_words)))
        sample_with_freq = sorted(
            [(w, word_freqs[w]) for w in sample], key=lambda x: -x[1]
        )
        for w, f in sample_with_freq:
            lines.append(f"      {w:25s} {f:>15,}")
        lines.append("")

    report = "\n".join(lines)

    with open(OUTPUT_DIR / "frequency_report.txt", "w") as f:
        f.write(report + "\n")

    print(report)


if __name__ == "__main__":
    main()
