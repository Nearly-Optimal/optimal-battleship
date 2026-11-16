# Optimal Battleship

Code and data behind [optimalbattleship.com](https://optimalbattleship.com): how good the simple Battleship hunts are,
how close they come to the best strategies we could compute, and why the fastest hunt on random boards can be the
easiest one to beat. There is also a [7-minute video](https://www.youtube.com/watch?v=Obusq8kjxCo). A
[Nearly Optimal](https://nearlyoptimal.com) project.

## What is here

- **[`play/`](play/)**: the page's six hunts (random hunt, checkerboard, plain 3-parity, smart 3-parity, smart 3-parity
  pro, heat map) in one readable Python file, a command-line runner, and a check against the research engine. Start
  here.
- **[`research/`](research/)**: the engines and pipelines that produced the page's numbers, with
  [`REPRODUCE.md`](research/REPRODUCE.md) mapping each figure and table to the code and data behind it. Being filled in.

## Quick start

Python 3.10 or later, standard library only.

    cd play
    python3 run.py list                              # the hunts and the hard boards
    python3 run.py average smart3 --games 20000      # shots on random boards, win rate against the best strategy
    python3 run.py board heat heat_worst             # the heat map on the board that beats it
    python3 run.py board smart3pro smart3pro_worst   # pro on the hardest board found against it
    python3 run.py race smart3pro parity3            # head to head on random boards
    python3 test_battleship.py                       # quick checks, a few seconds

## The rules

A 10×10 board and a fleet of ships of 5, 4, 3, 3 and 2 cells. Ships are straight, inside the board, may touch but not
overlap. Every shot is announced as a miss, a hit, or "you sank a ship of size k" (the size only, not which cells). Two
players race: whoever sinks the other's fleet first wins, and a finish in the same round counts half. A hunt's
**win rate against the best strategy** is its chance of winning that race against the best strategy found, which hunts
a randomly hidden fleet ([`play/data/pace_best.json`](play/data/pace_best.json)); it is the yardstick of every
classic-board win rate on the page.

## The hunts

| Hunt | Name in `play/` | Average shots | Win rate, random boards | Win rate, worst board found |
|---|---|---|---|---|
| Random hunt | `random` | 59.7 | 24.7% | ≤ 19.1% |
| Checkerboard | `checker` | 51.4 | 35.4% | ≤ 27.2% |
| Plain 3-parity | `parity3` | 49.3 | 45.0% | ≤ 34.4% |
| Smart 3-parity | `smart3` | 48.1 | 46.9% | ≤ 35.8% |
| Smart 3-parity pro | `smart3pro` | 47.5 | 48.5% | ≤ 38.6% |
| Heat map | `heat` | 44.8 | 56.9% | ≤ 3.8% |
| Best strategy found | (research engine) | 47.2 | 50% | ≤ 44.5% |

The page's numbers (Table 1 and section 5; the random hunt is not on the page). Worst boards come from searches, so
their win rates are upper bounds. The cards for smart 3-parity and pro are in sections 2 and 5 of the page; `Smart3`
and `Smart3Pro` in [`play/battleship.py`](play/battleship.py) follow them, including two details the cards leave out:
the 2 is hunted only where it could still be (next to an unshot cell), and pro's edge weight leaves the four corners
at full weight.

## Do the Python hunts match the page?

`play/validate.py` replays each hunt on random boards (128,000 games) and on its worst board found (64,000 games, each
in a random rotation or reflection), and compares with the engine's runs behind the page (32,000 random boards in all
eight rotations and reflections; 8,000 or 1,024,000 games on a board), all racing the same pace:

| Hunt | Shots, random boards | Win rate, random boards | Shots, worst board | Win rate, worst board |
|---|---|---|---|---|
| Random hunt | 59.77 (59.72) | 24.62% (24.69%) | 62.40 (62.32) | 18.86% (19.00%) |
| Checkerboard | 51.36 (51.39) | 35.55% (35.41%) | 54.27 (54.28) | 27.34% (27.40%) |
| Plain 3-parity | 49.28 (49.27) | 44.99% (45.04%) | 52.48 (52.51) | 34.36% (34.32%) |
| Smart 3-parity | 48.11 (48.07) | 46.79% (46.90%) | 51.23 (51.22) | 35.70% (35.75%) |
| Smart 3-parity pro | 47.51 (47.50) | 48.48% (48.52%) | 50.47 (50.50) | 38.57% (38.50%) |
| Heat map | 44.80 (44.83) | 57.04% (56.91%) | 66.25 (66.24) | 3.75% (3.77%) |

This code first, the engine in parentheses. All 24 differences are within 1.5 standard errors (about 0.03 shots and
0.1 points of win rate here; [`play/validation.json`](play/validation.json) has them all). For the checkerboard and the
heat map the engine's worst-board values are 8,000 fresh games against the final pace, so they differ slightly from the
page's search values (≤ 27.2% and ≤ 3.8%).

## The best strategy found

It is not in `play/`: it is the hunts of the 10×10 {3,3,2} self-play mixture, re-weighted for the full fleet together
with a few other hunts, and its three-ship hunts need the research engine (see `research/`). Its finishing times on
random boards are the pace in [`play/data/pace_best.json`](play/data/pace_best.json), and its worst board found is
`best_worst` in [`play/data/boards.json`](play/data/boards.json).

## License

Code: MIT (see [`LICENSE`](LICENSE)). Data and text: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Battleship is a trademark of Hasbro; this project is not affiliated with Hasbro.
