"""Quick checks of battleship.py (seconds). Run: python3 test_battleship.py   (or: python3 -m pytest)"""
import random

import battleship as bs


def test_random_layouts_are_legal():
    rng = random.Random(1)
    for _ in range(500):
        ships = bs.random_layout(rng)
        assert [bin(m).count("1") for m in ships] == list(bs.FLEET)
        occupied = 0
        for m in ships:
            assert m in bs.PLACEMENTS[bin(m).count("1")]
            assert not occupied & m
            occupied |= m


def test_placement_counts():
    # horizontal + vertical placements of a k-cell ship on 10x10: 2 * 10 * (11 - k)
    for k in (2, 3, 4, 5):
        assert len(bs.PLACEMENTS[k]) == 2 * 10 * (11 - k)


def test_parse_and_transform():
    ships = bs.parse_board("5:47,57,67,77,87 4:20,21,22,23 3:10,11,12 3:13,14,15 2:0,1")
    for d4 in range(8):
        t = bs.transform(ships, d4)
        assert sorted(bin(m).count("1") for m in t) == [2, 3, 3, 4, 5]
        assert bs.transform(t, 0) == t
    assert bs.transform(ships, 0) == ships


def test_sink_attribution_simple():
    # a horizontal 3 at cells 0, 1, 2 hit left to right: the sink at cell 2 claims all three cells
    obs = bs.Observation()
    obs.shots = obs.hits = 0b111
    obs.sinks = [(2, 3, 0b111)]
    obs.remaining = [5, 4, 3, 2]
    assert bs.sunk_cells(obs) == 0b111
    assert bs.open_hits(obs) == 0


def test_finisher_extends_a_line():
    obs = bs.Observation()
    obs.shots = obs.hits = bs.bit(44) | bs.bit(45)          # two hits in a row, nothing sunk
    rng = random.Random(3)
    picks = {bs.finisher(obs, rng) for _ in range(200)}
    assert picks == {43, 46}


def test_every_hunt_finishes_on_every_board():
    rng = random.Random(5)
    for name in sorted(bs.HUNTS):
        for _ in range(30):
            t = bs.play(bs.make(name), bs.random_layout(rng), rng)
            assert 17 <= t <= 100, (name, t)


def test_race():
    assert bs.race([10, 10], [20, 20]) == 1.0
    assert bs.race([15], [15]) == 0.5
    assert abs(bs.race([10, 20], [15]) - 0.5) < 1e-12


def _misses_except(keep, remaining=bs.FLEET):
    """an observation where every cell but `keep` was a miss"""
    obs = bs.Observation()
    obs.shots = bs.FULL & ~sum(bs.bit(i) for i in keep)
    obs.remaining = list(remaining)
    return obs


def test_plain_parity_skips_cells_no_3_fits():
    # only 44 (boxed in by misses) and the run 0-1-2 are unshot: while a 3 is afloat, plain 3-parity fires at the run
    obs = _misses_except([44, 0, 1, 2])
    picks = set()
    for seed in range(100):
        rng = random.Random(seed)
        h = bs.make("parity3")
        h.start(rng)
        picks.add(h.next_shot(obs, rng))
    assert picks <= {0, 1, 2}, picks
    obs.remaining = [5, 4, 2]                                # both 3s down: no skipping
    seen = set()
    for seed in range(100):
        rng = random.Random(seed)
        h = bs.make("parity3")
        h.start(rng)
        seen.add(h.next_shot(obs, rng))
    assert 44 in seen


def test_smart3_skips_cells_no_3_fits():
    # an A cell boxed in by misses is skipped for the one cell of the 3-parity set on the free run 0-1-2
    for seed in range(50):
        rng = random.Random(seed)
        h = bs.Smart3()
        h.start(rng)
        x = next(i for i in bs.cells_of(h.A) if 2 <= i // 10 <= 8 and 1 <= i % 10 <= 8)
        target = [i for i in (0, 1, 2) if (h.A | h.B) & bs.bit(i)]
        assert len(target) == 1                              # three cells in a row cross every third diagonal once
        assert h.next_shot(_misses_except([x, 0, 1, 2]), rng) == target[0]


def test_two_hunt_on_the_color_fired_at_more():
    # both 3s down; the even squares of the bottom half are misses, so the hunt for the 2 stays on even squares, at
    # cells next to an unshot cell
    keep = [i for i in range(bs.CELLS) if not (i // 10 >= 5 and (i // 10 + i % 10) % 2 == 0)]
    for name in ("smart3", "smart3pro"):
        for seed in range(40):
            rng = random.Random(seed)
            h = bs.make(name)
            h.start(rng)
            obs = _misses_except(keep, remaining=(5, 4, 2))
            c = h.next_shot(obs, rng)
            assert (c // 10 + c % 10) % 2 == 0 and bs.NEIGHBORS[c] & obs.unknown(), (name, c)
            if name == "smart3pro":                          # a big ship afloat: one every-fourth-diagonal set of it
                assert h.quarter % 2 == h.color and h.diag4[h.quarter] & bs.bit(c)


def test_big_ship_sweep_five_first():
    # the 4 and the 5 afloat; unshot: row 9 (the 5 fits) and cells 0-30 of column 0 (only the 4 fits). Every set of
    # every third or fourth diagonal meets both, and the cells where the 5 fits come first.
    keep = list(range(90, 100)) + [0, 10, 20, 30]
    for name in ("smart3", "smart3pro"):
        for seed in range(60):
            rng = random.Random(seed)
            h = bs.make(name)
            h.start(rng)
            assert h.next_shot(_misses_except(keep, remaining=(5, 4)), rng) // 10 == 9


def test_weighted_cell_proportions():
    rng = random.Random(9)
    picks = [bs.weighted_cell(bs.bit(3) | bs.bit(7), lambda i: 3.0 if i == 7 else 1.0, rng) for _ in range(8000)]
    assert abs(picks.count(7) / len(picks) - 0.75) < 0.02


def test_pro_weights_in_the_hunt_for_the_3s():
    # next to a sunk ship 0.4, an edge 2/3 (corners in full), elsewhere 1
    h = bs.Smart3Pro()
    resolved = bs.bit(44) | bs.bit(45)                       # a sunk 2 at 44-45
    cells = {"near": 46, "free": 22, "edge": 5, "corner": 0}
    rng = random.Random(11)
    mask = sum(bs.bit(i) for i in cells.values())
    picks = [h._pick3(mask, resolved, rng) for _ in range(30000)]
    share = {k: picks.count(i) / len(picks) for k, i in cells.items()}
    total = 0.4 + 1 + 2 / 3 + 1
    for k, w in (("near", 0.4), ("free", 1.0), ("edge", 2 / 3), ("corner", 1.0)):
        assert abs(share[k] - w / total) < 0.015, (k, share[k], w / total)


if __name__ == "__main__":
    for name, f in sorted(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)
