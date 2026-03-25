#!/usr/bin/env python3
"""Assemble the final dictionary from curated outputs."""

import argparse
from pathlib import Path

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    with open(BASE_DIR / "config" / "settings.yaml") as f:
        return yaml.safe_load(f)


def load_words(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with open(path) as f:
        return {line.strip().lower() for line in f if line.strip()}


def main():
    parser = argparse.ArgumentParser(description="Assemble the final dictionary.")
    parser.add_argument("--add-words", type=str, action="append", default=[],
                        help="Path to a file of words to add (repeatable)")
    parser.add_argument("--remove-words", type=str, action="append", default=[],
                        help="Path to a file of words to remove (repeatable)")
    args = parser.parse_args()

    config = load_config()
    output_dir = BASE_DIR / config["output_dir"]
    review_dir = BASE_DIR / config["review_dir"]

    # Base: clean dictionary from curation pipeline
    clean_path = output_dir / "clean_dictionary.txt"
    if not clean_path.exists():
        print(f"Error: {clean_path} not found. Run curate.py first.")
        return
    base = load_words(clean_path)
    base_count = len(base)

    # Add reviewed-keep words
    keep_path = review_dir / "reviewed_keep.txt"
    reviewed_keep = load_words(keep_path)
    added_from_review = reviewed_keep - base
    base |= reviewed_keep

    # Add extra word files
    added_from_files: set[str] = set()
    for fp in args.add_words:
        p = Path(fp) if Path(fp).is_absolute() else BASE_DIR / fp
        new_words = load_words(p)
        added_from_files |= new_words - base
        base |= new_words

    # Remove word files
    removed_from_files: set[str] = set()
    for fp in args.remove_words:
        p = Path(fp) if Path(fp).is_absolute() else BASE_DIR / fp
        remove_words = load_words(p)
        removed_from_files = remove_words & base
        base -= remove_words

    # Sort, deduplicate, write
    final = sorted(base)
    out_path = output_dir / "FINAL_DICTIONARY.txt"
    with open(out_path, "w") as f:
        f.write("\n".join(final) + "\n")

    # Report
    print(f"Final Dictionary")
    print(f"{'=' * 45}")
    print(f"Base (clean_dictionary.txt):  {base_count:>8,}")
    print(f"Added from review:           {len(added_from_review):>8,}")
    print(f"Added from --add-words:      {len(added_from_files):>8,}")
    print(f"Removed from --remove-words: {len(removed_from_files):>8,}")
    print(f"{'─' * 45}")
    print(f"Total words:                 {len(final):>8,}")
    print(f"\nWritten to {out_path}")


if __name__ == "__main__":
    main()
