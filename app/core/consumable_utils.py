# -*- coding: utf-8 -*-
"""
consumable_utils.py - اقلام مصرفی انبار (Consumable Items) v2

- کد خودکار: CONS-0001 و... (شمارندهٔ خودکار)
- موجودی مستقل هر قلم
- هر قلم به انبار و واحد وصل است

استفاده:
    from app.core.consumable_utils import (
        ensure_consumables_table, list_consumables, add_consumable,
        update_consumable, delete_consumable, get_consumable,
        next_consumable_code,
    )
"""
import sqlite3
from typing import Any, Dict, List, Optional


def ensure_consumables_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS consumable_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            unit_id INTEGER,
            warehouse_id INTEGER,
            opening_qty INTEGER DEFAULT 0,
            current_qty INTEGER DEFAULT 0,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()


def next_consumable_code(conn: sqlite3.Connection) -> str:
    """شماره بعدی: CONS-0001 و..."""
    ensure_consumables_table(conn)
    row = conn.execute(
        "SELECT MAX(CAST(SUBSTR(code, 6) AS INTEGER)) FROM consumable_items WHERE code LIKE 'CONS-%'"
    ).fetchone()
    nxt = (int(row[0]) if row and row[0] else 0) + 1
    return 'CONS-{:04d}'.format(nxt)


def list_consumables(conn: sqlite3.Connection, warehouse_id: Optional[int] = None,
                     active_only: bool = True) -> List[Dict[str, Any]]:
    ensure_consumables_table(conn)
    query = (
        'SELECT ci.id, ci.name, ci.code, ci.unit_id, ci.warehouse_id, '
        'ci.opening_qty, ci.current_qty, ci.description, ci.is_active, '
        'COALESCE(u.name, \'-\') AS unit_name, '
        'COALESCE(w.name, \'-\') AS warehouse_name '
        'FROM consumable_items ci '
        'LEFT JOIN units u ON u.id = ci.unit_id '
        'LEFT JOIN warehouses w ON w.id = ci.warehouse_id '
    )
    conds, params = [], []
    if active_only:
        conds.append('ci.is_active = 1')
    if warehouse_id:
        conds.append('ci.warehouse_id = ?')
        params.append(warehouse_id)
    if conds:
        query += 'WHERE ' + ' AND '.join(conds)
    query += ' ORDER BY ci.name'
    rows = conn.execute(query, params).fetchall()
    return [
        {
            'id': r[0], 'name': r[1], 'code': r[2], 'unit_id': r[3],
            'warehouse_id': r[4], 'opening_qty': r[5], 'current_qty': r[6],
            'description': r[7], 'is_active': r[8],
            'unit_name': r[9], 'warehouse_name': r[10],
        }
        for r in rows
    ]


def add_consumable(conn: sqlite3.Connection, name: str, unit_id: Optional[int],
                   warehouse_id: Optional[int], opening_qty: int = 0,
                   code: str = None, description: str = None) -> int:
    ensure_consumables_table(conn)
    if not code:
        code = next_consumable_code(conn)
    cur = conn.execute(
        'INSERT INTO consumable_items (name, code, unit_id, warehouse_id, '
        'opening_qty, current_qty, description, is_active, created_at, updated_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)',
        (name, code, unit_id, warehouse_id, opening_qty, opening_qty,
         description, '2026-08-05 00:00:00', '2026-08-05 00:00:00'),
    )
    conn.commit()
    return int(cur.lastrowid)


def update_consumable(conn: sqlite3.Connection, item_id: int, name: str = None,
                      unit_id: Optional[int] = None, warehouse_id: Optional[int] = None,
                      description: str = None, is_active: int = None) -> None:
    ensure_consumables_table(conn)
    sets, params = [], []
    if name is not None:
        sets.append('name = ?'); params.append(name)
    if unit_id is not None:
        sets.append('unit_id = ?'); params.append(unit_id)
    if warehouse_id is not None:
        sets.append('warehouse_id = ?'); params.append(warehouse_id)
    if description is not None:
        sets.append('description = ?'); params.append(description)
    if is_active is not None:
        sets.append('is_active = ?'); params.append(int(is_active))
    if not sets:
        return
    sets.append('updated_at = ?'); params.append('2026-08-05 00:00:00')
    params.append(item_id)
    conn.execute('UPDATE consumable_items SET {} WHERE id = ?'.format(', '.join(sets)), params)
    conn.commit()


def delete_consumable(conn: sqlite3.Connection, item_id: int) -> None:
    ensure_consumables_table(conn)
    conn.execute('UPDATE consumable_items SET is_active = 0, updated_at = ? WHERE id = ?',
                 ('2026-08-05 00:00:00', item_id))
    conn.commit()


def get_consumable(conn: sqlite3.Connection, item_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        'SELECT id, name, code, unit_id, warehouse_id, opening_qty, current_qty, '
        'description, is_active FROM consumable_items WHERE id = ?',
        (item_id,),
    ).fetchone()
    if not row:
        return None
    return {
        'id': row[0], 'name': row[1], 'code': row[2], 'unit_id': row[3],
        'warehouse_id': row[4], 'opening_qty': row[5], 'current_qty': row[6],
        'description': row[7], 'is_active': row[8],
    }


def reduce_consumable_qty(conn: sqlite3.Connection, item_id: int, qty: int) -> bool:
    row = conn.execute('SELECT current_qty FROM consumable_items WHERE id = ?', (item_id,)).fetchone()
    if not row:
        return False
    current = int(row[0] or 0)
    if current < qty:
        return False
    conn.execute(
        'UPDATE consumable_items SET current_qty = ?, updated_at = ? WHERE id = ?',
        (current - qty, '2026-08-05 00:00:00', item_id),
    )
    return True


def ensure_expenses_qty_columns(conn: sqlite3.Connection) -> None:
    """اطمینان از وجود ستون‌های quantity و consumable_item_id در expenses"""
    cols = [r[1] for r in conn.execute('PRAGMA table_info(expenses)').fetchall()]
    if 'quantity' not in cols:
        try:
            conn.execute('ALTER TABLE expenses ADD COLUMN quantity INTEGER DEFAULT 1')
        except Exception:
            pass
    if 'consumable_item_id' not in cols:
        try:
            conn.execute('ALTER TABLE expenses ADD COLUMN consumable_item_id INTEGER')
        except Exception:
            pass
    conn.commit()
