# Dictionary Curation

A config-driven pipeline for building clean, game-ready English word lists. Takes a raw dictionary (default: ENABLE2K, 173K words), filters it through frequency data, blocklists, and pattern matchers, then outputs a curated word list with full audit trail.

The pipeline is designed so you never edit code — all behavior is controlled through `config/settings.yaml` and drop-in text/YAML files.

## Quickstart

```bash
# 1. Install dependencies
pip install pyyaml

# 2. Run the curation pipeline
python3 scripts/curate.py

# 3. Review flagged words interactively
python3 scripts/review_helper.py

# 4. Assemble the final dictionary
python3 scripts/finalize.py

# 5. Validate the result
python3 scripts/validate.py
```

Output lands in `data/output/FINAL_DICTIONARY.txt`.

## Configuration

All settings live in `config/settings.yaml`.

### Frequency threshold

```yaml
frequency_threshold: 5000
```

Words below this frequency in Norvig's corpus are rejected. Use `frequency_filter.py` to calibrate — it shows the distribution at any threshold so you can pick the right cutoff.

With ENABLE2K + Norvig's data, the distribution is bimodal: words are either absent (frequency 0) or above ~12,700. Effective thresholds are:

| Threshold | Words kept | Notes |
|---|---|---|
| 1 | ~79K | Everything found in corpus |
| 20,000 | ~73K | Drops ~6K borderline words |
| 50,000 | ~59K | Starts cutting real words |
| 100,000 | ~48K | Only well-known words |

### Enabling/disabling filters

Each filter has an `enabled` flag:

```yaml
filters:
  frequency:
    enabled: true    # set to false to skip this filter entirely
    mode: reject
```

### Reject vs. flag mode

- **reject** — words are automatically removed from the dictionary
- **flag** — words are sent to `review/` for manual review via `review_helper.py`

```yaml
filters:
  agent_nouns:
    enabled: true
    mode: flag       # change to "reject" to auto-remove instead
```

### Built-in filters

| Filter | Default mode | What it does |
|---|---|---|
| `frequency` | reject | Removes words below the frequency threshold |
| `blocklist` | reject | Removes words found in any `.txt` file in `data/blocklists/reject/` |
| `uk_spelling` | reject | Removes UK spelling variants (colour, analyse, etc.) |
| `agent_nouns` | flag | Flags low-frequency `-er` nouns |
| `dialect` | flag | Flags words matching patterns in `config/dialect_patterns.txt` |
| `scientific` | flag | Flags long words with scientific combining forms |

## Customization

### Adding a blocklist

Drop a `.txt` file (one word per line, lowercase) into `data/blocklists/reject/`:

```bash
echo -e "foo\nbar\nbaz" > data/blocklists/reject/my_blocklist.txt
```

It will be picked up automatically on the next run.

### Adding a custom filter

1. Copy the example:
   ```bash
   cp config/custom_filters/00_example_loan_words.yaml.disabled \
      config/custom_filters/01_my_filter.yaml
   ```

2. Edit the YAML. Four filter types are available:

   | Type | What it does | Required fields |
   |---|---|---|
   | `blocklist` | Exact word matches | `words_file` |
   | `pattern` | Regex matches | `patterns` (list). Optional: `exclude` |
   | `frequency_gate` | Below a frequency cutoff | `max_frequency` or `frequency_multiplier`. Optional: `patterns` |
   | `suffix` | Words with a suffix (optionally where base exists) | `suffix`, `require_base_in_list`. Optional: `frequency_multiplier` |

   Example:
   ```yaml
   name: rare_compounds
   description: "Flag rare hyphenated words"
   mode: flag
   type: frequency_gate
   frequency_multiplier: 5
   patterns:
     - ".*-.*"
   ```

3. To disable without deleting, rename to `.yaml.disabled`.

See `config/custom_filters/README.md` for full documentation.

### Adding words to the whitelist

Words in the frequency filter's whitelist bypass the frequency check:

```yaml
filters:
  frequency:
    whitelist: data/blocklists/archaic_whitelist.txt
```

Add words to that file (one per line) to protect them from frequency-based removal.

For words missing from the source dictionary entirely, use `--add-words` at finalize time:

```bash
python3 scripts/finalize.py --add-words my_extras.txt
```

### Modifying dialect or scientific patterns

Edit the pattern files directly:

- `config/dialect_patterns.txt` — one regex per line, comments after `#`
- `config/scientific_forms.txt` — one prefix (`poly-`) or suffix (`-ology`) per line

## Scripts Reference

### curate.py

Main pipeline. Reads config, applies all filters, writes output.

