"""
visualizer.py — Professional ASCII Elevator Shaft Renderer.

Provides two rendering modes:
    render_shaft(elevators)   — Full building grid with elevator positions,
                                stop markers, floor labels, and status bar.
    render_status(elevators)  — Detailed per-elevator status panel.

Design principles:
    • Every column is exactly CELL_W characters wide — no overflow, no gaps.
    • All borders use consistent unicode box-drawing characters.
    • Floor numbers are always right-justified in a fixed 3-digit label.
    • The status bar below the shaft uses fixed-width fields.
    • Both panels look identical whether there are 2 or 10 elevators.
"""

import copy

from config import (
    DIR_DOWN, DIR_IDLE, DIR_UP, MAX_CAPACITY,
    STATE_ACCEL_DOWN, STATE_ACCEL_UP,
    STATE_DECEL_DOWN, STATE_DECEL_UP,
    STATE_DOOR_CLOSING, STATE_DOOR_OPEN, STATE_DOOR_OPENING, STATE_DOOR_PRE_OPEN,
    STATE_DOOR_STUCK, STATE_E_STOP, STATE_FIRE_RECALL,
    STATE_IDLE, STATE_LEVELING, STATE_MOVING_DOWN, STATE_MOVING_UP,
    STATE_OVERLOAD,
)

# ── Layout constants ───────────────────────────────────────────
CELL_W      = 10    # characters per elevator column (excluding border pipes)
FLOOR_W     = 5     # characters for the floor label column (e.g. " F12 ")
PANEL_W     = 60    # inner width of the status / detail panels

# ── State groups for symbol selection ─────────────────────────
_UP_STATES    = {STATE_MOVING_UP,   STATE_ACCEL_UP,   STATE_DECEL_UP}
_DOWN_STATES  = {STATE_MOVING_DOWN, STATE_ACCEL_DOWN, STATE_DECEL_DOWN}
_OPEN_STATES  = {STATE_DOOR_OPEN,   STATE_DOOR_OPENING, STATE_DOOR_PRE_OPEN}
_CLOSE_STATES = {STATE_DOOR_CLOSING, STATE_LEVELING}
_FAULT_STATES = {STATE_OVERLOAD, STATE_DOOR_STUCK, STATE_E_STOP, STATE_FIRE_RECALL}

# ── Symbols (pure ASCII) ─────────────────────────────────────
#   Each symbol is 1 char, centred in CELL_W by the renderer.
_SYM_UP    = "^"   # moving up
_SYM_DOWN  = "v"   # moving down
_SYM_OPEN  = "="   # door open
_SYM_CLOSE = "-"   # door closing / leveling
_SYM_FAULT = "!"   # fault state
_SYM_IDLE  = "*"   # idle


# ═══════════════════════════════════════════════════════════════

