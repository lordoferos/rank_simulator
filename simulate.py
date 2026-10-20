"""
Simulate a day on a forum discussion website and watch the front page change.

Posts from posts.txt go up at random times, each with a hidden quality
(the chance a reader upvotes it). Every simulated minute some visitors
arrive. Most read the front page, favouring the top slots; the rest browse
at random. Each visitor may vote, and the ranking is recalculated before
the next minute, so a post's position affects how many votes it gets.

Each run is scored on how good the front page was: 1.00 means it always
showed the best posts available, and the random baseline is what picking
posts at random would score.

    python3 simulate.py
    python3 simulate.py --sort top --hours 48 --seed 7
    python3 simulate.py --compare
"""

import argparse
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import exp
from pathlib import Path
from statistics import mean

from ranking import HOT_DECAY, Post, SORTS, rank, score

# Share of visitors who read the front page rather than browsing at random
FRONT_PAGE_SHARE = 0.85

# Of the readers who don't upvote, the share who downvote (the rest don't vote)
DOWNVOTE_SHARE = 0.3

# Posts go up during this share of the run, so late posts still get read
POSTING_WINDOW = 0.8

# A fixed start keeps seeded runs repeatable
START = datetime(2026, 1, 5, 6, 0, tzinfo=timezone.utc)

# Settings tried by --compare. Decay is in hours; it only applies to hot.
COMPARE_DECAYS = [3, 6, HOT_DECAY / 3600, 24]
COMPARE_FRONT_PAGES = [5, 10, 20]


@dataclass
class Result:
    posts: list
    # Front-page quality averaged over every minute of the run, 0 to 1
    score: float
    # What a front page of randomly chosen posts would have scored
    random_score: float
    # How many of the truly best posts were on the final front page
    hits: int
    front_page: int


def load_posts(path):
    """Read one post per line, dropping blank lines and surrounding quotes."""
    texts = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        text = line.strip()
        if len(text) >= 2 and text[0] == text[-1] == '"':
            text = text[1:-1].strip()
        if text:
            texts.append(text)
    return texts


def poisson(rng, mean):
    # Knuth's method; fine for the small means used here
    limit, k, p = exp(-mean), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def pick_post(rng, ordered, front_page):
    if rng.random() < FRONT_PAGE_SHARE:
        page = ordered[:front_page]
        # Slot 1 gets read twice as often as slot 2, three times slot 3, ...
        return rng.choices(page, weights=[1 / (i + 1) for i in range(len(page))])[0]
    return rng.choice(ordered)


def vote(rng, post):
    r = rng.random()
    if r < post.quality:
        post.ups += 1
    elif r < post.quality + (1 - post.quality) * DOWNVOTE_SHARE:
        post.downs += 1


def front_page_score(ordered, front_page):
    """Quality of the posts shown, relative to the best front page possible.

    Returns (score, random_score), both relative to that best page.
    """
    shown = ordered[:front_page]
    ideal = sorted((p.quality for p in ordered), reverse=True)[:len(shown)]
    return (mean(p.quality for p in shown) / mean(ideal),
            mean(p.quality for p in ordered) / mean(ideal))


def simulate(texts, hours=24, visitors_per_hour=600, front_page=10, sort='hot',
             decay=HOT_DECAY, seed=None, snapshot_every=6, on_snapshot=None):
    """Run the simulation and return a Result.

    decay is in seconds, as in ranking.hot.
    on_snapshot(now, ordered) is called every snapshot_every hours and at the end.
    """
    rng = random.Random(seed)
    minutes = int(hours * 60)
    posts = [
        Post(
            id=i,
            text=text,
            created=START + timedelta(minutes=rng.uniform(0, minutes * POSTING_WINDOW)),
            quality=rng.betavariate(2, 3),
        )
        for i, text in enumerate(texts, start=1)
    ]
    scores, random_scores = [], []

    for minute in range(1, minutes + 1):
        now = START + timedelta(minutes=minute)
        ordered = rank([p for p in posts if p.created <= now], sort, decay)
        if ordered:
            page_score, random_score = front_page_score(ordered, front_page)
            scores.append(page_score)
            random_scores.append(random_score)
            for _ in range(poisson(rng, visitors_per_hour / 60)):
                vote(rng, pick_post(rng, ordered, front_page))
        if on_snapshot and (minute == minutes or minute % int(snapshot_every * 60) == 0):
            on_snapshot(now, rank([p for p in posts if p.created <= now], sort, decay))

    final = rank([p for p in posts if p.created <= now], sort, decay)[:front_page]
    best_posts = sorted(posts, key=lambda p: p.quality, reverse=True)[:front_page]
    return Result(
        posts=posts,
        score=mean(scores) if scores else 0.0,
        random_score=mean(random_scores) if random_scores else 0.0,
        hits=len({p.id for p in final} & {p.id for p in best_posts}),
        front_page=front_page,
    )


