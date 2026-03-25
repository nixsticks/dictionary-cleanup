#!/usr/bin/env python3
"""Quality checks on a word list file."""

from __future__ import annotations

import argparse
import random
import re
import statistics
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


def load_words(path: Path) -> list[str]:
    with open(path) as f:
        return [line.strip().lower() for line in f if line.strip()]


def load_lines(path: Path) -> list[str]:
    lines = []
    if not path.exists():
        return lines
    with open(path) as f:
        for line in f:
            line = line.split("#")[0].strip()
            if line:
                lines.append(line)
    return lines


# ---------------------------------------------------------------------------
# Built-in coverage list: 500 common English words
# ---------------------------------------------------------------------------

COMMON_WORDS = [
    # Function words
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "because",
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "about",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might",
    "shall", "can", "must", "not", "no", "yes",
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her",
    "us", "them", "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those", "who", "what", "which", "where",
    "when", "how", "why", "all", "each", "every", "both", "few", "more",
    "most", "some", "any", "many", "much", "other", "another",
    # Common nouns
    "time", "year", "people", "way", "day", "man", "woman", "child",
    "world", "life", "hand", "part", "place", "case", "week", "company",
    "system", "program", "question", "work", "government", "number",
    "night", "point", "home", "water", "room", "mother", "area", "money",
    "story", "fact", "month", "lot", "right", "study", "book", "eye",
    "job", "word", "business", "issue", "side", "kind", "head", "house",
    "service", "friend", "father", "power", "hour", "game", "line",
    "end", "members", "family", "car", "city", "community", "name",
    "president", "team", "minute", "idea", "body", "information", "back",
    "parent", "face", "others", "level", "office", "door", "health",
    "person", "art", "war", "history", "party", "result", "change",
    "morning", "reason", "research", "girl", "guy", "moment", "air",
    "teacher", "force", "education", "food", "music", "dog", "cat",
    "bird", "fish", "tree", "sun", "moon", "star", "fire", "earth",
    "sea", "river", "mountain", "road", "street", "school", "church",
    "table", "bed", "chair", "window", "wall", "floor", "garden",
    "king", "queen", "land", "law", "death", "love", "blood", "song",
    # Common verbs
    "say", "get", "make", "go", "know", "take", "see", "come", "think",
    "look", "want", "give", "use", "find", "tell", "ask", "work", "seem",
    "feel", "try", "leave", "call", "need", "become", "keep", "let",
    "begin", "show", "hear", "play", "run", "move", "live", "believe",
    "hold", "bring", "happen", "write", "provide", "sit", "stand",
    "lose", "pay", "meet", "include", "continue", "set", "learn",
    "lead", "understand", "watch", "follow", "stop", "create", "speak",
    "read", "allow", "add", "spend", "grow", "open", "walk", "win",
    "offer", "remember", "consider", "appear", "buy", "wait", "serve",
    "die", "send", "expect", "build", "stay", "fall", "cut", "reach",
    "kill", "remain", "eat", "drink", "sleep", "sing", "dance", "fight",
    "fly", "drive", "ride", "draw", "break", "pull", "push", "carry",
    "pick", "throw", "catch", "climb", "jump", "hang", "burn", "wash",
    "cook", "smile", "laugh", "cry", "talk", "turn", "close", "help",
    # Common adjectives
    "good", "new", "first", "last", "long", "great", "little", "own",
    "old", "big", "high", "different", "small", "large", "next", "early",
    "young", "important", "public", "bad", "same", "able", "free",
    "right", "still", "best", "better", "true", "full", "real",
    "hard", "strong", "whole", "sure", "clear", "simple", "easy",
    "cold", "hot", "warm", "dark", "light", "deep", "fast", "slow",
    "soft", "quiet", "loud", "sharp", "sweet", "dry", "wet", "rich",
    "poor", "clean", "dirty", "safe", "sorry", "ready", "happy", "sad",
    "beautiful", "short", "tall", "heavy", "thin", "wide", "narrow",
    "red", "blue", "green", "white", "black", "brown", "yellow",
    # Common adverbs
    "up", "out", "just", "now", "also", "very", "often", "always",
    "never", "again", "still", "already", "almost", "enough", "quite",
    "here", "there", "together", "away", "down", "off", "only", "well",
    "too", "really", "even", "above", "below", "near", "far",
    # Time / misc
    "today", "tomorrow", "yesterday", "north", "south", "east", "west",
    "baby", "paper", "glass", "stone", "wood", "iron", "gold", "silver",
    "snow", "rain", "wind", "cloud", "island", "bridge", "boat", "ship",
    "horse", "cow", "pig", "chicken", "bread", "milk", "sugar", "salt",
    "egg", "fruit", "apple", "winter", "summer", "spring", "autumn",
    "hundred", "thousand", "million",
    # Body
    "heart", "brain", "bone", "skin", "arm", "leg", "foot", "finger",
    "nose", "mouth", "ear", "tooth", "hair", "neck", "shoulder",
    # More everyday words
    "picture", "letter", "ring", "ball", "hat", "dress", "shoe", "coat",
    "key", "box", "cup", "plate", "knife", "clock", "map", "flag",
    "gift", "price", "sign", "corner", "cross", "step", "hole", "lake",
    "farm", "village", "market", "store", "bank", "hotel", "station",
    "airport", "hospital", "library", "museum", "park", "restaurant",
    "color", "shape", "size", "sound", "smell", "taste", "touch",
    "dream", "fear", "hope", "pain", "anger", "peace", "truth",
    "brother", "sister", "daughter", "son", "husband", "wife",
]


