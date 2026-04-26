from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from gf.burnout import BurnoutScorer, BurnoutResult


@dataclass
class CommitInfo:
    hash: str
    author: str
    date: datetime
    message: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    churn: int = 0  # lines changed (additions + deletions)


@dataclass
class AuthorStats:
    commits: int = 0
    avg_churn: float = 0.0
    burnout_score: float = 0.0
    busiest_hour: int = 0
    busiest_weekday: int = 0
    first_commit: str = ""
    last_commit: str = ""
    refactor_ratio: float = 0.0
    top_keywords: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    total_commits: int = 0
    total_authors: int = 0
    commits_by_weekday: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    commits_by_hour: dict[int, int] = field(default_factory=lambda: defaultdict(int))
    avg_commit_size: float = 0.0
    refactor_ratio: float = 0.0
    churn_trend: list[float] = field(default_factory=list)
    burst_count: int = 0
    burnout_score: float = 0.0
    author_commits: dict[str, int] = field(default_factory=dict)
    date_range: tuple[datetime, datetime] | None = None
    commits_per_day: list[int] = field(default_factory=list)
    author_breakdown: dict[str, AuthorStats] = field(default_factory=dict)


class Analyzer:
    COMMIT_FORMAT = "--format=%H%n%an%n%ae%n%at%n%s%n==END=="
    CHURN_WINDOW_DAYS = 7

    def __init__(self, repo_path: str | None = None):
        self.repo_path = repo_path

    def analyze(self, commits: list[CommitInfo]) -> AnalysisResult:
        if not commits:
            return AnalysisResult()

        result = AnalysisResult()
        result.total_commits = len(commits)
        result.total_authors = len({c.author for c in commits})

        # Sort by date
        commits_sorted = sorted(commits, key=lambda c: c.date)
        result.date_range = (commits_sorted[0].date, commits_sorted[-1].date)

        # Commits by weekday (0=Monday, 6=Sunday)
        for c in commits:
            result.commits_by_weekday[c.date.weekday()] += 1

        # Commits by hour
        for c in commits:
            result.commits_by_hour[c.date.hour] += 1

        # Avg commit size (churn)
        if commits:
            total_churn = sum(c.churn for c in commits)
            result.avg_commit_size = total_churn / len(commits)

        # Refactor ratio: commits with message containing "refactor" / total
        refactor_count = sum(1 for c in commits if "refactor" in c.message.lower())
        result.refactor_ratio = refactor_count / len(commits) if commits else 0.0

        # Churn trend (rolling window)
        result.churn_trend = self._churn_trend(commits_sorted)

        # Burst detection: >10 commits in same day
        daily_counts: dict[str, int] = defaultdict(int)
        for c in commits:
            daily_counts[c.date.strftime("%Y-%m-%d")] += 1
        result.burst_count = sum(1 for count in daily_counts.values() if count > 10)

        # Commits per day for trend
        result.commits_per_day = list(daily_counts.values())

        # Author breakdown
        author_commits_map: dict[str, list[CommitInfo]] = defaultdict(list)
        for c in commits:
            author_commits_map[c.author].append(c)

        for author, author_commits in author_commits_map.items():
            sorted_author = sorted(author_commits, key=lambda c: c.date)
            total_churn = sum(c.churn for c in author_commits)
            avg_churn = total_churn / len(author_commits) if author_commits else 0.0

            # Per-author burnout
            author_scorer = BurnoutScorer()
            author_burnout = author_scorer.score(author_commits)

            # Busiest hour and weekday
            hour_counts: dict[int, int] = defaultdict(int)
            weekday_counts: dict[int, int] = defaultdict(int)
            for c in author_commits:
                hour_counts[c.date.hour] += 1
                weekday_counts[c.date.weekday()] += 1
            busiest_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 0
            busiest_weekday = max(weekday_counts, key=weekday_counts.get) if weekday_counts else 0

            # Refactor ratio for author
            refactor_count = sum(1 for c in author_commits if "refactor" in c.message.lower())
            author_refactor_ratio = refactor_count / len(author_commits) if author_commits else 0.0

            # Top keywords (most common words in messages)
            word_counts: dict[str, int] = defaultdict(int)
            for c in author_commits:
                words = c.message.lower().split()
                for word in words:
                    if len(word) > 4 and word not in {"which", "there", "their", "would", "could", "should", "where", "when", "what", "this", "that", "from", "with", "have", "been", "were", "they", "them", "your", "some", "also", "more", "into", "than"}:
                        word_counts[word] += 1
            top_keywords = [w for w, _ in sorted(word_counts.items(), key=lambda x: -x[1])][:5]

            result.author_breakdown[author] = AuthorStats(
                commits=len(author_commits),
                avg_churn=round(avg_churn, 1),
                burnout_score=author_burnout.score,
                busiest_hour=busiest_hour,
                busiest_weekday=busiest_weekday,
                first_commit=sorted_author[0].date.strftime("%Y-%m-%d") if sorted_author else "",
                last_commit=sorted_author[-1].date.strftime("%Y-%m-%d") if sorted_author else "",
                refactor_ratio=round(author_refactor_ratio, 3),
                top_keywords=top_keywords,
            )

        # Author commits
        for c in commits:
            result.author_commits[c.author] = result.author_commits.get(c.author, 0) + 1

        return result

    def _churn_trend(self, commits: list[CommitInfo]) -> list[float]:
        if not commits:
            return []

        min_date = commits[0].date
        max_date = commits[-1].date
        days = (max_date - min_date).days + 1
        if days <= self.CHURN_WINDOW_DAYS:
            return [sum(c.churn for c in commits) / max(days, 1)]

        windows = []
        for i in range(0, days, self.CHURN_WINDOW_DAYS):
            window_start = min_date + timedelta(days=i)
            window_end = window_start + timedelta(days=self.CHURN_WINDOW_DAYS)
            window_churn = sum(c.churn for c in commits if window_start <= c.date < window_end)
            windows.append(window_churn / self.CHURN_WINDOW_DAYS)

        return windows

    def trend(self, commits: list[CommitInfo], days: int) -> dict[str, Any]:
        if not commits:
            return {
                "period_days": days,
                "commit_count": 0,
                "avg_daily_commits": 0.0,
                "avg_churn": 0.0,
                "burnout_trend": 0.0,
            }

        cutoff = datetime.now() - timedelta(days=days)
        recent = [c for c in commits if c.date >= cutoff]

        older_cutoff = datetime.now() - timedelta(days=days * 2)
        older = [c for c in commits if older_cutoff <= c.date < cutoff]

        recent_count = len(recent)
        older_count = len(older)

        commit_trend = (recent_count - older_count) / max(older_count, 1) * 100

        recent_churn = sum(c.churn for c in recent) / max(recent_count, 1)
        older_churn = sum(c.churn for c in older) / max(older_count, 1)
        churn_trend = (recent_churn - older_churn) / max(older_churn, 1) * 100 if older_churn else 0.0

        # Simple burnout trend: difference in daily average commits
        burnout_trend = commit_trend

        return {
            "period_days": days,
            "commit_count": recent_count,
            "avg_daily_commits": recent_count / max(days, 1),
            "avg_churn": recent_churn,
            "burnout_trend": burnout_trend,
        }

    @staticmethod
    def parse_commits(log_output: str) -> list[CommitInfo]:
        commits = []
        records = log_output.split("==END==\n")
        for record in records:
            record = record.strip()
            if not record:
                continue
            lines = record.split("\n")
            if len(lines) < 5:
                continue
            try:
                hash_ = lines[0]
                author = lines[1]
                # email = lines[2]  # unused
                timestamp = int(lines[3])
                message = lines[4]
                date = datetime.fromtimestamp(timestamp)
                commits.append(CommitInfo(
                    hash=hash_,
                    author=author,
                    date=date,
                    message=message,
                ))
            except (ValueError, IndexError):
                continue
        return commits
