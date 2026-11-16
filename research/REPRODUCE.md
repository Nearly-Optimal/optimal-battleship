# Reproducing the page

Every figure and table on [optimalbattleship.com](https://optimalbattleship.com), in page order, with the code and data
behind it. **Status**: *done* = reproducible from this repository today; *to port* = produced by research code that is
being cleaned up for release here.

| Section | Item | What it shows | Code and data | Status |
|---|---|---|---|---|
| 1 | Figure 1, three obvious hunts | the checkerboard and 3-parity sets on an empty board, the heat map's counts | `play/battleship.py` (`Stripes`, `diagonal_class`, `density`) | done |
| 1 | Head to head on random boards | each simple hunt raced against each other | `python3 play/run.py race <hunt> <hunt>` | done (3-parity's lucky/unlucky split: to port) |
| 1 | Figure 2, the heat map's worst board | the board, and the heat map's 66.2 shots on it | `play/data/boards.json`, `python3 play/run.py board heat heat_worst` | done |
| 1 | Table 1 | average and worst board found for each hunt, against the best strategy | `play/validate.py` (checkerboard, plain 3-parity, heat map); the best strategy's row needs the classic engine | done except the best strategy |
| 2 | The smart 3-parity card | 48.1 shots; 47% of races on random boards, ≤ 35.8% on its worst board found | `play/battleship.py` (`Smart3`), `python3 play/run.py board smart3 smart3_worst` | done |
| 2 | Figure 3, how to play smart 3-parity | one real game, step by step | `Smart3`; the exact game drawn on the page: to port | partly |
| 2 | Figure 4, why it works | the color imbalance when both 3s are sunk, over about 66,000 games | to port | to port |
| 3 | Figure 5 and Replay 1 | exact 5×5 results: near-perfect play, hand rules | exact dynamic programming + linear programming pipeline | to port |
| 4 | Figure 6 and Replay 2 | the 10×10 {3,3,2} self-play mixture | self-play column generation, race scoring | to port |
| 5 | Figure 7 | 72 classic-fleet strategies, average against worst | classic rules engine, benchmark harness, board searches; six of the strategies are in `play/` | partly |
| 5 | Figure 8 | finishing times on random boards and on each strategy's worst board found | `python3 play/run.py average` / `board` for smart 3-parity, pro, the heat map, the checkerboard and plain 3-parity; the best strategy needs the classic engine | partly |
| 5 | Replay 3 | the best strategy found, shot by shot | exact replay engine | to port |
| 5 | Smart 3-parity pro | its five changes; 47.5 shots, 48.5% and ≤ 38.6% | `play/battleship.py` (`Smart3Pro`), `python3 play/run.py board smart3pro smart3pro_worst` | done |
| 6 | Figure 9 | every third diagonal | geometry, `play/battleship.py` | done |
| 6 | Figure 10 and the plain plan's extra rule | guarantees of the large-board plans | exact large-board model and solvers | to port |
| 7 | Hiding rules on the classic board | each hunt against five hiding rules | the hunts are in `play/`; the samplers for each hiding rule are to port; the best strategy needs the classic engine | partly |

Worst cases come from searches for hard boards, so each one is an upper bound on the hunt's true worst case; the
[classic-fleet page](https://optimalbattleship.com/classic) describes the searches.