# ---------------------------------------------------------------------------
# Check 1: Filter leak spot-check
# ---------------------------------------------------------------------------

def check_filter_leaks(words: list[str], freqs: dict[str, int],
                       config: dict) -> list[str]:
    out = []
    word_set = set(words)
    rng = random.Random(42)
    sample = rng.sample(words, min(200, len(words)))

    # Load UK spellings
    uk_words: set[str] = set()
    uk_cfg = config.get("filters", {}).get("uk_spelling", {})
    pf = uk_cfg.get("patterns_file")
    if pf:
        p = BASE_DIR / pf
        if p.exists():
            with open(p) as f:
                for line in f:
                    if "|" in line:
                        uk_words.add(line.split("|")[0].strip().lower())

    # Load letter names
    letter_names: set[str] = set()
    bl_cfg = config.get("filters", {}).get("blocklist", {})
    bl_dir = bl_cfg.get("directory")
    if bl_dir:
        ln_path = BASE_DIR / bl_dir / "letter_names.txt"
        if ln_path.exists():
            with open(ln_path) as f:
                letter_names = {line.strip().lower() for line in f if line.strip()}

    # Load dialect patterns
    dialect_patterns = []
    d_cfg = config.get("filters", {}).get("dialect", {})
    dpf = d_cfg.get("patterns_file")
    if dpf:
        for line in load_lines(BASE_DIR / dpf):
            dialect_patterns.append(re.compile(line))

    # Load custom filter patterns
    custom_patterns = []
    custom_dir = BASE_DIR / config.get("custom_filters_dir", "config/custom_filters")
    if custom_dir.is_dir():
        for yf in sorted(custom_dir.glob("*.yaml")):
            with open(yf) as f:
                filt = yaml.safe_load(f)
            if filt and filt.get("type") == "pattern":
                for p in filt.get("patterns", []):
                    custom_patterns.append((re.compile(p), filt.get("name", yf.stem)))

    # Abbreviation heuristic: all consonants, or very short with no vowels
    abbrev_re = re.compile(r"^[^aeiou]{3,}$")

    issues = []
    for w in sorted(sample):
        flags = []
        # UK spelling patterns
        if w in uk_words:
            flags.append("UK spelling")
        elif w.endswith(("our", "ise", "ised", "ising")):
            flags.append("possible UK spelling (-our/-ise)")
        elif len(w) > 4 and w.endswith("re") and not w.endswith(("re", "ore", "ire", "ure", "are", "ere")):
            flags.append("possible UK spelling (-re)")

        # Letter names
        if w in letter_names:
            flags.append("letter name")

        # Low frequency
        freq = freqs.get(w, 0)
        if freq < 100:
            flags.append(f"very low frequency ({freq})")

        # Abbreviation pattern
        if abbrev_re.match(w) and len(w) <= 5:
            flags.append("possible abbreviation")

        # Dialect patterns
        for pat in dialect_patterns:
            if pat.fullmatch(w):
                flags.append(f"dialect pattern /{pat.pattern}/")
                break

        # Custom filter patterns
        for pat, name in custom_patterns:
            if pat.fullmatch(w):
                flags.append(f"custom filter '{name}' /{pat.pattern}/")
                break

        if flags:
            issues.append((w, freq, flags))

    out.append("1. FILTER LEAK SPOT-CHECK")
    out.append(f"   Sampled 200 random words from the dictionary.")
    if issues:
        out.append(f"   Found {len(issues)} potential issues:\n")
        for w, freq, flags in issues:
            freq_str = f"{freq:,}" if freq > 0 else "—"
            out.append(f"   {w:<25s} freq={freq_str:<12s} {', '.join(flags)}")
    else:
        out.append("   No issues found — all 200 sampled words look clean.")
    out.append("")
    return out


