# Research code

The engines and pipelines behind the page's numbers. Being moved here from the project's working tree, cleaned up and
documented; [`REPRODUCE.md`](REPRODUCE.md) tracks what is here and what is still to come.

Planned layout:

- `classic/`: the C++ rules engine for the classic fleet (the hand-written rules, the heat map, smart 3-parity, pro
  and their variants), the benchmark harness (random boards, races against a pace, searches for hard boards), the
  registry of the 72 strategies on the page, and the re-weighting program that produced the best strategy found.
- `small-boards/`: the exact 4×4 and 5×5 pipeline (dynamic programming over every state of knowledge, linear programs
  over the hunts found).
- `self-play/`: the 10×10 {3,3,2} self-play loop (column generation with a race-scored linear program).
- `large-board/`: the exact large-board model and its solvers (the plans of Figure 10, certified and proven bounds).

Large outputs (multi-gigabyte tables and game logs) will be published as release assets or described with the command
that regenerates them, not stored in the repository.
