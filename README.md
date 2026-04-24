# GitFingerprint

CLI tool that mines your git history to reveal who you actually are as a programmer. Not how you think you code, but how you really code — revealed through the objective lens of your commit history.

## Installation

```bash
pip install -e .
```

Or directly:

```bash
pip install git-fingerprint
```

## Commands

### `gf analyze`

Run full analysis on the repository.

```bash
gf analyze
gf analyze --repo /path/to/repo
gf analyze --json
gf analyze --max-commits 1000
```

Output includes:
- Commit frequency by weekday and hour
- Average commit size
- Refactoring ratio
- Churn trends
- Burst detection
- Burnout score

### `gf burnout`

Focused burnout risk assessment with 0-100 score.

```bash
gf burnout
gf burnout --repo /path/to/repo
gf burnout --json
```

Score breakdown:
- Late-night commits (0-30)
- Frequency spike/drop (0-30)
- Burst patterns (0-25)
- Sentiment (0-15)

### `gf trend`

Show how metrics changed over last 30/60/90 days.

```bash
gf trend --days 30
gf trend --days 60
gf trend --days 90
```

### `gf init`

Initialize fingerprint tracking in current repo.

```bash
gf init
```

Creates `.gitfingerprint/config.json` for incremental updates.

### `gf report`

Generate a summary card.

```bash
gf report
gf report --json
```

## JSON Output

All commands support `--json` flag for machine-readable output:

```bash
gf analyze --json > analysis.json
gf burnout --json | jq '.score'
```

## Requirements

- Python 3.10+
- Git
- click
- rich
- gitpython

## License

MIT