# ---------------------------------------------------------------------------
# Check 2: Coverage check
# ---------------------------------------------------------------------------

def check_coverage(words_set: set[str], coverage_file: Path | None) -> list[str]:
    out = []
    if coverage_file and coverage_file.exists():
        expected = [line.strip().lower() for line in open(coverage_file) if line.strip()]
        source = str(coverage_file)
    else:
        expected = COMMON_WORDS
        source = f"built-in list ({len(COMMON_WORDS)} common words)"

    missing = [w for w in expected if w not in words_set]
    out.append("2. COVERAGE CHECK")
    out.append(f"   Source: {source}")
    out.append(f"   Expected: {len(expected):,}  |  Present: {len(expected) - len(missing):,}  |  Missing: {len(missing)}")
    if missing:
        out.append(f"   Missing words:")
        for w in sorted(missing):
            out.append(f"     - {w}")
    else:
        out.append("   All common words present.")
    out.append("")
    return out


# ---------------------------------------------------------------------------
# Check 3: Game-readiness stats
# ---------------------------------------------------------------------------

def check_game_readiness(words: list[str]) -> list[str]:
    out = []
    out.append("3. GAME-READINESS STATS")

    lengths = [len(w) for w in words]
    if not lengths:
        out.append("   No words to analyze.")
        return out

    avg_len = statistics.mean(lengths)
    med_len = statistics.median(lengths)
    min_len = min(lengths)
    max_len = max(lengths)

    out.append(f"   Total words: {len(words):,}")
    out.append(f"   Average length: {avg_len:.1f}")
    out.append(f"   Median length:  {med_len:.1f}")
    out.append(f"   Range: {min_len}–{max_len} letters")
    out.append("")

    # Length distribution
    from collections import Counter
    length_counts = Counter(lengths)
    max_count = max(length_counts.values())
    bar_width = 50

    out.append(f"   {'Len':>5s} {'Count':>7s}  Distribution")
    out.append(f"   {'─' * 5} {'─' * 7}  {'─' * bar_width}")
    for length in range(min_len, max_len + 1):
        count = length_counts.get(length, 0)
        bar_len = int(count / max_count * bar_width) if max_count > 0 else 0
        bar = "█" * bar_len
        out.append(f"   {length:>5d} {count:>7,}  {bar}")
    out.append("")

    # Single-letter and two-letter words
    one_letter = sorted(w for w in words if len(w) == 1)
    two_letter = sorted(w for w in words if len(w) == 2)
    out.append(f"   Single-letter words ({len(one_letter)}): {', '.join(one_letter) if one_letter else '(none)'}")
    out.append(f"   Two-letter words ({len(two_letter)}): {', '.join(two_letter) if two_letter else '(none)'}")
    out.append("")
    return out


# ---------------------------------------------------------------------------
# Check 4: Duplicate check
# ---------------------------------------------------------------------------

