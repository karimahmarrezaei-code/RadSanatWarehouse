# -*- coding: utf-8 -*-
"""
DatabaseManager - اصلاح‌شده

⚠️ نسخه اصلاح‌شده (بازبینی ۱۴۰۵/۰۵/۱۱):
  [FIX] تعمیر کامل تخریب‌های کپی-پیست (سینتکس): __init__، SCHEMA_PATH.read_text، fd.finance_date، < و ...
  [NOTE] PRAGMA foreign_keys = ON روی همه اتصال‌ها → قید FK جدول payment_entries زنده است.
         این یعنی تصمیم C1 (cash_accounts یا treasury_accounts) اجرای برنامه را قفل کرده:
         - اگر cash_accounts وجود نداشته باشد → no such table
         - اگر وجود داشته باشد ولی FK به treasury_accounts باشد → FOREIGN KEY constraint failed
  [FIX] fetch_low_stock_pallets: هماهنگ‌سازی محاسبه موجودی بین دو شاخه (با/بدون انبار)
  [NOTE] fetch_dashboard_treasury_balances: وقتی فیلتر تاریخ داده شود، ستون current_balance
         عملاً «جمع گردش دوره» است نه مانده واقعی (نام‌گذاری گمراه‌کننده)
"""

import json
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .config import DB_PATH, SCHEMA_PATH, SEED_PATH, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from .jalali import now_iso
from .security import hash_password, verify_password


class _ClosingConnection(sqlite3.Connection):
    """اتصالی که هنگام خروج از with: commit و close می‌شود (رفع قفل دائمی).

    رفتار پیش‌فرض sqlite3 این است که with فقط commit کند و اتصال باز بماند؛
    همین اتصال‌های باز (با تراکنش معلق) عامل «database is locked» هستند.
    """

    def __exit__(self, exc_type, exc_val, exc_tb):  # type: ignore
        try:
            if exc_type is None:
                if self.in_transaction:
                    self.commit()
            else:
                if self.in_transaction:
                    self.rollback()
        finally:
            self.close()
        return False


