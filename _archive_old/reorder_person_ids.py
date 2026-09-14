# -*- coding: utf-8 -*-
"""
reorder_person_ids.py - بازنویسی ID اشخاص از ۱ (مرتب)

ID های فعلی: 1,2,5,6,7,8 (شماره‌های 3,4,9,... خالی‌اند)
این اسکریپت:
  ۱) پشتیبان می‌گیرد
  ۲) همه ستون‌های خارجی (FK) که به persons.id اشاره می‌کنند را پیدا می‌کند
  ۳) به هر پرسنل (به ترتیب id) یک id جدید از ۱ می‌دهد
  ۴) همه ارجاع‌ها را به‌روز می‌کند
  ۵) id ها را بازنویسی می‌کند
  ۶) شمارنده AUTOINCREMENT را درست می‌کند

اجرا (از F:\\warehouse_app — برنامه بسته باشد):
    py -X utf8 .\\reorder_person_ids.py            (گزارش فقط)
    py -X utf8 .\\reorder_person_ids.py APPLY      (اعمال)
"""
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

DB_CANDIDATES = ['data/app.db', 'app.db', 'data/appdb', 'appdb']


def main():
    apply = 'APPLY' in sys.argv
    db_path = next((c for c in DB_CANDIDATES if os.path.exists(c)), None)
    if not db_path:
        print('دیتابیس پیدا نشد')
        return

    print('دیتابیس:', db_path)
    print('حالت:', 'APPLY (اعمال)' if apply else 'DRY (گزارش)')
    print()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # ۱) لیست پرسنل فعلی
    persons = conn.execute('SELECT id, first_name, last_name FROM persons ORDER BY id').fetchall()
    print('=== پرسنل فعلی ({}) ==='.format(len(persons)))
    for p in persons:
        print('  id={} | {} {}'.format(p['id'], p['first_name'] or '', p['last_name'] or ''))

    # ۲) پیدا کردن همه ستون‌های FK به persons
    print()
    print('=== ستون‌های ارجاع‌دهنده به persons.id ===')
    fk_columns = []  # [(table, column)]
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for t in tables:
        try:
            cols = conn.execute('PRAGMA foreign_key_list({})'.format(t)).fetchall()
            for fk in cols:
                if fk['table'] == 'persons':
                    fk_columns.append((t, fk['from']))
                    print('  {} . {} → persons.id'.format(t, fk['from']))
        except Exception:
            pass

    # ۳) نقشه id قدیمی → id جدید
    mapping = {}
    new_id = 1
    for p in persons:
        mapping[p['id']] = new_id
        new_id += 1

    print()
    print('=== نقشه بازنویسی ===')
    for old, new in mapping.items():
        print('  {} → {}'.format(old, new))

    if not apply:
        print()
        print('حالت DRY — هیچ تغییری نشد.')
        print('برای اعمال: py -X utf8 .\\reorder_person_ids.py APPLY')
        conn.close()
        return

    # ۴) پشتیبان
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    bak = '{}.reorderid_{}.db'.format(db_path, stamp)
    shutil.copy2(db_path, bak)
    print()
    print('✅ پشتیبان:', bak)

    conn.execute('PRAGMA foreign_keys = OFF;')
    conn.execute('BEGIN;')

    # ۵) به‌روزرسانی همه ارجاع‌ها
    for table, col in fk_columns:
        for old, new in mapping.items():
            try:
                conn.execute(
                    'UPDATE {} SET {} = ? WHERE {} = ?'.format(table, col, col),
                    (new, old))
            except Exception as e:
                print('  ⚠️ {}: {}'.format(table, str(e)[:50]))

    # ۶) بازنویسی id اشخاص
    for old, new in mapping.items():
        conn.execute('UPDATE persons SET id = ? WHERE id = ?', (new, old))

    # ۷) درست کردن AUTOINCREMENT
    try:
        conn.execute('DELETE FROM sqlite_sequence WHERE name = ?', ('persons',))
        conn.execute('INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)', ('persons', len(persons)))
        print('  ✅ sqlite_sequence برای persons = {}'.format(len(persons)))
    except Exception as e:
        print('  ⚠️ sqlite_sequence:', str(e)[:50])

    conn.execute('COMMIT;')
    conn.execute('PRAGMA foreign_keys = ON;')

    # ۸) بررسی نهایی
    print()
    print('=== پرسنل بعد از بازنویسی ===')
    for p in conn.execute('SELECT id, first_name, last_name FROM persons ORDER BY id'):
        print('  id={} | {} {}'.format(p['id'], p['first_name'] or '', p['last_name'] or ''))

    print()
    print('✅ بازنویسی انجام شد!')
    conn.close()


if __name__ == '__main__':
    main()
