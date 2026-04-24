import json
import sys
from typing import Any

# Fix Windows console Unicode support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


BG_COLOR = "#1a1a2e"
PRIMARY = "#e0e0e0"
ACCENT = "#00d9ff"
WARNING = "#ff6b6b"
SUCCESS = "#00ff88"


class RichFormatter:
    def __init__(self, console=None):
        self.console = console

    def format_analysis(self, result, json_output: bool = False) -> str | dict:
        if json_output:
            return self._analysis_to_json(result)

        from rich.console import Console
        from rich.table import Table
        from rich.text import Text
        from rich.panel import Panel

        console = self.console or Console()
        output = []

        # Summary panel
        summary = f"""[cyan]Total Commits:[/cyan] {result.total_commits}
[cyan]Total Authors:[/cyan] {result.total_authors}
[cyan]Date Range:[/cyan] {result.date_range[0].strftime('%Y-%m-%d') if result.date_range else 'N/A'} -> {result.date_range[1].strftime('%Y-%m-%d') if result.date_range else 'N/A'}"""

        console.print(Panel(summary, title="GitFingerprint Analysis", border_style=ACCENT))

        # Commits by weekday
        weekday_table = Table(title="Commits by Weekday")
        weekday_table.add_column("Day", style=PRIMARY)
        weekday_table.add_column("Commits", style=ACCENT)

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            count = result.commits_by_weekday.get(i, 0)
            weekday_table.add_row(day, str(count))

        console.print(weekday_table)

        # Commits by hour
        hour_table = Table(title="Commits by Hour (24h)")
        hour_table.add_column("Hour", style=PRIMARY)
        hour_table.add_column("Commits", style=ACCENT)

        for hour in range(24):
            count = result.commits_by_hour.get(hour, 0)
            hour_table.add_row(f"{hour:02d}:00", str(count))

        console.print(hour_table)

        # Metrics panel
        metrics = f"""[cyan]Avg Commit Size:[/cyan] {result.avg_commit_size:.1f} lines
[cyan]Refactor Ratio:[/cyan] {result.refactor_ratio*100:.1f}%
[cyan]Burst Days (>10 commits):[/cyan] {result.burst_count}
[cyan]Burnout Score:[/cyan] {result.burnout_score:.0f}/100"""

        console.print(Panel(metrics, title="Metrics", border_style=WARNING if result.burnout_score > 60 else SUCCESS))

        # Top authors
        if result.author_commits:
            author_table = Table(title="Top Authors by Commit Count")
            author_table.add_column("Author", style=PRIMARY)
            author_table.add_column("Commits", style=ACCENT)

            sorted_authors = sorted(result.author_commits.items(), key=lambda x: x[1], reverse=True)[:10]
            for author, count in sorted_authors:
                author_table.add_row(author, str(count))

            console.print(author_table)

        return ""

    def _analysis_to_json(self, result) -> dict:
        return {
            "total_commits": result.total_commits,
            "total_authors": result.total_authors,
            "commits_by_weekday": dict(result.commits_by_weekday),
            "commits_by_hour": dict(result.commits_by_hour),
            "avg_commit_size": round(result.avg_commit_size, 2),
            "refactor_ratio": round(result.refactor_ratio, 4),
            "burst_count": result.burst_count,
            "burnout_score": round(result.burnout_score, 1),
            "author_commits": result.author_commits,
            "date_range": [
                result.date_range[0].isoformat() if result.date_range else None,
                result.date_range[1].isoformat() if result.date_range else None,
            ],
        }

    def format_burnout(self, result, json_output: bool = False) -> str | dict:
        if json_output:
            return self._burnout_to_json(result)

        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = self.console or Console()

        score_color = SUCCESS if result.score < 40 else WARNING if result.score < 70 else WARNING
        score_style = f"[{score_color}]{result.score}[/{score_color}]"

        breakdown_text = f"""[cyan]Late-night commits factor:[/cyan] {result.late_night_factor}/30
[cyan]Frequency spike/drop factor:[/cyan] {result.frequency_spike_factor}/30
[cyan]Burst pattern factor:[/cyan] {result.burst_factor}/25
[cyan]Sentiment factor:[/cyan] {result.sentiment_factor}/15

[yellow]Breakdown:[/yellow]
Late-night commits: {result.breakdown['late_night_commits']} ({result.breakdown['late_night_ratio']}%)
Recent daily avg: {result.breakdown['recent_daily_avg']}
Spike ratio: {result.breakdown['spike_ratio']}x
Burst days: {result.breakdown['burst_days']}
Neg/Pos commits: {result.breakdown['negative_commits']}/{result.breakdown['positive_commits']}"""

        console.print(Panel(
            breakdown_text,
            title=f"Burnout Score: {score_style}/100",
            border_style=score_color,
        ))

        return ""

    def _burnout_to_json(self, result) -> dict:
        return {
            "score": result.score,
            "late_night_factor": result.late_night_factor,
            "frequency_spike_factor": result.frequency_spike_factor,
            "burst_factor": result.burst_factor,
            "sentiment_factor": result.sentiment_factor,
            "breakdown": result.breakdown,
        }

    def format_trend(self, trend_data: dict, json_output: bool = False) -> str | dict:
        if json_output:
            return trend_data

        from rich.console import Console
        from rich.panel import Panel

        console = self.console or Console()

        burnout_indicator = "^" if trend_data["burnout_trend"] > 10 else "v" if trend_data["burnout_trend"] < -10 else "="
        trend_color = WARNING if trend_data["burnout_trend"] > 10 else SUCCESS

        trend_text = f"""[cyan]Period:[/cyan] Last {trend_data['period_days']} days
[cyan]Commit count:[/cyan] {trend_data['commit_count']}
[cyan]Avg daily commits:[/cyan] {trend_data['avg_daily_commits']:.2f}
[cyan]Avg churn:[/cyan] {trend_data['avg_churn']:.1f} lines
[{trend_color}]Burnout trend:[/] {burnout_indicator} {abs(trend_data['burnout_trend']):.1f}%"""

        console.print(Panel(trend_text, title=f"Trend ({trend_data['period_days']} days)", border_style=ACCENT))

        return ""

    def format_init(self, is_new: bool, json_output: bool = False) -> str | dict:
        if json_output:
            return {"initialized": True, "incremental": not is_new}

        from rich.console import Console
        from rich.panel import Panel

        console = self.console or Console()
        msg = "Initialized GitFingerprint (incremental mode)" if not is_new else "Initialized GitFingerprint (first run - analyzing all history)"
        console.print(Panel(msg, border_style=SUCCESS))

        return ""
