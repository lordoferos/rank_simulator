# rank_simulator

Ranking algorithms for a forum discussion website, and a simulator to see how they behave before real users arrive.

## The algorithms ([ranking.py](ranking.py))

| Sort | Use it for | How it works |
|---|---|---|
| `hot` | Front page / thread list | Votes count on a log scale (10 votes ≈ 1 point, 100 ≈ 2) and every 12.5 hours of age costs 1 point, so fresh threads can overtake old popular ones. |
| `best` | Replies inside a thread | Lower bound of the Wilson score interval: how good the reply probably is, given how many votes it has. 90 up / 10 down beats 1 up / 0 down. |
| `top` | "Top this week" lists | Upvotes minus downvotes, ignoring age. |
| `new` | Latest activity | Newest first. |

`hot` and `best` follow the formulas Reddit published in its open-source code. `HOT_DECAY` in `ranking.py` sets how fast the front page turns over.

```python
from ranking import Post, rank
front_page = rank(threads, 'hot')
replies = rank(thread_replies, 'best')
```

## The simulator ([simulate.py](simulate.py))

Plays out a day on the forum using the posts in [posts.txt](posts.txt). Each post goes up at a random time with a hidden quality (the chance a reader upvotes it). Every minute visitors arrive; most read the front page, favouring the top slots, and the rest browse at random. Because the ranking decides what people see, and what they see decides the votes, you can watch the feedback loop play out.

```sh
python3 simulate.py                       # 24 hours, sorted by hot
python3 simulate.py --sort top --seed 7   # compare sorts on the same run
python3 simulate.py --help                # hours, visitors, front-page size, ...
```

Each snapshot prints the front page with every post's votes, age and hidden quality. At the end the run gets a **front-page score**: the average quality of the posts on the front page, relative to the best front page possible at that moment, averaged over every minute. 1.00 means readers always saw the best posts available; the random baseline is what picking posts at random would score. It also reports how many of the truly best posts made the final front page.

### Watching a run

```sh
python3 simulate.py --html replay.html --seed 42
open replay.html
```

Writes a self-contained page ([viewer.html](viewer.html) filled with the run) that replays the day minute by minute. Rows slide as the ranking changes, a ★ marks posts that are truly among the best live right now, and the score chart fills in as you go. All four sorts are recorded on the same seed, so you can switch between them and watch the same day play out differently. Space plays and pauses; the arrow keys step through the day.

### Tuning with `--compare`

```sh
python3 simulate.py --compare           # 10 runs per setting, about 2 minutes
python3 simulate.py --compare --runs 3  # quicker, noisier
```

Runs every sort, several `hot` decay speeds (3h, 6h, 12.5h, 24h) and front-page sizes (5, 10, 20) on the same seeds, and ranks the settings by average score. Compare rows with the same page size: with 40 posts, a 20-slot front page shows half of everything, so it scores high whatever the sort.

The score only measures quality. Visitor interest in a post doesn't fade over time in this simulator, so it won't reward freshness the way a real forum would.

## Tests

```sh
python3 -m unittest -v
```

Needs Python 3.8+ and nothing else.