class DatabaseManager:

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
            factory=_ClosingConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys = ON;')
        connection.execute('PRAGMA busy_timeout = 30000;')
        try:
            connection.execute('PRAGMA journal_mode = WAL;')
        except sqlite3.OperationalError:
            pass  # اگر لحظه‌ای قفل باشد، نادیده بگیر؛ WAL بعداً با اسکریپت اعمال می‌شود
        connection.execute('PRAGMA synchronous = NORMAL;')
        return connection


    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA_PATH.read_text(encoding='utf-8'))
            connection.executescript(SEED_PATH.read_text(encoding='utf-8'))
            connection.commit()
        self.ensure_default_admin()

    def ensure_default_admin(self) -> None:
        with self.connect() as connection:
            row = connection.execute(
                'SELECT id FROM users WHERE username = ? LIMIT 1',
                (DEFAULT_ADMIN_USERNAME,),
            ).fetchone()
            if row:
                return

            admin_role = connection.execute(
                'SELECT id FROM roles WHERE code = ? LIMIT 1',
                ('ADMIN',),
            ).fetchone()
            if not admin_role:
                raise RuntimeError('نقش ADMIN در دیتابیس پیدا نشد.')

            connection.execute(
                '''
                INSERT INTO users (
                    username, password_hash, full_name, mobile, email, role_id,
                    is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                ''',
                (
                    DEFAULT_ADMIN_USERNAME,
                    hash_password(DEFAULT_ADMIN_PASSWORD),
                    'مدیر سیستم',
                    None,
                    None,
                    admin_role['id'],
                    now_iso(),
                ),
            )
            connection.commit()

    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        with self.connect() as connection:
            row = connection.execute(
                '''
                SELECT users.id, users.username, users.password_hash, users.full_name,
                       users.is_active, roles.name AS role_name, roles.code AS role_code
                FROM users
                JOIN roles ON roles.id = users.role_id
                WHERE users.username = ?
                LIMIT 1
                ''',
                (username.strip(),),
            ).fetchone()

            if not row or not row['is_active']:
                return None
            if not verify_password(password, row['password_hash']):
                return None

            connection.execute(
                'UPDATE users SET last_login_at = ? WHERE id = ?',
                (now_iso(), row['id']),
            )
            connection.commit()

            user_id = row['id']
            return {
                'id': user_id,
                'username': row['username'],
                'full_name': row['full_name'],
                'role_name': row['role_name'],
                'role_code': row['role_code'],
                'permissions': sorted(self.fetch_user_permissions(user_id)),
            }

    def fetch_user_permissions(self, user_id: int) -> Set[str]:
        query = '''
            SELECT p.code
            FROM users u
            JOIN roles r ON r.id = u.role_id
            JOIN role_permissions rp ON rp.role_id = r.id
            JOIN permissions p ON p.id = rp.permission_id
            WHERE u.id = ?
        '''
        with self.connect() as connection:
            rows = connection.execute(query, (user_id,)).fetchall()
            return {row['code'] for row in rows}

    def user_has_permission(self, user_id: int, permission_code: str) -> bool:
        return permission_code in self.fetch_user_permissions(user_id)

    def log_audit(
        self,
        connection: sqlite3.Connection,
        user_id: Optional[int],
        entity_name: str,
        entity_id: Optional[str],
        action_name: str,
        old_values: Optional[Dict[str, Any]],
        new_values: Optional[Dict[str, Any]],
    ) -> None:
        connection.execute(
            '''
            INSERT INTO audit_logs (
                user_id, entity_name, entity_id, action_name,
                old_values_json, new_values_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                user_id,
                entity_name,
                entity_id,
                action_name,
                json.dumps(old_values, ensure_ascii=False) if old_values is not None else None,
                json.dumps(new_values, ensure_ascii=False) if new_values is not None else None,
                now_iso(),
            ),
        )

    def next_sequence_value(self, connection: sqlite3.Connection, name: str) -> str:
        row = connection.execute(
            'SELECT prefix, current_value, width FROM sequences WHERE name = ? LIMIT 1',
            (name,),
        ).fetchone()
        if not row:
            raise RuntimeError(f'Sequence not found: {name}')
        next_value = int(row['current_value']) + 1
        connection.execute(
            'UPDATE sequences SET current_value = ?, updated_at = ? WHERE name = ?',
            (next_value, now_iso(), name),
        )
        return f"{row['prefix']}{next_value:0{int(row['width'])}d}"

    def fetch_low_stock_pallets(self, warehouse_id: Optional[int] = None) -> List[sqlite3.Row]:
        if warehouse_id:
            query = '''
                SELECT
                    p.code,
                    p.name,
                    p.low_stock_threshold,
                    COALESCE(SUM(il.quantity), 0) AS current_stock
                FROM pallets p
                LEFT JOIN inventory_levels il
                    ON il.pallet_id = p.id AND il.warehouse_id = ?
                WHERE p.is_active = 1 AND p.low_stock_threshold > 0
                GROUP BY p.id
                HAVING current_stock <= p.low_stock_threshold
                ORDER BY current_stock ASC, p.name ASC
            '''
            with self.connect() as connection:
                return connection.execute(query, (warehouse_id,)).fetchall()

        query = '''
            SELECT
                p.code,
                p.name,
                p.low_stock_threshold,
                COALESCE(SUM(il.quantity), 0) AS current_stock
            FROM pallets p
            LEFT JOIN inventory_levels il ON il.pallet_id = p.id
            WHERE p.is_active = 1 AND p.low_stock_threshold > 0
            GROUP BY p.id
            HAVING current_stock <= p.low_stock_threshold
            ORDER BY current_stock ASC, p.name ASC
        '''
        with self.connect() as connection:
            return connection.execute(query).fetchall()

    def fetch_stats(self) -> Dict[str, int]:
        with self.connect() as connection:
            inbound_open = connection.execute(
                "SELECT COUNT(*) FROM inbound_loads WHERE load_status IN ('OPEN', 'PARTIAL') AND is_active = 1"
            ).fetchone()[0]
            outbound_open = connection.execute(
                "SELECT COUNT(*) FROM outbound_loads WHERE load_status IN ('OPEN', 'PARTIAL') AND is_active = 1"
            ).fetchone()[0]
            stats = {
                'pallets': connection.execute('SELECT COUNT(*) FROM pallets').fetchone()[0],
                'persons': connection.execute('SELECT COUNT(*) FROM persons').fetchone()[0],
                'warehouses': connection.execute('SELECT COUNT(*) FROM warehouses').fetchone()[0],
                'open_shipments': inbound_open + outbound_open,
            }
        return stats

    def list_dashboard_warehouses(self) -> List[Dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                'SELECT id, code, name FROM warehouses WHERE is_active = 1 ORDER BY name'
            ).fetchall()
            return [dict(row) for row in rows]

    def list_dashboard_persons(self) -> List[Dict[str, Any]]:
        query = '''
            SELECT p.id, p.first_name, p.last_name,
                   (SELECT GROUP_CONCAT(role_type) FROM person_roles pr WHERE pr.person_id = p.id) AS roles_csv
            FROM persons p
            WHERE p.is_active = 1
            ORDER BY p.first_name, p.last_name
        '''
        with self.connect() as connection:
            rows = connection.execute(query).fetchall()
            return [dict(row) for row in rows]

    def fetch_dashboard_period_summary(
        self,
        date_from: str,
        date_to: str,
        warehouse_id: Optional[int] = None,
        person_id: Optional[int] = None,
        operation_filter: str = 'ALL',
    ) -> Dict[str, int]:
        with self.connect() as connection:
            receipts_count = receipts_qty = issues_count = issues_qty = 0

            if operation_filter in ('ALL', 'INBOUND'):
                filters = ["wr.receipt_date BETWEEN ? AND ?", "wr.receipt_status <> 'CANCELLED'"]
                params: List[Any] = [date_from, date_to]
                if warehouse_id:
                    filters.append('EXISTS (SELECT 1 FROM warehouse_receipt_items wri WHERE wri.receipt_id = wr.id AND wri.warehouse_id = ?)')
                    params.append(warehouse_id)
                if person_id:
                    filters.append('(wr.supplier_id = ? OR wr.driver_id = ?)')
                    params.extend([person_id, person_id])
                query = f"SELECT COUNT(*) AS cnt, COALESCE(SUM(wr.delivered_qty), 0) AS qty FROM warehouse_receipts wr WHERE {' AND '.join(filters)}"
                row = connection.execute(query, params).fetchone()
                receipts_count = int(row['cnt']) if row else 0
                receipts_qty = int(row['qty']) if row else 0

            if operation_filter in ('ALL', 'OUTBOUND'):
                filters = ["wi.issue_date BETWEEN ? AND ?", "wi.issue_status <> 'CANCELLED'"]
                params = [date_from, date_to]
                if warehouse_id:
                    filters.append('EXISTS (SELECT 1 FROM warehouse_issue_items wii WHERE wii.issue_id = wi.id AND wii.warehouse_id = ?)')
                    params.append(warehouse_id)
                if person_id:
                    filters.append('(wi.customer_id = ? OR wi.driver_id = ?)')
                    params.extend([person_id, person_id])
                query = f"SELECT COUNT(*) AS cnt, COALESCE(SUM(wi.delivered_qty), 0) AS qty FROM warehouse_issues wi WHERE {' AND '.join(filters)}"
                row = connection.execute(query, params).fetchone()
                issues_count = int(row['cnt']) if row else 0
                issues_qty = int(row['qty']) if row else 0

            finance_filters = ["fd.finance_date BETWEEN ? AND ?", "fd.status <> 'CANCELLED'"]
            finance_params: List[Any] = [date_from, date_to]
            if person_id:
                finance_filters.append('fd.counterparty_person_id = ?')
                finance_params.append(person_id)
            if warehouse_id:
                finance_filters.append("((fd.receipt_id IS NOT NULL AND EXISTS (SELECT 1 FROM warehouse_receipt_items wri WHERE wri.receipt_id = fd.receipt_id AND wri.warehouse_id = ?)) OR (fd.issue_id IS NOT NULL AND EXISTS (SELECT 1 FROM warehouse_issue_items wii WHERE wii.issue_id = fd.issue_id AND wii.warehouse_id = ?)))")
                finance_params.extend([warehouse_id, warehouse_id])
            if operation_filter == 'INBOUND':
                finance_filters.append("fd.operation_type IN ('INBOUND_RECEIPT', 'INBOUND_FREIGHT')")
            elif operation_filter == 'OUTBOUND':
                finance_filters.append("fd.operation_type IN ('OUTBOUND_ISSUE', 'OUTBOUND_FREIGHT')")
            finance_query = f"SELECT COUNT(*) AS cnt, COALESCE(SUM(fd.total_amount), 0) AS total_amount FROM financial_documents fd WHERE {' AND '.join(finance_filters)}"
            finance_row = connection.execute(finance_query, finance_params).fetchone()
            return {
                'receipts_count': receipts_count,
                'receipts_qty': receipts_qty,
                'issues_count': issues_count,
                'issues_qty': issues_qty,
                'finance_docs_count': int(finance_row['cnt']) if finance_row else 0,
                'finance_total_amount': int(finance_row['total_amount']) if finance_row else 0,
            }

    def fetch_dashboard_financial_overview(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        person_id: Optional[int] = None,
        operation_filter: str = 'ALL',
    ) -> Dict[str, int]:
        filters = ["fd.status <> 'CANCELLED'"]
        params: List[Any] = []

        if date_from and date_to:
            filters.append('fd.finance_date BETWEEN ? AND ?')
            params.extend([date_from, date_to])
        if person_id:
            filters.append('fd.counterparty_person_id = ?')
            params.append(person_id)
        if warehouse_id:
            filters.append("((fd.receipt_id IS NOT NULL AND EXISTS (SELECT 1 FROM warehouse_receipt_items wri WHERE wri.receipt_id = fd.receipt_id AND wri.warehouse_id = ?)) OR (fd.issue_id IS NOT NULL AND EXISTS (SELECT 1 FROM warehouse_issue_items wii WHERE wii.issue_id = fd.issue_id AND wii.warehouse_id = ?)))")
            params.extend([warehouse_id, warehouse_id])
        if operation_filter == 'INBOUND':
            filters.append("fd.operation_type IN ('INBOUND_RECEIPT', 'INBOUND_FREIGHT')")
        elif operation_filter == 'OUTBOUND':
            filters.append("fd.operation_type IN ('OUTBOUND_ISSUE', 'OUTBOUND_FREIGHT')")

        query = f'''
            SELECT
                COALESCE(SUM(CASE WHEN direction = 'RECEIVABLE' THEN total_amount ELSE 0 END), 0) AS receivable_total,
                COALESCE(SUM(CASE WHEN direction = 'RECEIVABLE' THEN settled_amount ELSE 0 END), 0) AS receivable_settled,
                COALESCE(SUM(CASE WHEN direction = 'PAYABLE' THEN total_amount ELSE 0 END), 0) AS payable_total,
                COALESCE(SUM(CASE WHEN direction = 'PAYABLE' THEN settled_amount ELSE 0 END), 0) AS payable_settled,
                COALESCE(SUM(CASE WHEN status IN ('OPEN', 'PARTIAL') THEN 1 ELSE 0 END), 0) AS open_docs,
                COALESCE(SUM(CASE WHEN status = 'SETTLED' THEN 1 ELSE 0 END), 0) AS settled_docs
            FROM financial_documents fd
            WHERE {' AND '.join(filters)}
        '''
        with self.connect() as connection:
            row = connection.execute(query, params).fetchone()
            receivable_total = int(row['receivable_total']) if row else 0
            receivable_settled = int(row['receivable_settled']) if row else 0
            payable_total = int(row['payable_total']) if row else 0
            payable_settled = int(row['payable_settled']) if row else 0
            return {
                'receivable_total': receivable_total,
                'receivable_balance': receivable_total - receivable_settled,
                'payable_total': payable_total,
                'payable_balance': payable_total - payable_settled,
                'open_docs': int(row['open_docs']) if row else 0,
                'settled_docs': int(row['settled_docs']) if row else 0,
            }

    def fetch_dashboard_warehouse_values(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        person_id: Optional[int] = None,
        operation_filter: str = 'ALL',
    ) -> List[Dict[str, Any]]:
        join_condition = 'it.warehouse_id = w.id'
        params: List[Any] = []

        if date_from and date_to:
            join_condition += ' AND it.transaction_date BETWEEN ? AND ?'
            params.extend([date_from, date_to])
        if operation_filter == 'INBOUND':
            join_condition += " AND it.transaction_type = 'IN'"
        elif operation_filter == 'OUTBOUND':
            join_condition += " AND it.transaction_type = 'OUT'"
        if person_id:
            join_condition += " AND ((it.reference_type = 'RECEIPT' AND EXISTS (SELECT 1 FROM warehouse_receipts wr WHERE wr.id = it.reference_id AND (wr.supplier_id = ? OR wr.driver_id = ?))) OR (it.reference_type = 'ISSUE' AND EXISTS (SELECT 1 FROM warehouse_issues wi WHERE wi.id = it.reference_id AND (wi.customer_id = ? OR wi.driver_id = ?))))"
            params.extend([person_id, person_id, person_id, person_id])

        filters = ['w.is_active = 1']
        if warehouse_id:
            filters.append('w.id = ?')
            params.append(warehouse_id)

        query = f'''
            SELECT
                w.id,
                w.code,
                w.name,
                COALESCE(SUM(it.qty_in - it.qty_out), 0) AS current_qty,
                COALESCE(SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE -it.total_price END), 0) AS current_value,
                COALESCE(SUM(it.qty_in - it.qty_out), 0) AS period_qty_delta,
                COALESCE(SUM(CASE WHEN it.transaction_type = 'IN' THEN it.total_price ELSE -it.total_price END), 0) AS period_value_delta
            FROM warehouses w
            LEFT JOIN inventory_transactions it ON {join_condition}
            WHERE {' AND '.join(filters)}
            GROUP BY w.id
            ORDER BY current_value DESC, w.name
        '''
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def fetch_dashboard_treasury_balances(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        person_id: Optional[int] = None,
        operation_filter: str = 'ALL',
    ) -> List[Dict[str, Any]]:
        sub_filters: List[str] = []
        sub_params: List[Any] = []
        contextual_filter = bool(warehouse_id or person_id or operation_filter != 'ALL')

        if date_from and date_to:
            sub_filters.append('tt.transaction_date BETWEEN ? AND ?')
            sub_params.extend([date_from, date_to])
        if contextual_filter:
            sub_filters.append("tt.source_type = 'PAYMENT_ENTRY'")
        if person_id:
            sub_filters.append('fd.counterparty_person_id = ?')
            sub_params.append(person_id)
        if warehouse_id:
            sub_filters.append("((fd.receipt_id IS NOT NULL AND EXISTS (SELECT 1 FROM warehouse_receipt_items wri WHERE wri.receipt_id = fd.receipt_id AND wri.warehouse_id = ?)) OR (fd.issue_id IS NOT NULL AND EXISTS (SELECT 1 FROM warehouse_issue_items wii WHERE wii.issue_id = fd.issue_id AND wii.warehouse_id = ?)))")
            sub_params.extend([warehouse_id, warehouse_id])
        if operation_filter == 'INBOUND':
            sub_filters.append("fd.operation_type IN ('INBOUND_RECEIPT', 'INBOUND_FREIGHT')")
        elif operation_filter == 'OUTBOUND':
            sub_filters.append("fd.operation_type IN ('OUTBOUND_ISSUE', 'OUTBOUND_FREIGHT')")

        sub_where = f"WHERE {' AND '.join(sub_filters)}" if sub_filters else ''
        query = f'''
            SELECT
                ta.id,
                ta.code,
                ta.name,
                ta.account_type,
                COALESCE(SUM(CASE WHEN tx.transaction_type = 'IN' THEN tx.amount ELSE -tx.amount END), 0) AS current_balance,
                COALESCE(SUM(CASE WHEN tx.transaction_type = 'IN' THEN tx.amount ELSE -tx.amount END), 0) AS period_balance_delta
            FROM treasury_accounts ta
            LEFT JOIN (
                SELECT tt.treasury_account_id, tt.transaction_type, tt.amount
                FROM treasury_transactions tt
                LEFT JOIN payment_entries pe ON tt.source_type = 'PAYMENT_ENTRY' AND pe.id = tt.source_id
                LEFT JOIN financial_documents fd ON fd.id = pe.financial_document_id
                {sub_where}
            ) tx ON tx.treasury_account_id = ta.id
            WHERE ta.is_active = 1
            GROUP BY ta.id
            ORDER BY current_balance DESC, ta.name
        '''
        with self.connect() as connection:
            rows = connection.execute(query, sub_params).fetchall()
            return [dict(row) for row in rows]

    def fetch_dashboard_recent_activity(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        person_id: Optional[int] = None,
        operation_filter: str = 'ALL',
    ) -> List[Dict[str, Any]]:
        if not date_from or not date_to:
            end_day = date.today()
            start_day = end_day - timedelta(days=6)
            date_from = start_day.isoformat()
            date_to = end_day.isoformat()

        start_day = date.fromisoformat(date_from)
        end_day = date.fromisoformat(date_to)
        days: Dict[str, Dict[str, Any]] = {}
        current = start_day
        while current <= end_day:
            day_text = current.isoformat()
            days[day_text] = {'day_text': day_text, 'day_label': day_text[5:], 'receipts': 0, 'issues': 0, 'finance_docs': 0}
            current += timedelta(days=1)

        with self.connect() as connection:
            if operation_filter in ('ALL', 'INBOUND'):
                filters = ["wr.receipt_date BETWEEN ? AND ?", "wr.receipt_status <> 'CANCELLED'"]
                params: List[Any] = [date_from, date_to]
                if warehouse_id:
                    filters.append('EXISTS (SELECT 1 FROM warehouse_receipt_items wri WHERE wri.receipt_id = wr.id AND wri.warehouse_id = ?)')
                    params.append(warehouse_id)
                if person_id:
                    filters.append('(wr.supplier_id = ? OR wr.driver_id = ?)')
                    params.extend([person_id, person_id])
                query = f"SELECT wr.receipt_date AS day_text, COUNT(*) AS cnt FROM warehouse_receipts wr WHERE {' AND '.join(filters)} GROUP BY wr.receipt_date"
                for row in connection.execute(query, params).fetchall():
                    if row['day_text'] in days:
                        days[row['day_text']]['receipts'] = int(row['cnt'])

            if operation_filter in ('ALL', 'OUTBOUND'):
                filters = ["wi.issue_date BETWEEN ? AND ?", "wi.issue_status <> 'CANCELLED'"]
                params = [date_from, date_to]
                if warehouse_id:
                    filters.append('EXISTS (SELECT 1 FROM warehouse_issue_items wii WHERE wii.issue_id = wi.id AND wii.warehouse_id = ?)')
                    params.append(warehouse_id)
                if person_id:
                    filters.append('(wi.customer_id = ? OR wi.driver_id = ?)')
                    params.extend([person_id, person_id])
                query = f"SELECT wi.issue_date AS day_text, COUNT(*) AS cnt FROM warehouse_issues wi WHERE {' AND '.join(filters)} GROUP BY wi.issue_date"
                for row in connection.execute(query, params).fetchall():
                    if row['day_text'] in days:
                        days[row['day_text']]['issues'] = int(row['cnt'])

            filters = ["fd.finance_date BETWEEN ? AND ?", "fd.status <> 'CANCELLED'"]
            params = [date_from, date_to]
            if person_id:
                filters.append('fd.counterparty_person_id = ?')
                params.append(person_id)
            if warehouse_id:
                filters.append("((fd.receipt_id IS NOT NULL AND EXISTS (SELECT 1 FROM warehouse_receipt_items wri WHERE wri.receipt_id = fd.receipt_id AND wri.warehouse_id = ?)) OR (fd.issue_id IS NOT NULL AND EXISTS (SELECT 1 FROM warehouse_issue_items wii WHERE wii.issue_id = fd.issue_id AND wii.warehouse_id = ?)))")
                params.extend([warehouse_id, warehouse_id])
            if operation_filter == 'INBOUND':
                filters.append("fd.operation_type IN ('INBOUND_RECEIPT', 'INBOUND_FREIGHT')")
            elif operation_filter == 'OUTBOUND':
                filters.append("fd.operation_type IN ('OUTBOUND_ISSUE', 'OUTBOUND_FREIGHT')")
            query = f"SELECT fd.finance_date AS day_text, COUNT(*) AS cnt FROM financial_documents fd WHERE {' AND '.join(filters)} GROUP BY fd.finance_date"
            for row in connection.execute(query, params).fetchall():
                if row['day_text'] in days:
                    days[row['day_text']]['finance_docs'] = int(row['cnt'])

        return [days[key] for key in sorted(days.keys())]
