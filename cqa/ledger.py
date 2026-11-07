import math
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


class BudgetExceeded(Exception):
    pass


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

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def committed(self):
        with self.connect() as db:
            return db.execute("SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM usage").fetchone()[0]

    def reserve(self, model: str, maximum_cost: float, run_ceiling: float):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            total = db.execute("SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM usage").fetchone()[0]
            if total + maximum_cost > min(self.limit, run_ceiling) + 1e-9:
                raise BudgetExceeded("Insufficient remaining budget for this request's conservative reservation")
            if self.budget_group is not None:
                grouped = db.execute("SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM usage WHERE budget_group=?",
                                     (self.budget_group,)).fetchone()[0]
                if grouped + maximum_cost > self.group_limit + 1e-9:
                    raise BudgetExceeded("Batch budget cannot cover the next conservative reservation")
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
        return {"lifetime_committed_usd": round(self.committed(), 6), "lifetime_limit_usd": self.limit,
                "attempts_by_status": dict(rows)}

    def group_committed(self, group_id):
        with self.connect() as db:
            return round(db.execute("SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM usage WHERE budget_group=?",
                                    (group_id,)).fetchone()[0], 6)
