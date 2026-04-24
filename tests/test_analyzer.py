import pytest
from datetime import datetime, timedelta

from gf.analyzer import Analyzer, CommitInfo, AnalysisResult
from gf.burnout import BurnoutScorer, BurnoutResult


class TestAnalyzer:
    def test_parse_commits_empty(self):
        result = Analyzer.parse_commits("")
        assert result == []

    def test_parse_commits_single(self):
        log = "abc123\nJohn Doe\njohn@example.com\n1609459200\nInitial commit\n==END==\n"
        commits = Analyzer.parse_commits(log)
        assert len(commits) == 1
        assert commits[0].hash == "abc123"
        assert commits[0].author == "John Doe"
        assert commits[0].message == "Initial commit"

    def test_parse_commits_multiple(self):
        log = """abc123
John Doe
john@example.com
1609459200
Initial commit
==END==
def456
Jane Smith
jane@example.com
1609545600
Add feature
==END=="""
        commits = Analyzer.parse_commits(log)
        assert len(commits) == 2
        assert commits[0].hash == "abc123"
        assert commits[1].hash == "def456"

    def test_analyze_empty(self):
        analyzer = Analyzer()
        result = analyzer.analyze([])
        assert result.total_commits == 0
        assert result.total_authors == 0
        assert result.refactor_ratio == 0.0

    def test_analyze_basic(self):
        now = datetime.now()
        commits = [
            CommitInfo(hash="a", author="Alice", date=now, message="Add feature"),
            CommitInfo(hash="b", author="Alice", date=now, message="Fix bug"),
            CommitInfo(hash="c", author="Bob", date=now, message="Refactor code"),
        ]
        analyzer = Analyzer()
        result = analyzer.analyze(commits)

        assert result.total_commits == 3
        assert result.total_authors == 2
        assert result.refactor_ratio == 1/3

    def test_analyze_avg_commit_size(self):
        now = datetime.now()
        commits = [
            CommitInfo(hash="a", author="A", date=now, message="msg", churn=10),
            CommitInfo(hash="b", author="A", date=now, message="msg", churn=20),
            CommitInfo(hash="c", author="A", date=now, message="msg", churn=30),
        ]
        analyzer = Analyzer()
        result = analyzer.analyze(commits)
        assert result.avg_commit_size == 20.0

    def test_analyze_burst_detection(self):
        now = datetime.now()
        day = timedelta(days=1)
        commits = [
            CommitInfo(hash=f"c{i}", author="A", date=now - day * i, message=f"msg {i}", churn=5)
            for i in range(25)
        ]
        # First day has 11 commits = burst
        for i in range(11):
            commits[i].date = now

        analyzer = Analyzer()
        result = analyzer.analyze(commits)
        assert result.burst_count >= 1

    def test_trend_basic(self):
        now = datetime.now()
        commits = [
            CommitInfo(hash="a", author="A", date=now - timedelta(days=1), message="a", churn=10),
            CommitInfo(hash="b", author="A", date=now - timedelta(days=2), message="b", churn=10),
            CommitInfo(hash="c", author="A", date=now - timedelta(days=15), message="c", churn=10),
            CommitInfo(hash="d", author="A", date=now - timedelta(days=16), message="d", churn=10),
        ]
        analyzer = Analyzer()
        result = analyzer.trend(commits, 7)
        assert result["period_days"] == 7
        assert result["commit_count"] == 2

    def test_trend_empty(self):
        analyzer = Analyzer()
        result = analyzer.trend([], 30)
        assert result["commit_count"] == 0
        assert result["avg_daily_commits"] == 0.0


class TestBurnoutScorer:
    def test_score_empty(self):
        scorer = BurnoutScorer()
        result = scorer.score([])
        assert result.score == 0.0
        assert result.late_night_factor == 0.0

    def test_score_no_late_night(self):
        now = datetime.now()
        noon = now.replace(hour=12)
        commits = [
            CommitInfo(hash="a", author="A", date=noon, message="msg"),
            CommitInfo(hash="b", author="A", date=noon, message="msg"),
        ]
        scorer = BurnoutScorer()
        result = scorer.score(commits)
        assert result.late_night_factor == 0.0

    def test_score_late_night(self):
        now = datetime.now()
        late = now.replace(hour=2)  # 2 AM
        commits = [
            CommitInfo(hash="a", author="A", date=late, message="msg"),
            CommitInfo(hash="b", author="A", date=late, message="msg"),
            CommitInfo(hash="c", author="A", date=late, message="msg"),
            CommitInfo(hash="d", author="A", date=late, message="msg"),
        ]
        scorer = BurnoutScorer()
        result = scorer.score(commits)
        assert result.late_night_factor == 30.0  # 100% late night

    def test_score_burst(self):
        now = datetime.now()
        day = timedelta(days=1)
        # 15 commits in one day = burst
        commits = [
            CommitInfo(hash=f"c{i}", author="A", date=now, message=f"msg {i}")
            for i in range(15)
        ]
        scorer = BurnoutScorer()
        result = scorer.score(commits)
        assert result.burst_factor > 0

    def test_score_sentiment(self):
        now = datetime.now()
        commits = [
            CommitInfo(hash="a", author="A", date=now, message="Fix critical bug"),
            CommitInfo(hash="b", author="A", date=now, message="Hotfix production"),
            CommitInfo(hash="c", author="A", date=now, message="Add new feature"),
        ]
        scorer = BurnoutScorer()
        result = scorer.score(commits)
        assert result.sentiment_factor > 0
