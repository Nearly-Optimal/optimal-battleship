"""The hunts of optimalbattleship.com, in plain Python.

Rules (as on the page): a 10x10 board and a fleet of ships of 5, 4, 3, 3 and 2 cells. Ships are straight, inside the
board, may touch but not overlap. Every shot is announced as a miss, a hit, or "you sank a ship of size k" (the size
only, not which cells). A hunt's score on a board is the number of shots it needs to sink the whole fleet.

Six hunts, written to make the same decisions as the C++ rules engine behind the page's numbers (only the random
number streams differ, so averages agree within sampling error; validate.py checks them):

    random      fire at random until a hit, then sink that ship
    checker     the checkerboard: fire at random squares of one color, then the other
    parity3     plain 3-parity: every third diagonal first, then the next set, then the last; while a 3 is afloat it
                skips cells where no 3 could fit
    smart3      smart 3-parity, the card in section 2 of the page
    smart3pro   smart 3-parity pro, section 5's five changes to it
    heat        the heat map: fire where the most placements of the remaining ships fit

Every hunt finishes the ships it hits the same way (the "finisher"): extend a line of two or more hits at either end,
otherwise fire next to a single hit.

Cells are numbered 10 * row + column, both from 0 (row 0 at the top, column 0 at the left).
Usage: see run.py, or

    import random, battleship as bs
    rng = random.Random(1)
    print(bs.play(bs.Smart3(), bs.random_layout(rng), rng))       # shots to sink the fleet on one random board
"""
import random

N = 10
CELLS = N * N
FLEET = (5, 4, 3, 3, 2)
FULL = (1 << CELLS) - 1


def bit(i):
    return 1 << i


def cells_of(mask):
    """the cell numbers in a bit mask, ascending"""
    out = []
    while mask:
        low = mask & -mask
        out.append(low.bit_length() - 1)
        mask ^= low
    return out


def random_cell(mask, rng):
    return rng.choice(cells_of(mask))


def weighted_cell(mask, weight, rng):
    """a cell of the mask, drawn with probability proportional to weight(cell)"""
    cells = cells_of(mask)
    w = [weight(i) for i in cells]
    r = rng.random() * sum(w)
    for i, x in zip(cells, w):
        r -= x
        if r < 0:
            return i
    return cells[-1]


def _placements(size):
    """every placement of a ship of this size: all horizontal ones (row by row), then all vertical ones"""
    out = []
    for r in range(N):
        for c in range(N - size + 1):
            out.append(sum(bit(r * N + c + k) for k in range(size)))
    for r in range(N - size + 1):
        for c in range(N):
            out.append(sum(bit((r + k) * N + c) for k in range(size)))
    return out


PLACEMENTS = {s: _placements(s) for s in set(FLEET)}
PLACEMENT_CELLS = {s: [cells_of(m) for m in PLACEMENTS[s]] for s in PLACEMENTS}
NEIGHBORS = [sum(bit(rr * N + cc) for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
                 if 0 <= rr < N and 0 <= cc < N) for r in range(N) for c in range(N)]
