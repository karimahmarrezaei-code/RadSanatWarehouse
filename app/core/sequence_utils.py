# -*- coding: utf-8 -*-
"""
sequence_utils.py - شماره‌گذاری سریالی سالانه (هسته فاز ۲)

قوانین:
  - شروع سال مالی: اول فروردین هر سال
  - سریالی: هر روز از جایی که دیروز تمام شده ادامه می‌یابد
  - ریست: اول فروردین، همه شمارنده‌ها از 0001
  - فرمت: {نوع}-{سال}-{دنباله ۴ رقمی}  (مثل RC-1405-0001)

استفاده:
  from app.core.sequence_utils import next_sequence_no

  next_sequence_no(conn, 'RC', jalali_year=1405)  → 'RC-1405-0001'
"""

import jdatetime
import time
import sqlite3
from typing import Optional


def current_jalali_year() -> int:
    """سال جاری شمسی (برای شروع سال مالی از اول فروردین)"""
    return jdatetime.date.today().year


def _jalali_year_of_date(iso_date: Optional[str]) -> int:
    """سال شمسی مربوط به یک تاریخ میلادی (yyyy-mm-dd)"""
    if not iso_date:
        return current_jalali_year()
    try:
        parts = str(iso_date).strip().split(' ')[0].split('-')
        if len(parts) == 3:
            g = jdatetime.date.fromgregorian(
                year=int(parts[0]), month=int(parts[1]), day=int(parts[2]))
            return g.year
    except Exception:
        pass
    return current_jalali_year()




def _exec_with_retry(connection, sql, params=(), tries=6, wait=0.3):
    """اجرای کوئری با چند بار تلاش هنگام قفل بودن دیتابیس (database is locked).

    busy_timeout را کوتاه می‌کند تا هر تلاش سریع خطا بدهد و retry سریع
    بچرخد؛ حداکثر انتظار ≈ tries × (busy + wait) ≈ چند ثانیه.
    """
    try:
        connection.execute('PRAGMA busy_timeout = 1200;')
    except Exception:
        pass
    last = None
    for attempt in range(tries):
        try:
            return connection.execute(sql, params)
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if 'locked' not in msg and 'busy' not in msg:
                raise
            last = e
            time.sleep(wait)
    raise last


def next_sequence_no(
    connection: sqlite3.Connection,
    doc_type: str,
    width: int = 4,
    iso_date: Optional[str] = None,
    personnel_id: Optional[int] = None,
) -> str:
    """تولید شماره سریالی سالانه.

    Args:
        connection: اتصال دیتابیس (با row_factory فعال)
        doc_type: نوع سند (مثل 'RC', 'IS', 'FN', 'PR', 'EX')
        width: تعداد رقم دنباله (پیش‌فرض 4)
        iso_date: تاریخ میلادی سند (برای تشخیص سال شمسی)

    Returns:
        رشته شماره، مثل 'RC-1405-0001'
    """
    year = _jalali_year_of_date(iso_date)
    if personnel_id is not None:
        seq_name = f"{doc_type}-{year}-{int(personnel_id):03d}"
        prefix = f"{doc_type}-{year}-{int(personnel_id):03d}-"
    else:
        seq_name = f"{doc_type}-{year}"
        prefix = f"{doc_type}-{year}-"

    # خواندن مقدار فعلی
    row = connection.execute(
        'SELECT current_value, width FROM sequences WHERE name = ?',
        (seq_name,),
    ).fetchone()
    if row:
        current = int(row[0])
        w = int(row[1] or width)
    else:
        current = 0
        w = width
        # ساخت رکورد جدید (شروع سال مالی جدید → از 0001)
        try:
            _exec_with_retry(
                connection,
                'INSERT INTO sequences (name, prefix, current_value, width, updated_at) '
                'VALUES (?, ?, 0, ?, ?)',
                (seq_name, prefix, w, '2026-01-01 00:00:00'),
            )
        except Exception:
            # رقابت هم‌زمان — دوباره بخوان
            row2 = connection.execute(
                'SELECT current_value, width FROM sequences WHERE name = ?',
                (seq_name,),
            ).fetchone()
            if row2:
                current = int(row2[0])
                w = int(row2[1] or width)

    next_value = current + 1
    _exec_with_retry(
        connection,
        'UPDATE sequences SET current_value = ?, prefix = ?, updated_at = ? WHERE name = ?',
        (next_value, prefix, '2026-01-01 00:00:00', seq_name),
    )

    return f"{prefix}{next_value:0{w}d}"


def peek_sequence_no(
    connection: sqlite3.Connection,
    doc_type: str,
    width: int = 4,
    iso_date: Optional[str] = None,
    personnel_id: Optional[int] = None,
) -> str:
    """مقدار شماره بعدی را برمی‌گرداند بدون اینکه جلو ببرد (برای نمایش لیبل).

    این تابع برای پیش‌نمایش شماره در فرم استفاده می‌شود تا شماره واقعی
    فقط هنگام ثبت (با next_sequence_no) جلو برود.
    """
    year = _jalali_year_of_date(iso_date)
    if personnel_id is not None:
        seq_name = f"{doc_type}-{year}-{int(personnel_id):03d}"
        prefix = f"{doc_type}-{year}-{int(personnel_id):03d}-"
    else:
        seq_name = f"{doc_type}-{year}"
        prefix = f"{doc_type}-{year}-"

    row = connection.execute(
        'SELECT current_value, width FROM sequences WHERE name = ?',
        (seq_name,),
    ).fetchone()
    if row:
        current = int(row[0])
        w = int(row[1] or width)
    else:
        current = 0
        w = width

    next_value = current + 1
    return f"{prefix}{next_value:0{w}d}"


def reset_sequence(connection: sqlite3.Connection, doc_type: str, year: Optional[int] = None) -> None:
    """ریست شمارنده برای یک نوع در یک سال (برای تست/تعمیر)"""
    y = year or current_jalali_year()
    seq_name = f"{doc_type}-{y}"
    connection.execute(
        'UPDATE sequences SET current_value = 0 WHERE name = ?',
        (seq_name,),
    )
