# GitFingerprint — Spec

## Concept & Vision

GitFingerprint is a CLI tool that mines your git history to reveal *who you actually are as a programmer*. Not how you think you code, but how you really code — revealed through the objective lens of your commit history. It's introspective, a bit uncomfortable, and genuinely useful.

The vibe is: a serious dev tool with a dark terminal aesthetic and moments of levity (especially around burnout predictions).

## Design Language

- **Aesthetic**: Dark terminal UI using `rich` library. Think `htop` meets a health tracker.
- **Colors**: 
  - Background: `#1a1a2e` (deep navy)
  - Primary text: `#e0e0e0`
  - Accent: `#00d9ff` (cyan) for metrics
  - Warning: `#ff6b6b` (soft red) for burnout indicators
  - Success: `#00ff88` (green) for healthy metrics
- **Typography**: Monospace terminal font (system default)
- **Motion**: Minimal — data appears in tables, no flashy animations

## Features & Interactions

### Commands

1. **`gf init`** — Initialize fingerprint tracking in current repo
   - Creates `.gitfingerprint/config.json`
   - First run: analyze all history
   - Subsequent runs: incremental updates

2. **`gf analyze`** — Run full analysis on the repo
   - Shows: commit frequency heatmap (by day/hour), avg commit size, refactoring ratio, churn trends, burst detection, burnout score
   - Output: rich terminal table + optional `--json` flag

3. **`gf trend`** — Show how metrics changed over last 30/60/90 days
   - Time-series stats: commit count trend, churn trend, burnout trend

4. **`gf burnout`** — Focused burnout risk assessment
   - Score 0-100 with breakdown:
     - Consecutive late-night commits
     - Commit frequency spikes/drops
     - Message sentiment (if detectable)
     - Burst patterns (too many commits in short time)

5. **`gf report`** — Generate a summary card (text + optional PNG)

### Acceptance Criteria

- [ ] `gf analyze` produces commit frequency by weekday, churn stats, refactor ratio
- [ ] `gf burnout` shows a 0-100 score with contributing factors
- [ ] `gf trend` shows 30/60/90 day comparisons
- [ ] `--json` flag outputs machine-readable JSON for all commands
- [ ] Works with any git repo (no special setup required)
- [ ] Handles repos with 10k+ commits efficiently
- [ ] Comprehensive README with install instructions and examples
- [ ] Tests for core parsing logic

## Technical Approach

- **Language**: Python 3.10+
- **Libraries**: `rich` (terminal UI), `gitpython` (git log parsing), `click` (CLI framework)
- **Architecture**: 
  - `gf/cli.py` — Click command definitions
  - `gf/analyzer.py` — Core analysis engine
  - `gf/burnout.py` — Burnout scoring logic
  - `gf/formatter.py` — Rich terminal output + JSON
  - `gf/config.py` — Config file management
- **Data flow**: git log → parser → analyzer → formatter → output