```bash
python3 scripts/curate.py                     # use config as-is
python3 scripts/curate.py --threshold 20000   # override threshold
python3 scripts/curate.py --dry-run           # preview without writing files
python3 scripts/curate.py --config path.yaml  # use a different config file
```

**Output:**
- `data/output/clean_dictionary.txt` — words that passed all reject filters
- `data/output/rejected.txt` — removed words with reasons (`word | filter | reason`)
- `data/output/curation_report.txt` — per-filter stats
- `review/flagged_{filter}.txt` — per-filter flagged words
- `review/all_flagged.txt` — combined flagged words with reasons

### review_helper.py

Interactive terminal tool for reviewing flagged words.

```bash
python3 scripts/review_helper.py                        # review all flagged words
python3 scripts/review_helper.py --batch-size 10        # smaller batches
python3 scripts/review_helper.py --filter-name dialect  # review one filter only
python3 scripts/review_helper.py --reset                # discard progress, start over
```

Commands during review: `k` keep all, `r` reject all, `1,3,5` keep specific numbers, `s` skip, `q` quit and save.

Progress saves to `review/review_progress.json` — quit and resume any time.

**Output:**
- `review/reviewed_keep.txt` — approved words
- `review/reviewed_reject.txt` — rejected words

### finalize.py

Assembles the final dictionary from curated output + review decisions.

```bash
python3 scripts/finalize.py                                  # base + reviewed keeps
python3 scripts/finalize.py --add-words extras.txt           # merge additional words
python3 scripts/finalize.py --remove-words unwanted.txt      # remove specific words
python3 scripts/finalize.py --add-words a.txt --add-words b.txt  # multiple files
```

**Output:** `data/output/FINAL_DICTIONARY.txt`

### validate.py

Quality checks on any word list.

```bash
python3 scripts/validate.py                              # validate FINAL_DICTIONARY.txt
python3 scripts/validate.py path/to/wordlist.txt         # validate a different file
python3 scripts/validate.py --coverage-file my_words.txt # custom coverage check list
python3 scripts/validate.py --previous old_dictionary.txt # regression diff
```

Checks: filter leak spot-check (200-word sample), coverage against 540 common words, length distribution histogram, duplicate check, regression diff.

**Output:** `data/output/validation_report.txt`

### frequency_filter.py

Standalone calibration tool. Run this first to choose your threshold.

```bash
python3 scripts/frequency_filter.py                # default threshold (5000)
python3 scripts/frequency_filter.py --threshold 20000
```

**Output:** `data/output/frequency_report.txt` with distribution buckets and sample words.

## Reuse for a Different Game

1. **Swap the source dictionary.** Place your word list in `data/raw/` and update `config/settings.yaml`:
   ```yaml
   source_dictionary: data/raw/my_wordlist.txt
   ```
   Format: one word per line, lowercase.

2. **Calibrate the threshold.** Run the frequency filter to see how your dictionary maps to Norvig's data:
   ```bash
   python3 scripts/frequency_filter.py --threshold 1
   ```
   Look at the report, pick a cutoff, update `frequency_threshold` in config.

3. **Add game-specific filters.** Examples:
   - Minimum word length: create a custom `frequency_gate` filter with a `patterns` regex like `^.{1,2}$` to flag 1-2 letter words
   - Banned categories: drop a blocklist `.txt` into `data/blocklists/reject/`
   - Offensive words: the included `profanity.txt` works for most games

4. **Run the pipeline:**
   ```bash
   python3 scripts/curate.py
   python3 scripts/review_helper.py
   python3 scripts/finalize.py
   python3 scripts/validate.py
   ```

5. **Iterate.** If validation flags issues, adjust filters and re-run. Save `FINAL_DICTIONARY.txt` as `FINAL_DICTIONARY.prev.txt` before each run to track regressions.

## Project Structure

```
dictionary-curation/
├── config/
│   ├── settings.yaml              # main configuration
│   ├── dialect_patterns.txt       # regex patterns for dialect filter
│   ├── scientific_forms.txt       # prefixes/suffixes for scientific filter
│   └── custom_filters/            # drop .yaml files here to add filters
├── data/
│   ├── raw/                       # source dictionaries and frequency data
│   ├── blocklists/
│   │   ├── reject/                # auto-reject blocklists (one .txt per category)
│   │   ├── uk_spelling_patterns.txt
│   │   ├── archaic_whitelist.txt
│   │   └── essential_additions.txt
│   └── output/                    # generated files
├── review/                        # flagged words and review state
└── scripts/
    ├── curate.py                  # main pipeline
    ├── review_helper.py           # interactive review tool
    ├── finalize.py                # final assembly
    ├── validate.py                # quality checks
    └── frequency_filter.py        # threshold calibration
```
