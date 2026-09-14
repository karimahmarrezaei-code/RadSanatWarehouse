# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from app.core.database import DatabaseManager
from app.core.jalali import now_iso


class FiscalPeriodRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self._ensure()

    def _ensure(self) -> None:
        with self.db.connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS fiscal_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL, end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN','CLOSED')),
                created_by INTEGER, created_at TEXT,
                closed_by INTEGER, closed_at TEXT)""")
            c.commit()

    def list_periods(self) -> List[Dict[str, Any]]:
        with self.db.connect() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM fiscal_periods ORDER BY start_date DESC").fetchall()]

    def create(self, name, start, end, user_id) -> int:
        with self.db.connect() as c:
            cur = c.execute(
                "INSERT INTO fiscal_periods (name,start_date,end_date,status,created_by,created_at) "
                "VALUES (?,?,?,'OPEN',?,?)", (name, start, end, user_id, now_iso()))
            c.commit(); return cur.lastrowid

    def close(self, pid, user_id) -> None:
        with self.db.connect() as c:
            c.execute("UPDATE fiscal_periods SET status='CLOSED', closed_by=?, closed_at=? WHERE id=?",
                      (user_id, now_iso(), pid)); c.commit()

    def reopen(self, pid, user_id) -> None:
        with self.db.connect() as c:
            c.execute("UPDATE fiscal_periods SET status='OPEN', closed_by=NULL, closed_at=NULL WHERE id=?",
                      (pid,)); c.commit()

    def locked_period(self, date_iso: str) -> Optional[Dict[str, Any]]:
        """اگر تاریخ داخل یک دورهٔ بسته باشد، آن دوره را برمی‌گرداند"""
        with self.db.connect() as c:
            r = c.execute("SELECT * FROM fiscal_periods WHERE status='CLOSED' "
                          "AND ? BETWEEN start_date AND end_date", (date_iso,)).fetchone()
        return dict(r) if r else None