def check_duplicates(words: list[str]) -> list[str]:
    out = []
    out.append("4. DUPLICATE CHECK")
    from collections import Counter
    counts = Counter(words)
    dupes = {w: c for w, c in counts.items() if c > 1}
    if dupes:
        out.append(f"   Found {len(dupes)} duplicated words:")
        for w, c in sorted(dupes.items()):
            out.append(f"     {w} (appears {c}x)")
    else:
        out.append(f"   No duplicates found. All {len(words):,} entries are unique.")
    out.append("")
    return out


# ---------------------------------------------------------------------------
# Check 5: Regression check
# ---------------------------------------------------------------------------

def check_regression(current: set[str], previous_path: Path | None,
                     output_dir: Path) -> list[str]:
    out = []
    out.append("5. REGRESSION CHECK")

    # Auto-detect previous if not provided
    if previous_path is None:
        candidate = output_dir / "FINAL_DICTIONARY.prev.txt"
        if candidate.exists():
            previous_path = candidate

    if previous_path is None or not previous_path.exists():
        out.append("   No previous dictionary found. Skipping regression check.")
        out.append("   (Save a copy as FINAL_DICTIONARY.prev.txt to enable, or use --previous)")
        out.append("")
        return out

    prev_words = set(load_words(previous_path))
    added = current - prev_words
    removed = prev_words - current
    net = len(current) - len(prev_words)

    out.append(f"   Previous: {len(prev_words):,} words  ({previous_path.name})")
    out.append(f"   Current:  {len(current):,} words")
    out.append(f"   Added:    {len(added):,}")
    out.append(f"   Removed:  {len(removed):,}")
    out.append(f"   Net:      {'+' if net >= 0 else ''}{net:,}")

    if added and len(added) <= 30:
        out.append(f"\n   Added words:")
        for w in sorted(added):
            out.append(f"     + {w}")

    if removed and len(removed) <= 30:
        out.append(f"\n   Removed words:")
        for w in sorted(removed):
            out.append(f"     - {w}")

    if added and len(added) > 30:
        sample = sorted(added)[:15]
        out.append(f"\n   Added (showing 15 of {len(added):,}):")
        for w in sample:
            out.append(f"     + {w}")

    if removed and len(removed) > 30:
        sample = sorted(removed)[:15]
        out.append(f"\n   Removed (showing 15 of {len(removed):,}):")
        for w in sample:
            out.append(f"     - {w}")

    out.append("")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    config = load_config()
    output_dir = BASE_DIR / config["output_dir"]
    default_path = output_dir / "FINAL_DICTIONARY.txt"

    parser = argparse.ArgumentParser(description="Validate a word list file.")
    parser.add_argument("file", nargs="?", default=str(default_path),
                        help=f"Word list to validate (default: {default_path})")
    parser.add_argument("--coverage-file", type=str, default=None,
                        help="Custom coverage list (one word per line)")
    parser.add_argument("--previous", type=str, default=None,
                        help="Previous dictionary for regression check")
    args = parser.parse_args()

    word_file = Path(args.file) if Path(args.file).is_absolute() else BASE_DIR / args.file
    if not word_file.exists():
        print(f"Error: {word_file} not found.")
        return

    words = load_words(word_file)
    words_set = set(words)
    freqs = load_frequencies(BASE_DIR / config["frequency_data"])

    coverage_path = Path(args.coverage_file) if args.coverage_file else None
    previous_path = Path(args.previous) if args.previous else None

    report = []
    report.append(f"Validation Report: {word_file.name}")
    report.append(f"{'=' * 70}")
    report.append(f"File: {word_file}")
    report.append(f"Words: {len(words):,}")
    report.append("")

    report += check_filter_leaks(words, freqs, config)
    report += check_coverage(words_set, coverage_path)
    report += check_game_readiness(words)
    report += check_duplicates(words)
    report += check_regression(words_set, previous_path, output_dir)

    text = "\n".join(report)
    print(text)

    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "validation_report.txt", "w") as f:
        f.write(text + "\n")


if __name__ == "__main__":
    main()
