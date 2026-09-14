# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from app.core.database import DatabaseManager
from app.core.jalali import now_iso


class CheckbookRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with self.db.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS checkbook_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_no TEXT, sayyad_no TEXT, bank_name TEXT, branch TEXT,
                amount INTEGER NOT NULL DEFAULT 0,
                issue_date TEXT, due_date TEXT,
                issuer_person_id INTEGER,
                direction TEXT NOT NULL DEFAULT 'RECEIVED',
                status TEXT NOT NULL DEFAULT 'IN_HAND',
                source_type TEXT, source_id INTEGER,
                created_at TEXT, created_by INTEGER)""")
            conn.execute("""CREATE TABLE IF NOT EXISTS checkbook_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id INTEGER NOT NULL,
                move_type TEXT NOT NULL,
                move_date TEXT,
                from_person_id INTEGER, to_person_id INTEGER,
                ref_type TEXT, ref_id INTEGER,
                amount INTEGER, note TEXT,
                created_at TEXT, created_by INTEGER)""")
            conn.commit()

    def list_persons(self) -> List[Dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                "SELECT id, first_name, last_name FROM persons WHERE is_active=1 "
                "ORDER BY first_name, last_name").fetchall()
        return [{'id': r['id'], 'name': f"{r['first_name']} {r['last_name']}".strip()} for r in rows]

    def person_name(self, pid: Optional[int]) -> str:
        if not pid:
            return '-'
        with self.db.connect() as conn:
            r = conn.execute("SELECT first_name||' '||last_name FROM persons WHERE id=?", (pid,)).fetchone()
        return (r[0] or '-').strip() if r else '-'

    # ── ثبت چک دریافتی ──
    def create_check(self, p: Dict[str, Any], user_id: int) -> int:
        now = now_iso()
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO checkbook_checks (check_no,sayyad_no,bank_name,branch,amount,issue_date,due_date,"
                "issuer_person_id,direction,status,source_type,source_id,created_at,created_by) "
                "VALUES (?,?,?,?,?,?,?,?, 'RECEIVED','IN_HAND',?,?,?,?)",
                (p.get('check_no'), p.get('sayyad_no'), p.get('bank_name'), p.get('branch'),
                 int(p.get('amount') or 0), p.get('issue_date'), p.get('due_date'),
                 p.get('issuer_person_id'), p.get('source_type'), p.get('source_id'), now, user_id))
            cid = cur.lastrowid
            conn.execute(
                "INSERT INTO checkbook_movements (check_id,move_type,move_date,from_person_id,to_person_id,"
                "ref_type,ref_id,amount,note,created_at,created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (cid, 'RECEIVE', p.get('issue_date') or now, p.get('issuer_person_id'), None,
                 p.get('source_type'), p.get('source_id'), int(p.get('amount') or 0),
                 p.get('note') or 'دریافت چک', now, user_id))
            conn.commit()
        return cid

    def list_checks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        q = "SELECT * FROM checkbook_checks WHERE direction='RECEIVED'"
        params: List[Any] = []
        if status:
            q += " AND status=?"; params.append(status)
        q += " ORDER BY due_date"
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute(q, params).fetchall()]

    def get_check(self, cid: int) -> Optional[Dict[str, Any]]:
        with self.db.connect() as conn:
            r = conn.execute("SELECT * FROM checkbook_checks WHERE id=?", (cid,)).fetchone()
        return dict(r) if r else None

    def movements(self, cid: int) -> List[Dict[str, Any]]:
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT * FROM checkbook_movements WHERE check_id=? ORDER BY id", (cid,)).fetchall()]

    def on_hand_total(self) -> int:
        with self.db.connect() as conn:
            r = conn.execute("SELECT COALESCE(SUM(amount),0) FROM checkbook_checks "
                             "WHERE direction='RECEIVED' AND status='IN_HAND'").fetchone()
        return int(r[0] or 0)

    # ── عملیات‌ها ──
    def _move(self, cid, move_type, to_person, ref_type, ref_id, note, user_id):
        now = now_iso()
        chk = self.get_check(cid)
        with self.db.connect() as conn:
            conn.execute("INSERT INTO checkbook_movements (check_id,move_type,move_date,from_person_id,"
                         "to_person_id,ref_type,ref_id,amount,note,created_at,created_by) "
                         "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                         (cid, move_type, now, None, to_person, ref_type, ref_id,
                          int(chk['amount'] or 0), note, now, user_id))
            conn.commit()

    def spend_check(self, cid, to_person_id, ref_type, ref_id, note, user_id):
        self._move(cid, 'SPEND', to_person_id, ref_type, ref_id, note or 'خرج/انتقال چک', user_id)
        with self.db.connect() as conn:
            conn.execute("UPDATE checkbook_checks SET status='SPENT' WHERE id=?", (cid,)); conn.commit()

    def collect_check(self, cid, note, user_id):
        self._move(cid, 'COLLECT', None, None, None, note or 'وصول چک', user_id)
        with self.db.connect() as conn:
            conn.execute("UPDATE checkbook_checks SET status='COLLECTED' WHERE id=?", (cid,)); conn.commit()

    def bounce_check(self, cid, note, user_id):
        self._move(cid, 'BOUNCE', None, None, None, note or 'برگشت چک', user_id)
        with self.db.connect() as conn:
            conn.execute("UPDATE checkbook_checks SET status='BOUNCED' WHERE id=?", (cid,)); conn.commit()