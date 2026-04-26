import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click

from gf import __version__
from gf.analyzer import Analyzer, CommitInfo
from gf.burnout import BurnoutScorer
from gf.config import Config
from gf.formatter import RichFormatter


def get_repo_path(ctx, param, value):
    if value is None:
        return os.getcwd()
    return value


def run_git_log(repo_path: str, max_count: int | None = None) -> str:
    cmd = [
        "git", "-C", repo_path,
        "log", "--all",
        "--format=%H%n%an%n%ae%n%at%n%s%n==END==",
    ]
    if max_count:
        cmd.insert(4, f"--max-count={max_count}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise click.ClickException(f"Git error: {result.stderr}")
    return result.stdout


def run_git_log_with_stats(repo_path: str) -> list[CommitInfo]:
    cmd = [
        "git", "-C", repo_path,
        "log", "--all", "--numstat",
        "--format=%H%n%an%n%ae%n%at%n%s%n==END==",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise click.ClickException(f"Git error: {result.stderr}")

    commits = []
    records = result.stdout.split("==END==\n")
    current_commit = None
    current_insertions = 0
    current_deletions = 0

    for record in records:
        record = record.strip()
        if not record:
            continue
        lines = record.split("\n")
        if len(lines) < 5:
            continue

        # Check if this is a numstat block (lines with numbers)
        stat_lines = []
        content_lines = []
        for line in lines[5:]:
            if line and "\t" in line:
                parts = line.split("\t")
                if len(parts) == 3:
                    try:
                        int(parts[0])  # insertions
                        int(parts[1])  # deletions
                        stat_lines.append(line)
                    except ValueError:
                        content_lines.append(line)
                else:
                    content_lines.append(line)
            else:
                content_lines.append(line)

        # If we have stat lines, parse them for current commit
        if stat_lines and current_commit is None:
            # First record has the commit info
            try:
                hash_ = lines[0]
                author = lines[1]
                timestamp = int(lines[3])
                message = lines[4]
                date = datetime.fromtimestamp(timestamp)

                insertions = 0
                deletions = 0
                for stat_line in stat_lines:
                    parts = stat_line.split("\t")
                    if len(parts) == 3:
                        try:
                            insertions += int(parts[0])
                        except ValueError:
                            pass
                        try:
                            deletions += int(parts[1])
                        except ValueError:
                            pass

                churn = insertions + deletions
                commits.append(CommitInfo(
                    hash=hash_,
                    author=author,
                    date=date,
                    message=message,
                    insertions=insertions,
                    deletions=deletions,
                    churn=churn,
                ))
            except (ValueError, IndexError):
                continue

    return commits


@click.group()
@click.version_option(version=__version__)
def cli():
    """GitFingerprint — reveal who you actually are as a programmer."""
    pass


@cli.command()
@click.option("--repo", callback=get_repo_path, help="Path to git repository")
@click.option("--json", "json_output", is_flag=True, help="Output JSON")
def init(repo, json_output):
    """Initialize fingerprint tracking in current repo."""
    config = Config(repo)
    data = config.read()
    is_new = data.get("last_analyzed") is None
    config.write(data)

    formatter = RichFormatter()
    formatter.format_init(is_new, json_output)

    if json_output:
        click.echo(formatter.format_init(is_new, json_output))


@cli.command()
@click.option("--repo", callback=get_repo_path, help="Path to git repository")
@click.option("--json", "json_output", is_flag=True, help="Output JSON")
@click.option("--max-commits", default=None, type=int, help="Limit commits analyzed")
def analyze(repo, json_output, max_commits):
    """Run full analysis on the repo."""
    try:
        log_output = run_git_log(repo, max_commits)
    except FileNotFoundError:
        raise click.ClickException("Git not found. Is Git installed and in PATH?")
    except Exception as e:
        raise click.ClickException(str(e))

    commits = Analyzer.parse_commits(log_output)
    if not commits:
        click.echo("No commits found.")
        return

    analyzer = Analyzer(repo)
    result = analyzer.analyze(commits)

    # Calculate burnout
    scorer = BurnoutScorer()
    burnout = scorer.score(commits)
    result.burnout_score = burnout.score

    formatter = RichFormatter()

    if json_output:
        output = formatter.format_analysis(result, json_output=True)
        click.echo(json.dumps(output))
    else:
        formatter.format_analysis(result)
        # Also show burnout
        formatter.format_burnout(burnout)


@cli.command()
@click.option("--repo", callback=get_repo_path, help="Path to git repository")
@click.option("--json", "json_output", is_flag=True, help="Output JSON")
@click.option("--days", default=30, type=int, help="Number of days to analyze")
def trend(repo, json_output, days):
    """Show how metrics changed over time."""
    try:
        log_output = run_git_log(repo)
    except FileNotFoundError:
        raise click.ClickException("Git not found.")
    except Exception as e:
        raise click.ClickException(str(e))

    commits = Analyzer.parse_commits(log_output)
    analyzer = Analyzer(repo)
    trend_data = analyzer.trend(commits, days)

    formatter = RichFormatter()

    if json_output:
        click.echo(json.dumps(trend_data))
    else:
        formatter.format_trend(trend_data)


@cli.command()
@click.option("--repo", callback=get_repo_path, help="Path to git repository")
@click.option("--json", "json_output", is_flag=True, help="Output JSON")
@click.option("--by-author", is_flag=True, help="Show per-author burnout breakdown")
def burnout(repo, json_output, by_author):
    """Focused burnout risk assessment."""
    try:
        log_output = run_git_log(repo)
    except FileNotFoundError:
        raise click.ClickException("Git not found.")
    except Exception as e:
        raise click.ClickException(str(e))

    commits = Analyzer.parse_commits(log_output)
    scorer = BurnoutScorer()

    formatter = RichFormatter()

    if by_author:
        results = scorer.score_by_author(commits)
        if json_output:
            click.echo(json.dumps([formatter._author_burnout_to_json(r) for r in results]))
        else:
            formatter.format_burnout_by_author(results)
    else:
        result = scorer.score(commits)
        if json_output:
            click.echo(json.dumps(formatter._burnout_to_json(result)))
        else:
            formatter.format_burnout(result)


@cli.command()
@click.option("--repo", callback=get_repo_path, help="Path to git repository")
@click.option("--json", "json_output", is_flag=True, help="Output JSON")
@click.option("--output", type=click.Path(), help="Output file (PNG not implemented)")
def report(repo, json_output, output):
    """Generate a summary card."""
    try:
        log_output = run_git_log(repo)
    except FileNotFoundError:
        raise click.ClickException("Git not found.")
    except Exception as e:
        raise click.ClickException(str(e))

    commits = Analyzer.parse_commits(log_output)
    analyzer = Analyzer(repo)
    result = analyzer.analyze(commits)

    scorer = BurnoutScorer()
    burnout = scorer.score(commits)
    result.burnout_score = burnout.score

    formatter = RichFormatter()

    if json_output:
        report_data = {
            "analysis": formatter._analysis_to_json(result),
            "burnout": formatter._burnout_to_json(burnout),
        }
        click.echo(json.dumps(report_data))
    else:
        formatter.format_analysis(result)
        formatter.format_burnout(burnout)

    if output:
        click.echo(f"Report saved to {output} (PNG not yet implemented)")


def main():
    cli()


if __name__ == "__main__":
    main()
