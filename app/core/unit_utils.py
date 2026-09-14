# -*- coding: utf-8 -*-
"""
unit_utils.py - واحدهای کالا (Unit of Measure)

مدیریت واحدهای اندازه‌گیری کالاها (عدد، کارتن، لیتر، رول، ...)
- جدول units با واحدهای پیش‌فرض seed می‌شود
- امکان افزودن واحد جدید توسط کاربر
- هر کالا (پالت) می‌تواند واحد داشته باشد

استفاده:
    from app.core.unit_utils import ensure_units_table, list_units, add_unit, get_unit
"""
import sqlite3
from typing import Any, Dict, List, Optional

DEFAULT_UNITS = [
    ('عدد', 'PCS', 'تعداد تک'),
    ('کارتن', 'CTN', 'جعبه کارتنی'),
    ('لیتر', 'LTR', 'مایع'),
    ('رول', 'ROL', 'رول/طاقه'),
    ('متر', 'MTR', 'طول'),
    'متر مربع',
    'کیلوگرم',
    'شاخه',
    'جعبه',
    'بسته',
    'حلقه',
    'دستگاه',
]


def ensure_units_table(conn: sqlite3.Connection) -> None:
    """ساخت جدول units + seed واحدهای پیش‌فرض"""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        )
        """
    )
    # seed پیش‌فرض
    try:
        count = conn.execute('SELECT COUNT(*) FROM units').fetchone()[0]
        if count == 0:
            now = '2026-08-05 00:00:00'
            for u in DEFAULT_UNITS:
                if isinstance(u, tuple):
                    name, code, desc = u
                else:
                    name, code, desc = u, None, None
                try:
                    conn.execute(
                        'INSERT INTO units (name, code, description, is_active, created_at) '
                        'VALUES (?, ?, ?, 1, ?)',
                        (name, code, desc, now),
                    )
                except sqlite3.IntegrityError:
                    pass
            conn.commit()
    except Exception:
        pass


def list_units(conn: sqlite3.Connection, active_only: bool = True) -> List[Dict[str, Any]]:
    ensure_units_table(conn)
    if active_only:
        rows = conn.execute(
            'SELECT id, name, code, description, is_active FROM units WHERE is_active = 1 ORDER BY id'
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT id, name, code, description, is_active FROM units ORDER BY id'
        ).fetchall()
    return [
        {'id': r[0], 'name': r[1], 'code': r[2], 'description': r[3], 'is_active': r[4]}
        for r in rows
    ]


def add_unit(conn: sqlite3.Connection, name: str, code: str = None,
             description: str = None) -> int:
    ensure_units_table(conn)
    try:
        cur = conn.execute(
            'INSERT INTO units (name, code, description, is_active, created_at) '
            'VALUES (?, ?, ?, 1, ?)',
            (name, code, description, '2026-08-05 00:00:00'),
        )
        conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        # واحد تکراری → فعالش کن
        conn.execute('UPDATE units SET is_active = 1 WHERE name = ?', (name,))
        conn.commit()
        row = conn.execute('SELECT id FROM units WHERE name = ?', (name,)).fetchone()
        return int(row[0]) if row else 0


def update_unit(conn: sqlite3.Connection, unit_id: int, name: str = None,
                code: str = None, description: str = None, is_active: int = None) -> None:
    ensure_units_table(conn)
    sets, params = [], []
    if name is not None:
        sets.append('name = ?'); params.append(name)
    if code is not None:
        sets.append('code = ?'); params.append(code)
    if description is not None:
        sets.append('description = ?'); params.append(description)
    if is_active is not None:
        sets.append('is_active = ?'); params.append(int(is_active))
    if not sets:
        return
    params.append(unit_id)
    conn.execute('UPDATE units SET {} WHERE id = ?'.format(', '.join(sets)), params)
    conn.commit()


def delete_unit(conn: sqlite3.Connection, unit_id: int) -> None:
    """غیرفعال کردن واحد (حذف فیزیکی نمی‌کنیم تا تاریخچه حفظ شود)"""
    ensure_units_table(conn)
    conn.execute('UPDATE units SET is_active = 0 WHERE id = ?', (unit_id,))
    conn.commit()
