# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from app.core.database import DatabaseManager

TYPE_FA = {'ASSET': 'دارایی', 'LIABILITY': 'بدهی', 'EQUITY': 'سرمایه',
           'INCOME': 'درآمد', 'EXPENSE': 'هزینه'}


class GeneralLedgerRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def has_entries(self) -> bool:
        with self.db.connect() as c:
            r = c.execute("SELECT COUNT(*) FROM journal_entries").fetchone()
        return int(r[0]) > 0

    def list_accounts(self, account_type: Optional[str] = None) -> List[Dict[str, Any]]:
        q = """SELECT la.id, la.code, la.name, la.account_type, la.parent_id,
                      COALESCE(SUM(jl.debit_amount),0)  AS total_debit,
                      COALESCE(SUM(jl.credit_amount),0) AS total_credit
               FROM ledger_accounts la
               LEFT JOIN journal_lines jl ON jl.account_id = la.id"""
        params: List[Any] = []
        if account_type:
            q += " WHERE la.account_type=?"
            params.append(account_type)
        q += " GROUP BY la.id ORDER BY la.code"
        with self.db.connect() as c:
            return [dict(r) for r in c.execute(q, params).fetchall()]

    def account_lines(self, account_id: int, date_from=None, date_to=None) -> List[Dict[str, Any]]:
        q = """SELECT je.entry_no, je.entry_date, je.description AS entry_desc,
                      jl.line_no, jl.debit_amount, jl.credit_amount, jl.description,
                      (p.first_name||' '||p.last_name) AS person_name
               FROM journal_lines jl
               JOIN journal_entries je ON je.id = jl.journal_entry_id
               LEFT JOIN persons p ON p.id = jl.person_id
               WHERE jl.account_id=?"""
        params: List[Any] = [account_id]
        if date_from:
            q += " AND je.entry_date>=?"; params.append(date_from)
        if date_to:
            q += " AND je.entry_date<=?"; params.append(date_to)
        q += " ORDER BY je.entry_date, je.id, jl.line_no"
        with self.db.connect() as c:
            return [dict(r) for r in c.execute(q, params).fetchall()]