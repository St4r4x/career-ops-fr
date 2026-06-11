# Mode: rescore-offers

Use this mode after changing `config/settings.yaml` to recompute scores for all existing offers.

## When to use

- After changing `scoring.target_salary_min` or `scoring.target_salary_max`
- After adding or removing companies from `target_companies`
- After changing `search.keywords`
- When scores feel stale or miscalibrated

## How to run

```bash
# Dry run — preview changes without writing to DB
python -m scripts.rescore --dry-run

# Apply rescoring
python -m scripts.rescore

# Rescore a specific DB file
python -m scripts.rescore --db /path/to/applications.db
```

## What it does

1. Reads `config/settings.yaml` for current scoring config
2. Fetches all offers from the DB
3. Re-runs `score_offer()` from `scripts/pre_filter.py` on each offer's description
4. Updates `score_value` and `score_grade` in the DB
5. Prints a summary of grade distribution changes

## Expected output

```
Total: 156 offers -- Updated: 23
```

Individual changes are printed at INFO level (one line per updated offer):
```
INFO scripts.rescore: id=42  Mistral AI / AI Engineer          : B/72.0 -> A/85.5
```
