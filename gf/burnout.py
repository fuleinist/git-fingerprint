from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class BurnoutResult:
    score: float  # 0-100
    late_night_factor: float  # 0-30
    frequency_spike_factor: float  # 0-30
    burst_factor: float  # 0-25
    sentiment_factor: float  # 0-15
    breakdown: dict[str, float]


class BurnoutScorer:
    LATE_NIGHT_START = 23  # 11 PM
    LATE_NIGHT_END = 5     # 5 AM
    BURST_THRESHOLD = 10   # commits per day

    def score(self, commits: list) -> BurnoutResult:
        if not commits:
            return BurnoutResult(
                score=0.0,
                late_night_factor=0.0,
                frequency_spike_factor=0.0,
                burst_factor=0.0,
                sentiment_factor=0.0,
                breakdown={},
            )

        # Late night commits factor (0-30)
        late_night = sum(1 for c in commits
                        if c.date.hour >= self.LATE_NIGHT_START or c.date.hour < self.LATE_NIGHT_END)
        late_night_ratio = late_night / len(commits)
        late_night_factor = min(late_night_ratio * 100, 30.0)

        # Frequency spike/drop - compare last 7 days to prior 7 days
        now = datetime.now()
        recent_cutoff = now - timedelta(days=7)
        older_cutoff = now - timedelta(days=14)

        recent_commits = [c for c in commits if c.date >= recent_cutoff]
        older_commits = [c for c in commits if older_cutoff <= c.date < recent_cutoff]

        recent_rate = len(recent_commits) / 7.0
        older_rate = len(older_commits) / 7.0

        if older_rate > 0:
            spike_ratio = recent_rate / older_rate
        else:
            spike_ratio = recent_rate if recent_rate > 0 else 1.0

        # Both spikes and drops are concerning
        if spike_ratio > 1.5:
            frequency_spike_factor = min((spike_ratio - 1.5) * 20, 30.0)
        elif spike_ratio < 0.5:
            frequency_spike_factor = min((0.5 - spike_ratio) * 40, 30.0)
        else:
            frequency_spike_factor = 0.0

        # Burst factor: too many commits in short time
        daily_counts: dict[str, int] = defaultdict(int)
        for c in commits:
            daily_counts[c.date.strftime("%Y-%m-%d")] += 1

        burst_days = sum(1 for count in daily_counts.values() if count > self.BURST_THRESHOLD)
        burst_factor = min(burst_days * 5, 25.0)

        # Sentiment factor (simple keyword detection)
        negative_keywords = ["fix", "bug", "hotfix", "urgent", "critical", "emergency", "hack", "workaround"]
        positive_keywords = ["feat", "add", "implement", "improve", "refactor", "test", "docs"]

        negative_count = sum(1 for c in commits if any(k in c.message.lower() for k in negative_keywords))
        positive_count = sum(1 for c in commits if any(k in c.message.lower() for k in positive_keywords))

        total_keywords = negative_count + positive_count
        if total_keywords > 0:
            neg_ratio = negative_count / total_keywords
            sentiment_factor = min(neg_ratio * 15, 15.0)
        else:
            sentiment_factor = 0.0

        # Total score
        total = late_night_factor + frequency_spike_factor + burst_factor + sentiment_factor
        score = min(total, 100.0)

        breakdown = {
            "late_night_commits": late_night,
            "late_night_ratio": round(late_night_ratio * 100, 1),
            "recent_daily_avg": round(recent_rate, 2),
            "older_daily_avg": round(older_rate, 2),
            "spike_ratio": round(spike_ratio, 2),
            "burst_days": burst_days,
            "negative_commits": negative_count,
            "positive_commits": positive_count,
        }

        return BurnoutResult(
            score=round(score, 1),
            late_night_factor=round(late_night_factor, 1),
            frequency_spike_factor=round(frequency_spike_factor, 1),
            burst_factor=round(burst_factor, 1),
            sentiment_factor=round(sentiment_factor, 1),
            breakdown=breakdown,
        )
