#!/usr/bin/env python3
"""Interactive terminal tool for manual review of flagged words."""

import argparse
import json
import sys
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(BASE_DIR / "config" / "settings.yaml") as f:
        return yaml.safe_load(f)


def load_frequencies(path: Path) -> dict[str, int]:
    freqs = {}
    with open(path) as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                freqs[parts[0].lower()] = int(parts[1])
    return freqs


def load_wordlist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with open(path) as f:
        return {line.strip().lower() for line in f if line.strip()}


def load_flagged(path: Path) -> list[dict]:
    """Parse all_flagged.txt into structured records."""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                entries.append({
                    "word": parts[0],
                    "filter": parts[1],
                    "reason": parts[2],
                })
    return entries


def context_hint(entry: dict, dictionary: set[str]) -> str:
    """Generate a brief context hint for the word."""
    word = entry["word"]
    filt = entry["filter"]

    if filt == "agent_nouns" and word.endswith("er"):
        base = word[:-2]
        # Check verb forms
        candidates = [base, base + "e"]
        found = [c for c in candidates if c in dictionary]
        if found:
            return f"base verb: {found[0]}"

    if filt == "dialect":
        # For -ae endings, check if a version without trailing 'e' or with -a exists
        if word.endswith("ae"):
            for alt in [word[:-1], word[:-2] + "a"]:
                if alt in dictionary:
                    return f"cf. {alt}"
        # For -it endings, check -ed equivalent
        if word.endswith("it"):
            for alt in [word[:-2] + "ed", word[:-1] + "ted"]:
                if alt in dictionary:
                    return f"cf. {alt}"
        # For wh- words, check w- equivalent
        if word.startswith("wh"):
            alt = "w" + word[2:]
            if alt in dictionary:
                return f"cf. {alt}"

    return ""


def display_batch(batch: list[dict], freqs: dict[str, int],
                  dictionary: set[str], offset: int):
    """Print a batch of words for review."""
    print(f"\n{'─' * 70}")
    print(f"  #   {'Word':<25s} {'Freq':>10s}  {'Filter':<15s} Context")
    print(f"{'─' * 70}")
    for i, entry in enumerate(batch):
        num = offset + i + 1
        word = entry["word"]
        freq = freqs.get(word, 0)
        freq_str = f"{freq:,}" if freq > 0 else "—"
        hint = context_hint(entry, dictionary)
        print(f"  {num:<3d} {word:<25s} {freq_str:>10s}  {entry['filter']:<15s} {hint}")
    print(f"{'─' * 70}")


def save_progress(progress_path: Path, decisions: dict[str, str],
                  current_idx: int):
    data = {
        "current_index": current_idx,
        "decisions": decisions,
    }
    with open(progress_path, "w") as f:
        json.dump(data, f, indent=2)


def load_progress(progress_path: Path) -> tuple[dict[str, str], int]:
    if not progress_path.exists():
        return {}, 0
    with open(progress_path) as f:
        data = json.load(f)
    return data.get("decisions", {}), data.get("current_index", 0)


def write_results(review_dir: Path, decisions: dict[str, str]):
    keep = sorted(w for w, d in decisions.items() if d == "keep")
    reject = sorted(w for w, d in decisions.items() if d == "reject")

    with open(review_dir / "reviewed_keep.txt", "w") as f:
        f.write("\n".join(keep) + "\n" if keep else "")
    with open(review_dir / "reviewed_reject.txt", "w") as f:
        f.write("\n".join(reject) + "\n" if reject else "")

    print(f"\nResults: {len(keep)} kept, {len(reject)} rejected")
    print(f"  {review_dir / 'reviewed_keep.txt'}")
    print(f"  {review_dir / 'reviewed_reject.txt'}")


def main():
    parser = argparse.ArgumentParser(description="Interactive review of flagged words.")
    parser.add_argument("--batch-size", type=int, default=20,
                        help="Words per batch (default: 20)")
    parser.add_argument("--filter-name", type=str, default=None,
                        help="Review only words from this filter")
    parser.add_argument("--reset", action="store_true",
                        help="Discard saved progress and start over")
    args = parser.parse_args()

    config = load_config()
    review_dir = BASE_DIR / config["review_dir"]
    flagged_path = review_dir / "all_flagged.txt"
    progress_path = review_dir / "review_progress.json"

    if not flagged_path.exists():
        print(f"No flagged words found at {flagged_path}")
        print("Run curate.py first.")
        sys.exit(1)

    # Load data
    freqs = load_frequencies(BASE_DIR / config["frequency_data"])
    dictionary = load_wordlist(BASE_DIR / config["source_dictionary"])
    entries = load_flagged(flagged_path)

    if args.filter_name:
        entries = [e for e in entries if e["filter"] == args.filter_name]
        if not entries:
            print(f"No flagged words for filter '{args.filter_name}'")
            sys.exit(1)
        print(f"Reviewing {len(entries)} words from filter: {args.filter_name}")

    # Load or reset progress
    if args.reset and progress_path.exists():
        progress_path.unlink()
    decisions, start_idx = load_progress(progress_path)

    # Filter out already-decided entries
    pending = [(i, e) for i, e in enumerate(entries) if e["word"] not in decisions]

    if not pending:
        print("All words have been reviewed!")
        write_results(review_dir, decisions)
        return

    total = len(entries)
    reviewed = len(decisions)
    print(f"\n{total} flagged words total, {reviewed} already reviewed, {len(pending)} remaining")
    print(f"\nCommands per batch:")
    print(f"  k          — keep all")
    print(f"  r          — reject all")
    print(f"  1,3,5      — keep those numbers (reject the rest)")
    print(f"  s          — skip batch (decide later)")
    print(f"  q          — quit and save progress\n")

    bs = args.batch_size
    batch_start = 0

    while batch_start < len(pending):
        batch_entries = [e for _, e in pending[batch_start:batch_start + bs]]
        if not batch_entries:
            break

        display_batch(batch_entries, freqs, dictionary, batch_start)

        reviewed_count = len(decisions)
        remaining_count = len(pending) - batch_start
        print(f"  [{reviewed_count} reviewed / {remaining_count} remaining]")

        try:
            response = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            response = "q"

        if response == "q":
            save_progress(progress_path, decisions, batch_start)
            write_results(review_dir, decisions)
            print("Progress saved. Run again to resume.")
            return

        if response == "s":
            batch_start += bs
            continue

        if response == "k":
            for entry in batch_entries:
                decisions[entry["word"]] = "keep"
            batch_start += bs
            continue

        if response == "r":
            for entry in batch_entries:
                decisions[entry["word"]] = "reject"
            batch_start += bs
            continue

        # Parse comma-separated keep numbers
        try:
            keep_nums = {int(n.strip()) for n in response.split(",")}
            for i, entry in enumerate(batch_entries):
                num = batch_start + i + 1
                if num in keep_nums:
                    decisions[entry["word"]] = "keep"
                else:
                    decisions[entry["word"]] = "reject"
            batch_start += bs
        except ValueError:
            print("  Invalid input. Try again.")
            continue

    # All done
    save_progress(progress_path, decisions, len(pending))
    write_results(review_dir, decisions)
    print("Review complete!")


if __name__ == "__main__":
    main()
