"""Check battleship.py against the rules engine behind the page: same hunts, same boards, independent random numbers.

    python validate.py [--games 20000] [--board-games 8000]

For every hunt: the average number of shots and the win rate against the best strategy on random boards, then the same
on the hardest board the page's searches found against it. The engine's values come from the page's runs (32,000
random boards x 8 rotations/reflections; on a board 8,000 or 1,024,000 games), raced against the same pace
(data/pace_best.json). Each gap is in standard errors of the difference (this code's and the engine's sampling errors
combined; the engine's for shots estimated from this code's spread); gaps of a few standard errors or less mean this
code plays the same hunt. Writes validation.json next to this file.
"""
import argparse
import json
import math
import os

import run

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = {   # hunt: (random boards: games, shots, win rate, its se), (hard board: name, games, shots, win rate, its se)
    "random": ((1024000, 59.7219, 0.24688, 0.00029), ("random_worst", 1024000, 62.3244, 0.19003, 0.00024)),
    "checker": ((256000, 51.3906, 0.35411, 0.00053), ("checker_worst", 8000, 54.2844, 0.27397, 0.00258)),
    "parity3": ((256000, 49.2748, 0.45041, 0.00056), ("parity3_worst", 1024000, 52.5147, 0.34320, 0.00024)),
    "smart3": ((256000, 48.0737, 0.46901, 0.00055), ("smart3_worst", 1024000, 51.2168, 0.35748, 0.00022)),
    "smart3pro": ((256000, 47.4968, 0.48519, 0.00055), ("smart3pro_worst", 1024000, 50.5027, 0.38497, 0.00025)),
    "heat": ((256000, 44.8261, 0.56911, 0.00058), ("heat_worst", 8000, 66.2449, 0.03772, 0.00026)),
}


def line(label, s, games, ref_t, ref_w, ref_w_se):
    t_se = s["mean_shots_se"] * math.sqrt(1 + s["games"] / games)
    w_se = math.hypot(s["win_rate_vs_best_se"], ref_w_se)
    dt = (s["mean_shots"] - ref_t) / t_se
    dw = (s["win_rate_vs_best"] - ref_w) / w_se
    print("%-26s shots %6.2f (engine %6.2f, %+5.1f se)   win rate %5.2f%% (engine %5.2f%%, %+5.1f se)" % (
        label, s["mean_shots"], ref_t, dt, 100 * s["win_rate_vs_best"], 100 * ref_w, dw), flush=True)
    return {"games": s["games"], "mean_shots": s["mean_shots"], "se": s["mean_shots_se"], "engine_games": games,
            "engine_shots": ref_t, "shots_dev_se": dt, "win_rate": s["win_rate_vs_best"],
            "win_rate_se": s["win_rate_vs_best_se"], "engine_win_rate": ref_w, "engine_win_rate_se": ref_w_se,
            "win_rate_dev_se": dw}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games", type=int, default=20000)
    ap.add_argument("--board-games", type=int, default=8000)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    out = {}
    for hunt, ((games, rt, rw, rw_se), (bname, bgames, bt, bw, bw_se)) in ENGINE.items():
        s = run.summary(run.run_games(hunt, None, a.games, a.seed))
        out[hunt + " random boards"] = line(hunt + ", random boards", s, games, rt, rw, rw_se)
        s = run.summary(run.run_games(hunt, run.BOARDS[bname]["board"], a.board_games, a.seed + 1))
        out[hunt + " " + bname] = line(hunt + ", " + bname, s, bgames, bt, bw, bw_se)
    worst = max(max(abs(v["shots_dev_se"]), abs(v["win_rate_dev_se"])) for v in out.values())
    print("largest gap: %.1f standard errors (%d comparisons)" % (worst, 2 * len(out)))
    json.dump(out, open(os.path.join(HERE, "validation.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