class Visualizer:
    """
    ASCII-based elevator shaft and status renderer.

    All output is written to stdout via print(). No external
    dependencies — only the standard library and config.py.
    """

    def __init__(self, num_floors: int, num_elevators: int) -> None:
        self.num_floors    = num_floors
        self.num_elevators = num_elevators

    # ───────────────────────────────────────────────────────────
    #  INTERNAL HELPERS
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def _symbol(elevator) -> str:
        """
        Return the single glyph representing an elevator's current state.

        Returns one of: ^  v  =  -  !  *
        """
        if elevator.state in _UP_STATES:    return _SYM_UP
        if elevator.state in _DOWN_STATES:  return _SYM_DOWN
        if elevator.state in _OPEN_STATES:  return _SYM_OPEN
        if elevator.state in _CLOSE_STATES: return _SYM_CLOSE
        if elevator.state in _FAULT_STATES: return _SYM_FAULT
        return _SYM_IDLE

    @staticmethod
    def _load_bar(load: int, capacity: int, width: int = 8) -> str:
        """
        Render a compact ASCII load bar, e.g.  [####....]  3/8

        Length of filled portion proportional to load / capacity.
        """
        filled = round((load / max(1, capacity)) * width)
        bar    = "#" * filled + "." * (width - filled)
        return f"[{bar}] {load}/{capacity}"

    @staticmethod
    def _direction_arrow(direction: str) -> str:
        """Return a readable direction arrow string."""
        return {"UP": "^ UP", "DOWN": "v DN", "IDLE": "* --"}.get(direction, direction)

    @staticmethod
    def _cell(text: str) -> str:
        """Centre text in exactly CELL_W characters, truncating if needed."""
        text = text[:CELL_W]
        return text.center(CELL_W)

    @staticmethod
    def _hline(n_elevators: int, left: str, mid: str, right: str,
               fill: str = "─") -> str:
        """
        Build a horizontal border line for the shaft grid.

        Example (3 elevators, fill="─"):
            ├─────┼──────────┼──────────┼──────────┤
        """
        floor_seg = fill * (FLOOR_W + 2)        # the floor-label column segment
        elev_seg  = fill * (CELL_W + 2)         # one elevator column segment
        parts = [fill * (FLOOR_W + 2)] + [fill * (CELL_W + 2)] * n_elevators
        return left + mid.join(parts) + right

    # ───────────────────────────────────────────────────────────
    #  SHAFT GRID
    # ───────────────────────────────────────────────────────────

    def render_shaft(self, elevators: list, num_floors: int = None) -> None:
        """
        Print a full building shaft grid with elevator positions and stops.

        Layout:
        ╔══════╦══════════╦══════════╦══════════╗
        ║ Flr  ║    E0    ║    E1    ║    E2    ║
        ╠══════╬══════════╬══════════╬══════════╣
        ||  10  ||          ||  (stop)  ||  ^ E2   ||
        ||   9  ||  = E0   ||          ||          ||
        ...
        ╚══════╩══════════╩══════════╩══════════╝

        Below the grid: a one-line status summary per elevator.
        """
        if num_floors is None:
            num_floors = self.num_floors
        n = len(elevators)

        # ── Legend ──────────────────────────────────────────────
        print()
        print("  ╔═════════════════════════════════════════════════╗")
        print("  ║  SHAFT LEGEND                                   ║")
        print("  ║  ^ Moving UP    v Moving DOWN   = Door OPEN    ║")
        print("  ║  - Closing/Lvl  ! FAULT/EMG     * IDLE         ║")
        print("  ║  (stop) = pending floor stop                    ║")
        print("  ╚═════════════════════════════════════════════════╝")
        print()

        # ── Top border ──────────────────────────────────────────
        print("  " + self._hline(n, "╔", "╦", "╗", "═"))

        # ── Column header: Floor label + elevator IDs ────────────
        h = "║ " + "Flr".center(FLOOR_W - 1) + " ║"
        for elev in elevators:
            h += f" E{elev.id}".center(CELL_W) + " ║"
        print(f"  {h}")

        # ── Sub-header separator ────────────────────────────────
        print("  " + self._hline(n, "╠", "╬", "╣", "═"))

        # ── Floor rows: top to bottom ──────────────────────────
        for floor in range(num_floors, -1, -1):
            row = f"║ {floor:>{FLOOR_W - 1}} ║"
            for elev in elevators:
                elev_floor = int(round(elev.current_floor))
                if elev_floor == floor:
                    sym  = self._symbol(elev)
                    cell = f"{sym} E{elev.id}"
                    row += " " + cell.center(CELL_W) + " ║"
                elif floor in elev.stop_queue:
                    row += " " + "(stop)".center(CELL_W) + " ║"
                else:
                    row += " " + " " * CELL_W + " ║"
            print(f"  {row}")

        # ── Bottom border ────────────────────────────────────────
        print("  " + self._hline(n, "╚", "╩", "╝", "═"))

        # ── Status bar (one line per elevator) ──────────────────
        print()
        self._render_status_bar(elevators)

    def _render_status_bar(self, elevators: list) -> None:
        """
        Print a compact fixed-width status line for each elevator.

        Format:
          E0 | Flr  4.0 | ^ UP      | Load [####....] 2/8 | Stops [2,5,8] | ETA  6.0s
        """
        # Header
        w = 80
        print("  " + "─" * w)
        print("  " + " ELEVATOR STATUS SUMMARY".ljust(w))
        print("  " + "─" * w)

        for elev in elevators:
            eta      = elev.get_eta_to_next_stop()
            eta_str  = f"{eta:5.1f}s" if eta > 0 else "  —   "
            stops    = ", ".join(str(s) for s in elev.stop_queue) if elev.stop_queue else "—"
            load_bar = self._load_bar(elev.current_load, MAX_CAPACITY, width=8)
            dir_str  = self._direction_arrow(elev.direction)
            state    = elev.state[:14].ljust(14)   # truncate long fault names

            line = (
                f"  E{elev.id}"
                f"  │  Flr {elev.current_floor:5.1f}"
                f"  │  {dir_str}"
                f"  │  {state}"
                f"  │  {load_bar}"
                f"  │  Stops [{stops}]"
                f"  │  ETA {eta_str}"
            )
            print(line)

        print("  " + "─" * w)

    # ───────────────────────────────────────────────────────────
    #  DETAILED STATUS PANEL
    # ───────────────────────────────────────────────────────────

    def render_status(self, elevators: list) -> None:
        """
        Print a detailed status card for every elevator.

        Each card shows: position, state, direction, queue, load bar,
        ETA, distance traveled, passengers served, and energy stats.
        """
        W = PANEL_W
        print()
        print("  ╔" + "═" * W + "╗")
        print("  ║" + " DETAILED ELEVATOR STATUS REPORT".center(W) + "║")
        print("  ╠" + "═" * W + "╣")

        for i, elev in enumerate(elevators):
            status   = elev.get_status_dict()
            load_bar = self._load_bar(elev.current_load, MAX_CAPACITY, width=10)
            net_e    = status["energy_consumed"] - status["energy_regenerated"]
            stops    = str(status["stop_queue"]) if status["stop_queue"] else "[ ]"

            def row(label: str, value: str) -> None:
                content = f"  {label:<22}  {value}"
                print("  ║  " + content.ljust(W - 2) + "  ║")

            print("  ║" + f"  ── Elevator E{status['id']} ──".ljust(W) + "║")
            row("Current Floor",      f"{status['floor']:.1f}")
            row("State",              status["state"])
            row("Direction",          self._direction_arrow(status["direction"]))
            row("Stop Queue",         stops)
            row("Load",               load_bar)
            row("ETA to Next Stop",   f"{status['eta_next']:.1f} s")
            row("Total Distance",     f"{status['total_traveled']:.1f} floors")
            row("Passengers Served",  str(status["passengers_served"]))
            row("Energy Consumed",    f"{status['energy_consumed']:.2f} units")
            row("Energy Regenerated", f"{status['energy_regenerated']:.2f} units")
            row("Net Energy",         f"{net_e:.2f} units")

            if i < len(elevators) - 1:
                print("  ╠" + "─" * W + "╣")

        print("  ╠" + "═" * W + "╣")
        # ── Symbol legend in footer ──────────────────────────────
        print("  ║" + "  States: ^=UP  v=DN  ==OPEN  -=CLOSING  !=FAULT  *=IDLE".ljust(W) + "║")
        print("  ╚" + "═" * W + "╝")


