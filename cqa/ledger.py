import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class BudgetExceeded(Exception):
    def __init__(self, message="Budget allowance exceeded", *, required=None, available=None):
        super().__init__(message)
        self.required, self.available = required, available


class Ledger:
    def __init__(self, path: Path, lifetime_limit: float, *, budget_group=None, group_limit=None):
        self.path, self.limit = path, lifetime_limit
        if budget_group is not None and (group_limit is None or not math.isfinite(group_limit) or group_limit <= 0):
            raise ValueError("A budget group requires a positive finite limit")
        self.budget_group, self.group_limit = budget_group, group_limit
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, model TEXT NOT NULL,
                status TEXT NOT NULL, reserved REAL NOT NULL, cost REAL,
                input_tokens INTEGER, output_tokens INTEGER)""")
            db.execute("BEGIN IMMEDIATE")
            if "budget_group" not in {r[1] for r in db.execute("PRAGMA table_info(usage)")}:
                db.execute("ALTER TABLE usage ADD COLUMN budget_group TEXT")
            db.execute("""CREATE TABLE IF NOT EXISTS budget_holds (
                id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, model TEXT NOT NULL,
                remaining REAL NOT NULL, budget_group TEXT, active INTEGER NOT NULL DEFAULT 1)""")

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def committed(self):
        with self.connect() as db:
            return self._committed(db)

    def _committed(self, db, *, grouped=False):
        where = " WHERE budget_group=?" if grouped else ""
        args = (self.budget_group,) if grouped else ()
        usage = db.execute("SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM usage" + where, args).fetchone()[0]
        held = db.execute("SELECT COALESCE(SUM(remaining),0) FROM budget_holds WHERE active=1" +
                          (" AND budget_group=?" if grouped else ""), args).fetchone()[0]
        return usage + held

    def _check_capacity(self, db, maximum_cost, run_ceiling):
        if not math.isfinite(maximum_cost) or maximum_cost <= 0:
            raise ValueError("Reservation must be positive and finite")
        if self._committed(db) + maximum_cost > min(self.limit, run_ceiling) + 1e-9:
            raise BudgetExceeded("Insufficient remaining budget for the first attempt and bounded repair allowance",
                required=maximum_cost, available=max(0, min(self.limit, run_ceiling) - self._committed(db)))
        if self.budget_group is not None and self._committed(db, grouped=True) + maximum_cost > self.group_limit + 1e-9:
            raise BudgetExceeded("Batch budget cannot cover the first attempt and bounded repair allowance",
                required=maximum_cost, available=max(0, self.group_limit - self._committed(db, grouped=True)))

    def hold(self, model, maximum_cost, run_ceiling):
        """Atomically protect a complete bounded stage from concurrent budget consumers."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._check_capacity(db, maximum_cost, run_ceiling)
            return db.execute("INSERT INTO budget_holds(created_at,model,remaining,budget_group) VALUES (?,?,?,?)",
                (datetime.now(UTC).isoformat(), model, maximum_cost, self.budget_group)).lastrowid

    def release(self, hold_id):
        with self.connect() as db:
            db.execute("UPDATE budget_holds SET active=0,remaining=0 WHERE id=?", (hold_id,))

    def release_interrupted_group(self, group_id):
        """Release only unspent allowance; submitted calls retain their unknown-cost reservation."""
        if group_id is None:
            raise ValueError("Recovery requires an explicitly interrupted application batch")
        with self.connect() as db:
            db.execute("UPDATE budget_holds SET active=0,remaining=0 WHERE budget_group=?", (group_id,))

    def reserve(self, model: str, maximum_cost: float, run_ceiling: float, *, hold_id=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if hold_id is None:
                self._check_capacity(db, maximum_cost, run_ceiling)
            else:
                if not math.isfinite(maximum_cost) or maximum_cost <= 0:
                    raise ValueError("Reservation must be positive and finite")
                hold = db.execute("SELECT model,remaining,budget_group FROM budget_holds WHERE id=? AND active=1",
                                  (hold_id,)).fetchone()
                if hold is None or hold[0] != model or hold[2] != self.budget_group:
                    raise ValueError("Reservation does not belong to this active model/budget hold")
                if maximum_cost > hold[1] + 1e-9:
                    raise BudgetExceeded("Request exceeds its protected repair allowance")
                db.execute("UPDATE budget_holds SET remaining=MAX(0,remaining-?) WHERE id=?", (maximum_cost, hold_id))
            cursor = db.execute("INSERT INTO usage(created_at,model,status,reserved,budget_group) VALUES (?,?,?,?,?)",
                                (datetime.now(UTC).isoformat(), model, "reserved", maximum_cost, self.budget_group))
            return cursor.lastrowid

    def finish(self, call_id, status, *, cost=None, input_tokens=None, output_tokens=None):
        # Unknown usage retains the full reservation, including timeouts and crashes.
        with self.connect() as db:
            db.execute("UPDATE usage SET status=?,cost=?,input_tokens=?,output_tokens=? WHERE id=?",
                       (status, cost, input_tokens, output_tokens, call_id))

    def summary(self):
        with self.connect() as db:
            rows = db.execute("SELECT status,COUNT(*) FROM usage GROUP BY status").fetchall()
            held = db.execute("SELECT COALESCE(SUM(remaining),0) FROM budget_holds WHERE active=1").fetchone()[0]
        return {"lifetime_committed_usd": round(self.committed(), 6), "lifetime_limit_usd": self.limit,
                "protected_allowance_usd": round(held, 6),
                "attempts_by_status": dict(rows)}

    def group_committed(self, group_id):
        with self.connect() as db:
            usage = db.execute("SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM usage WHERE budget_group=?",
                               (group_id,)).fetchone()[0]
            held = db.execute("SELECT COALESCE(SUM(remaining),0) FROM budget_holds WHERE active=1 AND budget_group=?",
                              (group_id,)).fetchone()[0]
            return round(usage + held, 6)
