"""Run with: python3 -m unittest -v"""

import unittest
from datetime import datetime, timedelta, timezone

from ranking import HOT_DECAY, Post, best, hot, rank
from simulate import front_page_score, load_posts, simulate

NOW = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)


class HotTest(unittest.TestCase):
    def test_newer_post_wins_on_equal_votes(self):
        self.assertGreater(hot(10, 0, NOW), hot(10, 0, NOW - timedelta(hours=1)))

    def test_ten_times_the_votes_offsets_one_decay_period(self):
        older = hot(100, 0, NOW - timedelta(seconds=HOT_DECAY))
        newer = hot(10, 0, NOW)
        self.assertAlmostEqual(older, newer, places=5)

    def test_negative_score_ranks_below_zero(self):
        self.assertLess(hot(0, 5, NOW), hot(0, 0, NOW))
        self.assertLess(hot(0, 0, NOW), hot(5, 0, NOW))

    def test_naive_datetime_is_treated_as_utc(self):
        self.assertEqual(hot(3, 1, NOW), hot(3, 1, NOW.replace(tzinfo=None)))


class BestTest(unittest.TestCase):
    def test_no_votes_scores_zero(self):
        self.assertEqual(best(0, 0), 0.0)

    def test_more_evidence_beats_a_lucky_single_vote(self):
        self.assertGreater(best(90, 10), best(1, 0))

    def test_stays_between_zero_and_one(self):
        for ups, downs in [(1, 0), (0, 1), (1000, 0), (0, 1000), (50, 50)]:
            self.assertTrue(0 <= best(ups, downs) <= 1)


class RankTest(unittest.TestCase):
    def setUp(self):
        self.old_popular = Post(1, 'old', NOW - timedelta(days=2), ups=200)
        self.fresh = Post(2, 'fresh', NOW, ups=5)
        self.contested = Post(3, 'contested', NOW - timedelta(hours=1), ups=40, downs=35)
        self.posts = [self.old_popular, self.fresh, self.contested]

    def test_hot_lets_fresh_posts_overtake_old_ones(self):
        self.assertEqual(rank(self.posts, 'hot')[0], self.fresh)

    def test_top_ignores_age(self):
        self.assertEqual(rank(self.posts, 'top')[0], self.old_popular)

    def test_new_is_newest_first(self):
        self.assertEqual([p.id for p in rank(self.posts, 'new')], [2, 3, 1])

    def test_best_puts_the_contested_post_last(self):
        self.assertEqual(rank(self.posts, 'best')[-1], self.contested)

    def test_unknown_sort_is_rejected(self):
        with self.assertRaises(ValueError):
            rank(self.posts, 'random')


class SimulateTest(unittest.TestCase):
    texts = [f'post {i}' for i in range(20)]

    def test_loads_posts_without_quotes_or_blank_lines(self):
        texts = load_posts('posts.txt')
        self.assertEqual(len(texts), 40)
        self.assertFalse(any(t.startswith('"') or t.endswith('"') for t in texts))

    def test_same_seed_gives_same_result(self):
        votes = lambda result: [(p.ups, p.downs) for p in result.posts]
        first, second = simulate(self.texts, hours=6, seed=1), simulate(self.texts, hours=6, seed=1)
        self.assertEqual(votes(first), votes(second))
        self.assertEqual(first.score, second.score)

    def test_votes_are_cast(self):
        posts = simulate(self.texts, hours=6, seed=1).posts
        self.assertGreater(sum(p.ups + p.downs for p in posts), 0)

    def test_snapshots_only_show_posts_that_exist_yet(self):
        def check(now, ordered):
            self.assertTrue(all(p.created <= now for p in ordered))
        simulate(self.texts, hours=6, seed=1, snapshot_every=1, on_snapshot=check)

    def test_decay_changes_hot_results(self):
        fast = simulate(self.texts, hours=12, seed=1, decay=3600)
        slow = simulate(self.texts, hours=12, seed=1, decay=86400)
        self.assertNotEqual(fast.score, slow.score)


class FrontPageScoreTest(unittest.TestCase):
    def posts(self, *qualities):
        return [Post(i, '', NOW, quality=q) for i, q in enumerate(qualities)]

    def test_best_posts_first_scores_one(self):
        self.assertEqual(front_page_score(self.posts(0.9, 0.8, 0.1, 0.2), 2)[0], 1.0)

    def test_worst_posts_first_scores_below_random(self):
        page, random_page = front_page_score(self.posts(0.1, 0.2, 0.9, 0.8), 2)
        self.assertLess(page, random_page)
        self.assertAlmostEqual(page, 0.15 / 0.85)

    def test_short_list_is_scored_on_what_exists(self):
        self.assertEqual(front_page_score(self.posts(0.5, 0.7), 10)[0], 1.0)

    def test_hits_count_best_posts_on_final_page(self):
        result = simulate([f'post {i}' for i in range(20)], hours=6, seed=1, front_page=5)
        self.assertTrue(0 <= result.hits <= 5)
        self.assertTrue(0 < result.score <= 1)


if __name__ == '__main__':
    unittest.main()
