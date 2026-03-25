# Custom Filters

Drop `.yaml` files in this directory to add filters to the curation pipeline.
Files are loaded alphabetically **after** all built-in filters.

To disable a filter without deleting it, rename the file to `.yaml.disabled`.

---

## File format

```yaml
name: my_filter            # unique identifier
description: "What it does" # shown in the curation report
mode: reject               # "reject" (auto-remove) or "flag" (send to review)
type: blocklist             # one of: blocklist, pattern, frequency_gate, suffix
# ... type-specific fields below
```

---

## Filter types

### `blocklist`

Remove or flag exact word matches from a file.

| Field | Required | Description |
|---|---|---|
| `words_file` | yes | Path to a `.txt` file, one word per line |

```yaml
name: jargon
description: "Remove jargon terms"
mode: reject
type: blocklist
words_file: data/blocklists/jargon.txt
```

### `pattern`

Remove or flag words matching one or more regex patterns.

| Field | Required | Description |
|---|---|---|
| `patterns` | yes | List of regex strings |
| `exclude` | no | List of words to exempt from matching |

```yaml
name: double_vowels
description: "Flag words with unusual double vowels"
mode: flag
type: pattern
patterns:
  - ".*uu.*"
  - ".*aa.*"
exclude:
  - aardvark
  - vacuum
```

### `frequency_gate`

Remove or flag words below a frequency threshold. Use **one** of:

| Field | Required | Description |
|---|---|---|
| `max_frequency` | one of these | Absolute frequency cutoff |
| `frequency_multiplier` | one of these | Multiple of the main threshold from settings.yaml |
| `patterns` | no | Only apply to words matching these regexes |

```yaml
name: rare_compounds
description: "Flag rare hyphenated compounds"
mode: flag
type: frequency_gate
frequency_multiplier: 5
patterns:
  - ".*-.*"
```

### `suffix`

Remove or flag words with a specific suffix, optionally only when the base word
(word minus the suffix) exists in the dictionary.

| Field | Required | Description |
|---|---|---|
| `suffix` | yes | The suffix to match (e.g. `-ling`) |
| `require_base_in_list` | yes | If true, only match when the base word is also in the word list |
| `frequency_multiplier` | no | Only apply to words below this multiple of the main threshold |

```yaml
name: diminutives
description: "Flag rare -ling diminutives whose base word exists"
mode: flag
type: suffix
suffix: ling
require_base_in_list: true
frequency_multiplier: 2
```

---

## Example (uncomment to activate)

```yaml
# name: obscure_plurals
# description: "Flag obscure Latin/Greek plural forms"
# mode: flag
# type: frequency_gate
# frequency_multiplier: 3
# patterns:
#   - ".*ices$"
#   - ".*ata$"
```
