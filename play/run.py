"""Play the page's hunts from the command line.

    python run.py list                              the hunts and the hard boards
    python run.py average smart3 --games 20000      shots on random boards, and the win rate against the best strategy
    python run.py board heat heat_worst             the same on one board (each game a random rotation or reflection)
    python run.py board smart3pro "5:22,23,24,25,26 4:64,65,66,67 3:41,51,61 3:46,47,48 2:8,9"
    python run.py race smart3 parity3               head-to-head on random boards

"Win rate against the best strategy" races each game against the finishing times of the best strategy found
(data/pace_best.json), the yardstick of every classic-board win rate on the page. Games run on all cores.
"""
import argparse
import json
import math
import os
import random
from multiprocessing import Pool

import battleship as bs

HERE = os.path.dirname(os.path.abspath(__file__))
PACE = json.load(open(os.path.join(HERE, "data", "pace_best.json")))["credit"]
BOARDS = json.load(open(os.path.join(HERE, "data", "boards.json")))["boards"]


def _games(args):
    name, board, n, seed = args
    rng = random.Random(seed)
    fixed = bs.parse_board(board) if board else None
    out = []
    for _ in range(n):
        layout = bs.transform(fixed, rng.randrange(8)) if fixed else bs.random_layout(rng)
        out.append(bs.play(bs.make(name), layout, rng))
    return out


def run_games(name, board=None, games=10000, seed=1, workers=None):
    """finishing times of `games` games, split over the cores (seeds seed*1000 + chunk)"""
    workers = workers or os.cpu_count() or 1
    chunks = [(name, board, games // workers + (k < games % workers), seed * 1000 + k) for k in range(workers)]
    with Pool(workers) as pool:
        return [t for part in pool.map(_games, chunks) for t in part]


def summary(times):
    n = len(times)
    mean = sum(times) / n
    sd = math.sqrt(sum((t - mean) ** 2 for t in times) / (n - 1))
    credits = [bs.credit(t, PACE) for t in times]
    win = sum(credits) / n
    win_sd = math.sqrt(sum((c - win) ** 2 for c in credits) / (n - 1))
    return {"games": n, "mean_shots": mean, "mean_shots_se": sd / math.sqrt(n),
            "win_rate_vs_best": win, "win_rate_vs_best_se": win_sd / math.sqrt(n)}


def show(label, s):
    print("%s: %d games, %.2f shots (se %.2f), wins %.1f%% against the best strategy (se %.1f)" % (
        label, s["games"], s["mean_shots"], s["mean_shots_se"], 100 * s["win_rate_vs_best"], 100 * s["win_rate_vs_best_se"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["list", "average", "board", "race"])
    ap.add_argument("hunt", nargs="?")
    ap.add_argument("other", nargs="?", help="a board name or spec (board) or a second hunt (race)")
    ap.add_argument("--games", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    if a.what == "list":
        print("hunts:", ", ".join(sorted(bs.HUNTS)))
        for k, v in BOARDS.items():
            print("board %-15s %s\n    %s" % (k, v["board"], v["page"]))
        return
    if a.hunt not in bs.HUNTS:
        ap.error("unknown hunt %r (try: %s)" % (a.hunt, ", ".join(sorted(bs.HUNTS))))
    if a.what == "average":
        show(a.hunt + ", random boards", summary(run_games(a.hunt, None, a.games, a.seed, a.workers)))
    elif a.what == "board":
        board = BOARDS[a.other]["board"] if a.other in BOARDS else a.other
        show("%s, board %s" % (a.hunt, board), summary(run_games(a.hunt, board, a.games, a.seed, a.workers)))
    else:
        if a.other not in bs.HUNTS:
            ap.error("race needs two hunts")
        ta = run_games(a.hunt, None, a.games, a.seed, a.workers)
        tb = run_games(a.other, None, a.games, a.seed + 1, a.workers)
        print("%s beats %s in %.1f%% of races on random boards (%d games each)" % (a.hunt, a.other, 100 * bs.race(ta, tb), a.games))


if __name__ == "__main__":
    main()