CORNERS = bit(0) | bit(N - 1) | bit(N * (N - 1)) | bit(N * N - 1)
EDGES = sum(bit(i) for i in range(CELLS) if i // N in (0, N - 1) or i % N in (0, N - 1)) & ~CORNERS   # corners apart


def neighbors(mask):
    """cells orthogonally next to any cell of the mask"""
    out = 0
    for i in cells_of(mask):
        out |= NEIGHBORS[i]
    return out


def fit_mask(size, allowed):
    """cells that some placement of a ship of this size covers with all of its cells in `allowed`"""
    out = 0
    for m in PLACEMENTS[size]:
        if not m & ~allowed:
            out |= m
    return out


# ---------------------------------------------------------------------------------------------------------- boards
def random_layout(rng):
    """a uniformly random legal layout: one bit mask per ship, in fleet order. Drawing every ship independently and
    starting over on any overlap gives every legal layout the same chance."""
    while True:
        ships, occupied = [], 0
        for size in FLEET:
            m = rng.choice(PLACEMENTS[size])
            if occupied & m:
                break
            ships.append(m)
            occupied |= m
        else:
            return ships


def parse_board(text):
    """'5:47,57,67,77,87 4:20,21,22,23 3:10,11,12 3:13,14,15 2:0,1' -> ship masks in fleet order"""
    ships = []
    for part in text.split():
        size, cells = part.split(":")
        cells = [int(x) for x in cells.split(",")]
        assert len(cells) == int(size)
        ships.append(sum(bit(i) for i in cells))
    ships.sort(key=lambda m: -bin(m).count("1"))
    assert tuple(bin(m).count("1") for m in ships) == FLEET
    occupied = 0
    for m in ships:
        assert not occupied & m, "ships overlap"
        assert m in PLACEMENTS[bin(m).count("1")], "not a straight in-bounds ship"
        occupied |= m
    return ships


def transform(layout, d4):
    """one of the 8 rotations / reflections of a layout (d4 = 0..7: rotate d4 // 2 quarter turns, then mirror if odd)"""
    def t(i):
        r, c = divmod(i, N)
        for _ in range(d4 // 2):
            r, c = c, N - 1 - r
        if d4 & 1:
            c = N - 1 - c
        return r * N + c
    return [sum(bit(t(i)) for i in cells_of(m)) for m in layout]


# ---------------------------------------------------------------------------------------------------------- the game
class Observation:
    """what the hunter knows: its shots, which were hits, and the sink announcements"""

    def __init__(self):
        self.shots = 0
        self.hits = 0
        self.sinks = []                      # (cell of the sinking shot, ship size, hits so far)
        self.remaining = list(FLEET)         # sizes of the ships not yet announced sunk

    def unknown(self):
        return FULL & ~self.shots

    def misses(self):
        return self.shots & ~self.hits


def play(hunt, layout, rng, limit=CELLS):
    """shots the hunt needs to sink every ship of the layout"""
    obs = Observation()
    afloat = list(layout)                    # cells of each ship not yet hit
    hunt.start(rng)
    for t in range(1, limit + 1):
        cell = hunt.next_shot(obs, rng)
        assert not obs.shots & bit(cell), "fired twice at one cell"
        obs.shots |= bit(cell)
        for k, ship in enumerate(layout):
            if ship & bit(cell):
                obs.hits |= bit(cell)
                afloat[k] &= ~bit(cell)
                if not afloat[k]:
                    size = bin(ship).count("1")
                    obs.sinks.append((cell, size, obs.hits))
                    obs.remaining.remove(size)
        if not obs.remaining:
            return t
    raise RuntimeError("hunt did not finish")


def sunk_cells(obs):
    """the hit cells the hunter can attribute to announced sinks: each sink of size k claims a straight run of k
    then-unexplained hits through the sinking cell (an exact-length run first, then horizontal)"""
    attributed = 0
    for cell, k, hits_at in obs.sinks:
        active = hits_at & ~attributed
        r, c = divmod(cell, N)

        def run(dr, dc):
            n = 0
            while True:
                rr, cc = r + (n + 1) * dr, c + (n + 1) * dc
                if not (0 <= rr < N and 0 <= cc < N) or not active & bit(rr * N + cc):
                    return n
                n += 1
        left, right, up, down = run(0, -1), run(0, 1), run(-1, 0), run(1, 0)
        lh, lv = 1 + left + right, 1 + up + down
        if (lh == k) != (lv == k):
            horizontal = lh == k
        elif (lh >= k) != (lv >= k):
            horizontal = lh >= k
        elif lh >= k:
            horizontal = True
        else:
            attributed |= bit(cell)
            continue
        back = min(left if horizontal else up, k - 1)
        dr, dc = (0, 1) if horizontal else (1, 0)
        for i in range(-back, k - back):
            attributed |= bit((r + i * dr) * N + (c + i * dc))
    return attributed


def open_hits(obs):
    """hits that belong to ships still afloat, as far as the hunter can tell"""
    return obs.hits & ~sunk_cells(obs)


def finisher(obs, rng):
    """the shot that follows up open hits: either end of a line of two or more hits, else a cell next to a hit;
    None when there is no open hit"""
    hits = open_hits(obs)
    if not hits:
        return None
    unknown = obs.unknown()

    def is_hit(r, c):
        return 0 <= r < N and 0 <= c < N and hits & bit(r * N + c)
    cand = []

    def add(r, c):
        if 0 <= r < N and 0 <= c < N and unknown & bit(r * N + c):
            cand.append(r * N + c)
    for i in cells_of(hits):
        r, c = divmod(i, N)
        for dr, dc in ((0, 1), (1, 0)):
            if is_hit(r - dr, c - dc) or not is_hit(r + dr, c + dc):
                continue                       # walk each run of two or more hits from its start
            rr, cc = r, c
            while is_hit(rr + dr, cc + dc):
                rr, cc = rr + dr, cc + dc
            add(r - dr, c - dc)
            add(rr + dr, cc + dc)
    if not cand:
        for i in cells_of(hits):
            r, c = divmod(i, N)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                add(r + dr, c + dc)
    return rng.choice(cand) if cand else random_cell(unknown, rng)


def density(obs, hit_bonus=50.0, hunt_only=False):
    """per cell, how many placements of the remaining ships fit over it (missing misses and sunk ships). With open
    hits (unless hunt_only), only placements through an open hit count, weighted hit_bonus ** (open hits covered)."""
    resolved = sunk_cells(obs)
    allowed = FULL & ~(obs.misses() | resolved)
    hits = obs.hits & ~resolved
    targeting = hits != 0 and not hunt_only
    d = [0.0] * CELLS
    for size in obs.remaining:
        for m, cells in zip(PLACEMENTS[size], PLACEMENT_CELLS[size]):
            if m & ~allowed:
                continue
            w = 1.0
            if targeting:
                h = bin(m & hits).count("1")
                if h == 0:
                    continue
                w = hit_bonus ** min(h, 8)
            for i in cells:
                d[i] += w
    return d


def best_cell(d, mask, rng):
    """the cell of the mask with the highest positive value, exact ties broken at random; None if none is positive"""
    best, cands = 0.0, []
    for i in cells_of(mask):
        if d[i] > best + 1e-12:
            best, cands = d[i], [i]
        elif d[i] > best - 1e-12 and d[i] > 0:
            cands.append(i)
    return rng.choice(cands) if cands else None


# ---------------------------------------------------------------------------------------------------------- hunts
class Hunt:
    name = "?"

    def start(self, rng):
        pass

    def next_shot(self, obs, rng):
        raise NotImplementedError


class RandomHunt(Hunt):
    """fire at random until a hit, then sink that ship"""
    name = "random"

    def next_shot(self, obs, rng):
        cell = finisher(obs, rng)
        return cell if cell is not None else random_cell(obs.unknown(), rng)


def diagonal_class(i, k, direction):
    r, c = divmod(i, N)
    return ((r + c) if direction == 0 else (r - c + k * N)) % k


class Stripes(Hunt):
    """fire at random cells of one set of every k-th diagonal, then the next set, ...; the direction (one of the two
    diagonals) and the order of the sets are drawn at random for each game. k = 2 is the checkerboard (its two sets are
    the two colors), k = 3 is 3-parity. With skip3 (the page's plain 3-parity), while a 3 is afloat the hunt skips
    cells no 3 could fit through (every straight run of 3 cells through them crosses a shot cell)."""

    def __init__(self, k, skip3=False, name=None):
        self.k = k
        self.skip3 = skip3
        self.name = name or "stripes%d" % k

    def start(self, rng):
        self.direction = rng.randrange(2)
        self.order = rng.sample(range(self.k), self.k)

    def next_shot(self, obs, rng):
        cell = finisher(obs, rng)
        if cell is not None:
            return cell
        unknown = obs.unknown()
        if self.skip3 and 3 in obs.remaining:
            fit = unknown & fit_mask(3, unknown)
            if fit:
                unknown = fit
        for j in self.order:
            stripe = sum(bit(i) for i in cells_of(unknown) if diagonal_class(i, self.k, self.direction) == j)
            if stripe:
                return random_cell(stripe, rng)
        return random_cell(unknown, rng)


class HeatMap(Hunt):
    """fire at the cell the most placements of the remaining ships fit over (with open hits: the placements through
    them, strongly weighted by how many they cover); exact ties at random"""
    name = "heat"

    def next_shot(self, obs, rng):
        unknown = obs.unknown()
        cell = best_cell(density(obs), unknown, rng)
        if cell is None:
            cell = best_cell(density(obs, hunt_only=True), unknown, rng)
        return cell if cell is not None else random_cell(unknown, rng)


class Smart3(Hunt):
    """smart 3-parity, the card in section 2 of the page.

    Before the first shot: pick a 3-parity set at random (a diagonal direction and one of its sets of every third
    diagonal). Its diagonals alternate between the two checkerboard colors; split the set by color, at random which is
    which: half A on one color, half B on the other.
    Finishing comes first: with a hit not yet accounted for by a sink, the finisher.
    The 3s: fire at random unshot cells of half A, then half B, skipping cells where no 3 could fit (if neither half
    has such a cell left, none is skipped). When the first 3 sinks, jump in secret a third of the time: switch to half
    B at once (coming back to A if B is finished without the second 3).
    The 2: once both 3s are down, take the checkerboard color fired at more and fire at random at its cells where the
    2 could still be (cells next to an unshot cell).
    The 4 and the 5, if still afloat: call a cell live if a ship left still fits through it (a straight run of unshot
    cells long enough for the smaller one). Sweep the diagonal set with the fewest live cells (every third or every
    fourth diagonal, either direction; also every fifth when only the 5 is left), at random, until none is left; then
    choose again. While the 4 and the 5 are both afloat, the set's cells where the 5 could still fit come first."""
    name = "smart3"
    jump_share = 1 / 3

    def start(self, rng):
        self.offset = rng.randrange(6)                       # which set of every third diagonal is half A
        self.frame = rng.randrange(8)                        # the diagonal direction (a random rotation/reflection)
        self.jump = rng.random() < self.jump_share
        self.color = None                                    # the color of the hunt for the 2, chosen once
        self.quarter = None                                  # pro: the every-fourth-diagonal set of that color
        self.sweep = 0                                       # the big-ship sweep's current diagonal set
        self.parity = [0] * CELLS
        self.diag4 = [0, 0, 0, 0]                            # the four sets of every fourth diagonal (in the frame)
        masks = {"A": 0, "B": 0, "C": 0, "D": 0}
        for i in range(CELLS):
            r, c = divmod(i, N)
            for _ in range(self.frame // 2):
                r, c = c, N - 1 - r
            if self.frame & 1:
                c = N - 1 - c
            diag = r + c
            self.parity[i] = diag % 2
            self.diag4[diag % 4] |= bit(i)
            k = (diag - self.offset) % 6                     # 0 = half A, 3 = half B, 2 and 4 = A's color, 1 and 5 = B's
            masks["A" if k == 0 else "B" if k == 3 else "C" if k in (2, 4) else "D"] |= bit(i)
        self.A, self.B, self.C, self.D = masks["A"], masks["B"], masks["C"], masks["D"]

    def next_shot(self, obs, rng):
        cell = finisher(obs, rng)
        if cell is not None:
            return cell
        if 3 in obs.remaining:
            return self._threes(obs, rng)
        if 2 in obs.remaining:
            cell = self._two(obs, rng)
            return cell if cell is not None else self._checkerboard(obs, rng)
        return self._big_ships(obs, rng)

    def _threes(self, obs, rng):
        unknown = obs.unknown()
        resolved = sunk_cells(obs)
        a, b = unknown & self.A, unknown & self.B
        fit = fit_mask(3, FULL & ~(obs.misses() | resolved))
        if (a | b) & fit:
            a, b = a & fit, b & fit
        first_sunk = obs.remaining.count(3) < 2
        for half in ((b, a) if (self.jump and first_sunk) else (a, b)):
            if half:
                return self._pick3(half, resolved, rng)
        return random_cell(unknown, rng)

    def _pick3(self, cells, resolved, rng):
        return random_cell(cells, rng)

    def _choose_color(self, obs, rng):
        if self.color is None:
            left = [0, 0]
            for i in cells_of(obs.unknown()):
                left[self.parity[i]] += 1
            self.color = 0 if left[0] < left[1] else 1 if left[1] < left[0] else rng.randrange(2)

    def _two(self, obs, rng):
        return None                                          # smart 3-parity hunts the 2 on the plain checkerboard

    def _quarter(self, obs, rng):
        return FULL                                          # (pro: one every-fourth-diagonal set of the color)

    def _pick2(self, cells, rng):
        return random_cell(cells, rng)

    def _checkerboard(self, obs, rng):
        self._choose_color(obs, rng)
        unknown = obs.unknown()
        cand = sum(bit(i) for i in cells_of(unknown) if self.parity[i] == self.color) or unknown
        cand = cand & self._quarter(obs, rng) or cand
        fit = sum(bit(i) for i in cells_of(cand) if NEIGHBORS[i] & unknown)
        return self._pick2(fit, rng) if fit else random_cell(cand, rng)

    def _big_ships(self, obs, rng):
        unknown = obs.unknown()
        allowed = FULL & ~(obs.misses() | sunk_cells(obs))
        live = 0
        for size in set(obs.remaining):
            live |= fit_mask(size, allowed)
        live &= unknown
        if not live:
            return random_cell(unknown, rng)
        has4, has5 = 4 in obs.remaining, 5 in obs.remaining
        fit5 = fit_mask(5, unknown) if has4 and has5 else FULL

        def pick(cells):
            return random_cell(cells & fit5 or cells, rng)
        if self.sweep & live:
            return pick(self.sweep & live)
        best, best_n, ties = 0, CELLS + 1, 0
        for mod in (3, 4, 5):
            if mod == 5 and (has4 or not has5):
                continue
            for slope in (0, 1):
                for k in range(mod):
                    s = sum(bit(i) for i in cells_of(unknown)
                            if (((i // N) - (i % N) + 4 * N) if slope else ((i // N) + (i % N))) % mod == k)
                    n = bin(s & live).count("1")
                    if n <= 0:
                        continue
                    if n < best_n:
                        best, best_n, ties = s, n, 1
                    elif n == best_n:
                        ties += 1
                        if rng.randrange(ties) == 0:
                            best = s
        self.sweep = best
        return pick(best & live or live)


class Smart3Pro(Smart3):
    """smart 3-parity pro (section 5 of the page): smart 3-parity with five changes.

    1. Fire less often next to sunk ships: in the hunt for the 3s, a cell next to a sunk ship counts 0.4.
    2. A zone order for the 2: on the color fired at more, among its cells where the 2 could still be, fire first at
       (1) cells off the 3-parity set that touch an unshot cell of the set's half on the other color, then (2) the rest
       of the set's half on this color, then (3) the rest of the color.
    3. Favor corners in the hunt for the 2: within each step a corner counts 1.5, any other cell 1.
    4. Edge cells count 2/3 in the hunt for the 3s (the four corners count in full; the page's runs used 0.6667).
    5. While the 4 or the 5 is afloat, hunt the 2 on one of the color's two sets of every fourth diagonal (a quarter of
       the board), drawn at random once; if no step of the order has a cell there, on the whole color.
    "Counts w" means drawn with probability proportional to w (pick, then pick again with probability 1 - w); the
    counts multiply."""
    name = "smart3pro"
    near_sunk = 0.4
    edge = 2 / 3
    corner = 1.5

    def _pick3(self, cells, resolved, rng):
        near = neighbors(resolved) & ~resolved

        def weight(i):
            w = self.near_sunk if near & bit(i) else 1.0
            return w * self.edge if EDGES & bit(i) else w
        return weighted_cell(cells, weight, rng)

    def _quarter(self, obs, rng):
        if 4 not in obs.remaining and 5 not in obs.remaining:
            return FULL
        if self.quarter is None:
            self.quarter = self.color + 2 * rng.randrange(2)
        return self.diag4[self.quarter]

    def _pick2(self, cells, rng):
        return weighted_cell(cells, lambda i: self.corner if CORNERS & bit(i) else 1.0, rng)

    def _two(self, obs, rng):
        unknown = obs.unknown()
        hold = sum(bit(i) for i in cells_of(unknown) if NEIGHBORS[i] & unknown)    # a 2 can still be here
        self._choose_color(obs, rng)
        half, other, rest = self.A, self.B, self.C
        if self.color != self.offset % 2:                    # B's color was fired at more: swap the halves
            half, other, rest = self.B, self.A, self.D
        tiers = [rest & unknown & hold & neighbors(other & unknown), half & unknown & hold, rest & unknown & hold]
        q = self._quarter(obs, rng)
        if any(t & q for t in tiers):
            tiers = [t & q for t in tiers]
        for tier in tiers:
            if tier:
                return self._pick2(tier, rng)
        return None


HUNTS = {h.name: h for h in (RandomHunt, HeatMap, Smart3, Smart3Pro)}
HUNTS["checker"] = lambda: Stripes(2, name="checker")
HUNTS["parity3"] = lambda: Stripes(3, skip3=True, name="parity3")


def make(name):
    return HUNTS[name]()


# ---------------------------------------------------------------------------------------------------------- races
def credit(shots, pace):
    """a race against an opponent who finishes at random from `pace`: pace[T] = P(opponent needs more than T shots)
    + 1/2 P(exactly T) (a finish in the same round counts half)"""
    return pace[min(shots, len(pace) - 1)]


def race(times_a, times_b):
    """chance that a game drawn from times_a finishes before one drawn from times_b (ties count half)"""
    from collections import Counter
    ca, cb = Counter(times_a), Counter(times_b)
    na, nb = len(times_a), len(times_b)
    below = 0
    win = 0.0
    for t in sorted(set(ca) | set(cb)):
        win += ca[t] / na * ((nb - below - cb[t]) / nb + 0.5 * cb[t] / nb)
        below += cb[t]
    return win
