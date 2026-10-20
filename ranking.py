"""
Ranking algorithms for a forum discussion website.

- hot:  orders threads on the front page. Votes count on a log scale and
        newer posts get a steady boost, so fresh discussions can rise and
        old ones sink even if they once had many votes.
- best: orders replies inside a thread. Uses the lower bound of the Wilson
        score interval, so a reply with 1 upvote and 0 downvotes does not
        outrank one with 90 up and 10 down.
- top:  net score (ups - downs), ignoring age.
- new:  newest first.

hot and best follow the formulas Reddit published in its open-source code.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from math import log10, sqrt

# Set reference time
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# Reddit's launch (2005-12-08). Subtracting it only keeps hot values small;
# it does not change the order.
LAUNCH_SECONDS = 1134028003

# Seconds of age that cost the same as a 10x difference in votes (12.5 hours).
# Lower it to make the front page turn over faster.
HOT_DECAY = 45000

# z for an 80% confidence interval, the value Reddit uses for "best".
BEST_Z = 1.281551565545


@dataclass
class Post:
    id: int
    text: str
    created: datetime
    ups: int = 0
    downs: int = 0
    # Chance that a reader upvotes. Only the simulator uses it; a real
    # forum never knows it.
    quality: float = 0.5


def epoch_seconds(date):
    # Naive datetimes are treated as UTC
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return (date - EPOCH).total_seconds()


def score(ups, downs):
    return ups - downs


def hot(ups, downs, date, decay=HOT_DECAY):
    s = score(ups, downs)
    order = log10(max(abs(s), 1))
    sign = 1 if s > 0 else -1 if s < 0 else 0
    seconds = epoch_seconds(date) - LAUNCH_SECONDS
    return round(sign * order + seconds / decay, 7)


def best(ups, downs, z=BEST_Z):
    n = ups + downs
    if n == 0:
        return 0.0
    p = ups / n
    return (p + z * z / (2 * n) - z * sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / (1 + z * z / n)


SORTS = {
    'hot': lambda post, decay: hot(post.ups, post.downs, post.created, decay),
    'best': lambda post, decay: best(post.ups, post.downs),
    'top': lambda post, decay: score(post.ups, post.downs),
    'new': lambda post, decay: post.created,
}


def rank(posts, by='hot', decay=HOT_DECAY):
    """Return posts ordered best-first by the named sort.

    decay only affects 'hot': seconds of age worth a 10x difference in votes.
    """
    if by not in SORTS:
        raise ValueError(f"unknown sort {by!r}; choose from {', '.join(SORTS)}")
    key = SORTS[by]
    return sorted(posts, key=lambda post: key(post, decay), reverse=True)
