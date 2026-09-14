# -*- coding: utf-8 -*-
from typing import Any, Dict, List
from app.core.database import DatabaseManager
from app.core.jalali import now_iso


class BankReconciliationRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self._ensure()

    def _ensure(self) -> None:
        with self.db.connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS bank_reconciliations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                treasury_account_id INTEGER NOT NULL,
                statement_date TEXT,
                book_balance INTEGER, statement_balance INTEGER, difference INTEGER,
                note TEXT, created_at TEXT, created_by INTEGER)""")
            c.commit()

    def list_banks(self) -> List[Dict[str, Any]]:
        with self.db.connect() as c:
            return [dict(r) for r in c.execute(
                "SELECT id, code, name, current_balance FROM treasury_accounts "
                "WHERE account_type='BANK' AND is_active=1 ORDER BY code").fetchall()]

    def transactions(self, account_id: int) -> List[Dict[str, Any]]:
        with self.db.connect() as c:
            return [dict(r) for r in c.execute(
                "SELECT transaction_date, transaction_type, amount, balance_after, description "
                "FROM treasury_transactions WHERE treasury_account_id=? "
                "ORDER BY transaction_date DESC, id DESC", (account_id,)).fetchall()]

    def save(self, account_id, statement_date, book_bal, stmt_bal, note, user_id) -> int:
        with self.db.connect() as c:
            cur = c.execute(
                "INSERT INTO bank_reconciliations (treasury_account_id,statement_date,book_balance,"
                "statement_balance,difference,note,created_at,created_by) VALUES (?,?,?,?,?,?,?,?)",
                (account_id, statement_date, book_bal, stmt_bal, stmt_bal - book_bal, note, now_iso(), user_id))
            c.commit(); return cur.lastrowid

    def history(self, account_id: int) -> List[Dict[str, Any]]:
        with self.db.connect() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM bank_reconciliations WHERE treasury_account_id=? "
                "ORDER BY id DESC", (account_id,)).fetchall()]