def format_age(delta):
    minutes = int(delta.total_seconds() // 60)
    return f"{minutes // 60}h{minutes % 60:02d}" if minutes >= 60 else f"{minutes}m"


def format_hours(hours):
    return f"{hours:g}h"


def print_page(now, ordered, sort, show, width=60):
    elapsed = format_age(now - START)
    print(f"\nFront page at {now:%a %H:%M} ({elapsed} in), sorted by {sort}")
    print(f"{'#':>3} {'score':>6} {'up':>5} {'down':>5} {'age':>6} {'quality':>8}  post")
    for i, post in enumerate(ordered[:show], start=1):
        text = post.text if len(post.text) <= width else post.text[:width - 1] + '…'
        print(f"{i:>3} {score(post.ups, post.downs):>+6} {post.ups:>5} {post.downs:>5} "
              f"{format_age(now - post.created):>6} {post.quality:>8.2f}  {text}")


def print_result(result):
    print(f"\nFront-page score: {result.score:.2f}  "
          f"(random front page: {result.random_score:.2f}, perfect: 1.00)")
    print(f"At the end, {result.hits} of the {result.front_page} best posts were on the front page.")


def compare(texts, runs, hours, visitors_per_hour):
    """Score every sort, decay and front-page size over the same seeds."""
    settings = [('hot', d) for d in COMPARE_DECAYS] + [(s, None) for s in SORTS if s != 'hot']
    rows, baselines = [], []
    for sort, decay_hours in settings:
        for front_page in COMPARE_FRONT_PAGES:
            results = [
                simulate(texts, hours=hours, visitors_per_hour=visitors_per_hour,
                         front_page=front_page, sort=sort, seed=seed,
                         decay=(decay_hours or HOT_DECAY / 3600) * 3600)
                for seed in range(1, runs + 1)
            ]
            scores = [r.score for r in results]
            baselines += [r.random_score for r in results]
            rows.append((mean(scores), min(scores), max(scores), sort, decay_hours, front_page,
                         mean(r.hits for r in results)))

    print(f"\nFront-page score over {runs} runs of {format_hours(hours)} each "
          f"(1.00 = always showed the best posts; random = {mean(baselines):.2f})\n")
    print(f"{'sort':<5} {'decay':>6} {'page':>5} {'score':>6} {'range':>11} {'best posts on final page':>26}")
    for avg, low, high, sort, decay_hours, front_page, hits in sorted(rows, reverse=True):
        decay = format_hours(decay_hours) if decay_hours else '-'
        print(f"{sort:<5} {decay:>6} {front_page:>5} {avg:>6.2f} {f'{low:.2f}–{high:.2f}':>11} "
              f"{f'{hits:.1f} of {front_page}':>26}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--posts', default=Path(__file__).with_name('posts.txt'),
                        help='text file with one post per line (default: posts.txt)')
    parser.add_argument('--sort', choices=SORTS, default='hot')
    parser.add_argument('--decay', type=float, default=HOT_DECAY / 3600,
                        help='hot only: hours of age worth a 10x difference in votes (default: 12.5)')
    parser.add_argument('--hours', type=float, default=24, help='length of the run (default: 24)')
    parser.add_argument('--visitors', type=int, default=600, help='visitors per hour (default: 600)')
    parser.add_argument('--front-page', type=int, default=10, help='posts on the front page (default: 10)')
    parser.add_argument('--every', type=float, default=6, help='hours between snapshots (default: 6)')
    parser.add_argument('--show', type=int, default=10, help='rows per snapshot (default: 10)')
    parser.add_argument('--seed', type=int, help='random seed, for repeatable runs')
    parser.add_argument('--compare', action='store_true',
                        help='score every sort, decay and front-page size instead of one run')
    parser.add_argument('--runs', type=int, default=10, help='--compare only: runs per setting (default: 10)')
    args = parser.parse_args()
    texts = load_posts(args.posts)

    if args.compare:
        compare(texts, args.runs, args.hours, args.visitors)
        return

    result = simulate(
        texts,
        hours=args.hours,
        visitors_per_hour=args.visitors,
        front_page=args.front_page,
        sort=args.sort,
        decay=args.decay * 3600,
        seed=args.seed,
        snapshot_every=args.every,
        on_snapshot=lambda now, ordered: print_page(now, ordered, args.sort, args.show),
    )
    print_result(result)


if __name__ == '__main__':
    main()