# ═══════════════════════════════════════════════════════════════
#  STANDALONE DEMO  (python visualizer.py)
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from elevator import Elevator
    from ga import optimize_all_routes
    from fuzzy import score_all_elevators
    from config import (
        DIR_UP, DIR_DOWN,
        ENERGY_PER_FLOOR, ENERGY_LOAD_FACTOR, GA_REGEN_FACTOR_DESCENT,
    )

    # ── Helpers ─────────────────────────────────────────────────
    def clone_state(elevs):
        return copy.deepcopy(elevs)

    def planned_route_metrics(elev):
        route   = list(elev.stop_queue)
        current = int(round(elev.current_floor))
        load    = float(getattr(elev, "current_load", 0))
        prev_dir = elev.direction if elev.direction in (DIR_UP, DIR_DOWN) else None
        distance = energy = 0.0
        reversals = 0
        for stop in route:
            delta = int(stop) - current
            leg   = abs(delta)
            distance += leg
            if delta > 0:
                leg_dir = DIR_UP
                energy += leg * ENERGY_PER_FLOOR * (1 + ENERGY_LOAD_FACTOR * load)
            elif delta < 0:
                leg_dir = DIR_DOWN
                energy -= leg * GA_REGEN_FACTOR_DESCENT
            else:
                leg_dir = prev_dir
            if prev_dir in (DIR_UP, DIR_DOWN) and leg_dir in (DIR_UP, DIR_DOWN) and leg_dir != prev_dir:
                reversals += 1
            prev_dir = leg_dir
            current  = int(stop)
        return distance, energy, reversals

    def fleet_metrics(elevs):
        td = te = tr = 0
        for e in elevs:
            d, en, r = planned_route_metrics(e)
            td += d; te += en; tr += r
        return td, te, tr

    def tick_banner(tick):
        print(f"\n  {'─'*58}")
        print(f"  TICK {tick:02d}")
        print(f"  {'─'*58}")

    def apply_calls(elevs, calls):
        rows = []
        for idx, call in enumerate(calls, 1):
            best, score, all_scores = score_all_elevators(
                elevs, call["floor"], call["direction"], verbose=False
            )
            best.add_stop(call["floor"])
            best.add_stop(call["destination"])
            score_str = "  ".join(f"E{e.id}:{s:.1f}" for e, s, _, _ in all_scores)
            rows.append((idx, call["floor"], call["direction"],
                         call["destination"], best.id, score, score_str))
        return rows

    def simulate(elevs, viz, ticks=18):
        arrivals = set()
        for t in range(ticks):
            tick_banner(t)
            viz.render_shaft(elevs)
            for e in elevs:
                before = int(round(e.current_floor))
                e.update_tick()
                after = int(round(e.current_floor))
                if before != after:
                    arrivals.add((e.id, after))
        return arrivals

    # ── Demo setup ───────────────────────────────────────────────
    FLOORS = 10
    elevators = [
        Elevator(elevator_id=0, num_floors=FLOORS, start_floor=2),
        Elevator(elevator_id=1, num_floors=FLOORS, start_floor=6),
        Elevator(elevator_id=2, num_floors=FLOORS, start_floor=9),
    ]
    elevators[0].state = STATE_IDLE;      elevators[0].direction = DIR_IDLE
    elevators[0].current_load = 1;        elevators[0].stop_queue = [1]
    elevators[1].state = STATE_MOVING_UP; elevators[1].direction = DIR_UP
    elevators[1].current_load = 4;        elevators[1].stop_queue = [8]
    elevators[2].state = STATE_DOOR_OPEN; elevators[2].direction = DIR_IDLE
    elevators[2].current_load = 0;        elevators[2].stop_queue = [7]

    viz = Visualizer(num_floors=FLOORS, num_elevators=3)

    # ── Banner ───────────────────────────────────────────────────
    print("\n  ╔════════════════════════════════════════════════════════════╗")
    print("  ║        THREE SIMULTANEOUS CALLS — FUZZY ➜ GA DEMO        ║")
    print("  ╚════════════════════════════════════════════════════════════╝")

    calls = [
        {"floor": 5, "direction": DIR_UP,   "destination": 9},
        {"floor": 2, "direction": DIR_DOWN,  "destination": 0},
        {"floor": 8, "direction": DIR_DOWN,  "destination": 3},
    ]
    print("\n  Incoming hall calls (t=0):")
    for i, c in enumerate(calls, 1):
        print(f"    P{i}  Floor {c['floor']}  {c['direction']}  ->  dest {c['destination']}")

    print("\n  ── STEP 1: Fuzzy Assignment ─────────────────────────────────")
    print("     Factors: distance, direction, load, queue, passing-by")
    rows = apply_calls(elevators, calls)
    for idx, rf, rd, dst, eid, score, all_s in rows:
        print(f"    P{idx}  F{rf} {rd} -> F{dst}  ->  E{eid}  score={score:.1f}  [{all_s}]")

    print("\n  Planned routes after Fuzzy:")
    for e in elevators:
        print(f"    E{e.id}  {e.stop_queue}")

    fuzzy_snap = clone_state(elevators)
    fd, fe, fr = fleet_metrics(fuzzy_snap)

    print("\n  ── STEP 2: GA Route Optimisation ───────────────────────────")
    print("     Objective: 40% distance + 35% energy + 25% comfort")
    ga_asgn, dist_imp = optimize_all_routes(elevators, verbose=False)

    print("\n  Planned routes after GA:")
    for e in elevators:
        print(f"    E{e.id}  {ga_asgn.get(e.id, [])}")

    gd, ge, gr = fleet_metrics(elevators)
    print(f"\n  Fleet planning delta (Fuzzy -> GA):")
    print(f"    Distance   {fd:.1f} -> {gd:.1f} floors    (GA delta: {dist_imp:+.1f}%)")
    print(f"    Energy     {fe:.2f} -> {ge:.2f} units")
    print(f"    Reversals  {fr} -> {gr}")

    print("\n  ── STEP 3: Live Simulation ──────────────────────────────────")
    viz.render_shaft(elevators)
    viz.render_status(elevators)

    arrivals = simulate(elevators, viz, ticks=18)

    print("\n  ── Final Status ─────────────────────────────────────────────")
    viz.render_status(elevators)

    act_dist = sum(e.total_floors_traveled for e in elevators)
    act_enrg = sum(e.energy_consumed - e.energy_regenerated for e in elevators)
    print(f"\n  Runtime metrics:")
    print(f"    Actual distance traveled   : {act_dist:.1f} floors")
    print(f"    Net energy (used − regen)  : {act_enrg:.2f} units")
    print(f"    Passengers served (drops)  : {sum(e.passengers_served for e in elevators)}")
    print(f"    Distinct floor arrivals    : {len(arrivals)}")

    print("\n  Role summary:")
    print("    Fuzzy Logic   : decides WHICH elevator handles each call")
    print("    Genetic Algo  : decides IN WHAT ORDER each elevator visits stops")
