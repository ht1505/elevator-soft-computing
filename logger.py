"""
logger.py — Logging and Summary System for the Smart Elevator Management System.

Tracks all request assignments, system events, and per-elevator statistics.
Produces uniformly formatted, box-drawn console tables for the interactive
summary view (CLI menu option 4).

Formatting rules:
    • All tables share width = TABLE_W characters (inner).
    • Column widths are fixed — every row is exactly the same length.
    • Numbers are right-justified; text is left-justified.
    • Unicode box-drawing characters (╔ ║ ╠ ╣ ╚ ═ │) for all borders.
"""

from config import ENERGY_REGEN_FACTOR   # keeps the import for legacy callers

# ── Layout constants ─────────────────────────────────────────────────────────
TABLE_W  = 84   # inner width of main request table (between outer ║  ║)
PANEL_W  = 63   # inner width of elevator / system panels


# ═════════════════════════════════════════════════════════════════════════════

class Logger:
    """
    Centralised logging system for the elevator management system.

    Tracks:
        • Per-request details: fuzzy score, GA improvement, wait/pickup times.
        • Per-elevator statistics: floors, energy, passengers.
        • System-level events: mode changes, errors, anomalies.
    """

    def __init__(self) -> None:
        self.request_logs:  list = []
        self.system_events: list = []

    # ─── Private formatting helpers ──────────────────────────────────────────

    @staticmethod
    def _top(width: int = TABLE_W) -> str:
        return "  ╔" + "═" * width + "╗"

    @staticmethod
    def _mid(width: int = TABLE_W) -> str:
        return "  ╠" + "═" * width + "╣"

    @staticmethod
    def _div(width: int = TABLE_W) -> str:
        return "  ╟" + "─" * width + "╢"

    @staticmethod
    def _bot(width: int = TABLE_W) -> str:
        return "  ╚" + "═" * width + "╝"

    @staticmethod
    def _row(text: str, width: int = TABLE_W) -> str:
        return "  ║ " + text.ljust(width - 2) + " ║"

    @staticmethod
    def _title(label: str, width: int = TABLE_W) -> str:
        return "  ║" + label.center(width) + "║"

    @staticmethod
    def _blank(width: int = TABLE_W) -> str:
        return "  ║" + " " * width + "║"

    # ─── Request Table helpers ────────────────────────────────────────────────

    @staticmethod
    def _col_header() -> str:
        """Build the column header row for the request log table."""
        #  Req   Time    Flr   Dir   Dest   To    Wait   Pickup   Fuzzy   GA%   Status
        return (
            "  ║ "
            + f"{'Req':>3}  "
            + f"{'Time':>6}  "
            + f"{'Flr':>3}  "
            + f"{'Dir':>4}  "
            + f"{'Dest':>4}  "
            + f"{'To':>4}  "
            + f"{'Wait':>6}  "
            + f"{'Pickup':>6}  "
            + f"{'Fuzzy':>5}  "
            + f"{'GA%':>5}  "
            + f"{'Status':<7}"
            + " ║"
        )

    @staticmethod
    def _col_divider() -> str:
        """Divider line matching column header widths."""
        return (
            "  ╠─"
            + "─" * 3  + "──"
            + "─" * 6  + "──"
            + "─" * 3  + "──"
            + "─" * 4  + "──"
            + "─" * 4  + "──"
            + "─" * 4  + "──"
            + "─" * 6  + "──"
            + "─" * 6  + "──"
            + "─" * 5  + "──"
            + "─" * 5  + "──"
            + "─" * 7
            + "─╣"
        )

    @staticmethod
    def _data_row(log: dict) -> str:
        """Build one formatted request data row."""
        req      = log.get("_request_ref")
        wait     = f"{req.wait_time:.1f}s"  if req and req.wait_time  is not None else "  —   "
        pickup   = f"{req.pickup_time:.1f}" if req and req.pickup_time is not None else "   —  "
        ga_imp   = f"{log['ga_improvement']:.1f}" if log["ga_improvement"] is not None else "  —  "
        fuzzy    = f"{log['fuzzy_score']:.1f}"    if log["fuzzy_score"]    is not None else "  —  "
        assigned = f"E{log['assigned_to']}"        if log["assigned_to"]   is not None else "  — "
        dest     = str(log.get("destination", "—")) if log.get("destination") is not None else "  —"

        if req and req.served:
            status = "✓ Done "
        elif req and req.picked_up:
            status = "↑ InCab"
        else:
            status = "· Wait "

        return (
            "  ║ "
            + f"{log['request_id']:>3}  "
            + f"{log['time']:>6.1f}  "
            + f"{log['floor']:>3}  "
            + f"{log['direction']:>4}  "
            + f"{dest:>4}  "
            + f"{assigned:>4}  "
            + f"{wait:>6}  "
            + f"{pickup:>6}  "
            + f"{fuzzy:>5}  "
            + f"{ga_imp:>5}  "
            + f"{status:<7}"
            + " ║"
        )

    # ─── Public API ────────────────────────────────────────────────────────────

    def log_request(self, request, fuzzy_score=None, ga_improvement=None,
                    reason: str = "", **kwargs) -> None:
        """
        Record a request assignment event.

        Args:
            request:        Request object (kept as _request_ref for live updates).
            fuzzy_score:    Winning fuzzy suitability score.
            ga_improvement: GA route improvement percentage.
            reason:         Human-readable assignment reason string.
        """
        if fuzzy_score    is None and "score"       in kwargs:
            fuzzy_score    = kwargs["score"]
        if ga_improvement is None and "improvement" in kwargs:
            ga_improvement = kwargs["improvement"]

        self.request_logs.append({
            "request_id":     request.request_id,
            "time":           request.timestamp,
            "floor":          request.floor,
            "direction":      request.direction,
            "destination":    request.destination_floor,
            "assigned_to":    request.assigned_elevator,
            "fuzzy_score":    fuzzy_score,
            "ga_improvement": ga_improvement,
            "wait_time":      request.wait_time,
            "pickup_time":    request.pickup_time,
            "reason":         reason,
            "_request_ref":   request,   # live reference for real-time wait updates
        })

    def log_event(self, event_type: str, message: str, time: float = 0.0,
                  **kwargs) -> None:
        """
        Record a system-level event.

        Args:
            event_type: Short tag, e.g. "MODE_CHANGE", "CAPACITY_FULL", "ERROR".
            message:    Human-readable description.
            time:       Simulation time of the event.
        """
        if "timestamp" in kwargs:
            time = kwargs["timestamp"]
        self.system_events.append({"type": event_type, "message": message, "time": time})

    # ─── Print methods ──────────────────────────────────────────────────────────

    def print_request_table(self) -> None:
        """
        Print a uniformly aligned table of all logged requests.

        Columns: Req │ Time │ Flr │ Dir │ Dest │ To │ Wait │ Pickup │ Fuzzy │ GA% │ Status
        """
        print()
        print(self._top(TABLE_W))
        print(self._title(" REQUEST ASSIGNMENT LOG ", TABLE_W))
        print(self._mid(TABLE_W))
        print(self._col_header())
        print(self._col_divider())

        if not self.request_logs:
            print(self._blank(TABLE_W))
            print(self._row("  No requests have been logged yet.", TABLE_W))
            print(self._blank(TABLE_W))
        else:
            for log in self.request_logs:
                print(self._data_row(log))

        print(self._bot(TABLE_W))

    def print_elevator_summary(self, elevators: list) -> None:
        """
        Print a per-elevator performance panel.

        Shows: floors traveled, passengers served, avg wait,
               energy consumed, energy regenerated, net energy.
        """
        W = PANEL_W
        print()
        print(self._top(W))
        print(self._title(" PER-ELEVATOR PERFORMANCE SUMMARY ", W))
        print(self._mid(W))

        def kv(label: str, value: str) -> None:
            line = f"  {label:<28}  {value}"
            print("  ║ " + line.ljust(W - 2) + " ║")

        for i, elev in enumerate(elevators):
            elev_logs  = [lg for lg in self.request_logs if lg["assigned_to"] == elev.id]
            wait_times = [
                lg["_request_ref"].wait_time
                for lg in elev_logs
                if lg.get("_request_ref") and lg["_request_ref"].wait_time is not None
            ]
            avg_wait  = sum(wait_times) / len(wait_times) if wait_times else 0.0
            net_enrg  = elev.energy_consumed - elev.energy_regenerated

            print(self._blank(W))
            print("  ║ " + f"  ▸ Elevator E{elev.id}".ljust(W - 2) + " ║")
            kv("Floors Traveled",        f"{elev.total_floors_traveled:.1f}")
            kv("Passengers Served",      str(elev.passengers_served))
            kv("Requests Assigned",      str(len(elev_logs)))
            kv("Average Wait Time",      f"{avg_wait:.1f} s")
            kv("Energy Consumed",        f"{elev.energy_consumed:.2f} units")
            kv("Energy Regenerated",     f"{elev.energy_regenerated:.2f} units")
            kv("Net Energy",             f"{net_enrg:.2f} units")

            if i < len(elevators) - 1:
                print(self._div(W))

        print(self._blank(W))
        print(self._bot(W))

    def print_system_summary(self, traffic_analyzer=None) -> None:
        """
        Print the system-wide aggregated performance summary.

        Shows: total requests, GA improvement stats, wait time
               statistics, and traffic mode distribution.
        """
        W = PANEL_W
        print()
        print(self._top(W))
        print(self._title(" SYSTEM-WIDE PERFORMANCE SUMMARY ", W))
        print(self._mid(W))
        print(self._blank(W))

        def kv(label: str, value: str) -> None:
            line = f"  {label:<28}  {value}"
            print("  ║ " + line.ljust(W - 2) + " ║")

        # GA statistics
        ga_imps = [
            lg["ga_improvement"]
            for lg in self.request_logs
            if lg["ga_improvement"] is not None and lg["ga_improvement"] > 0
        ]
        total_ga = sum(ga_imps) if ga_imps else 0.0
        avg_ga   = total_ga / len(ga_imps) if ga_imps else 0.0

        kv("Total Requests Processed",  str(len(self.request_logs)))
        kv("GA Optimised Requests",     str(len(ga_imps)))
        kv("Total GA Distance Saved",   f"{total_ga:.1f} floors")
        kv("Average GA Improvement",    f"{avg_ga:.1f}%")

        # Wait time stats
        wait_times = [
            lg["_request_ref"].wait_time
            for lg in self.request_logs
            if lg.get("_request_ref") and lg["_request_ref"].wait_time is not None
        ]
        if wait_times:
            print(self._div(W))
            kv("Best Wait Time",            f"{min(wait_times):.1f} s")
            kv("Worst Wait Time",           f"{max(wait_times):.1f} s")
            kv("Average Wait Time",         f"{sum(wait_times)/len(wait_times):.1f} s")
        else:
            kv("Wait Time Data",            "No pickups recorded yet")

        # Traffic mode stats
        if traffic_analyzer:
            try:
                mode_dist = traffic_analyzer.get_mode_distribution()
                print(self._div(W))
                kv("Current Traffic Mode",      mode_dist.get("current_mode", "—"))
                kv("Mode Transitions",          str(mode_dist.get("total_transitions", 0)))
            except Exception:
                pass

        # Anomaly count
        non_opt = [e for e in self.system_events if e["type"] == "NON_OPTIMAL"]
        if non_opt:
            print(self._div(W))
            kv("Non-Optimal Assignments",   str(len(non_opt)))

        print(self._blank(W))
        print(self._bot(W))

    def print_full_summary(self, elevators: list, traffic_analyzer=None) -> None:
        """Print all three summary sections in sequence."""
        self.print_request_table()
        self.print_elevator_summary(elevators)
        self.print_system_summary(traffic_analyzer)
