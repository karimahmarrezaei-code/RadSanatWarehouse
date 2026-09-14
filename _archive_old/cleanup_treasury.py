# -*- coding: utf-8 -*-
import sqlite3, os, glob
BASE = os.path.dirname(os.path.abspath(__file__))

path = None
try:
    from app.core.database import DatabaseManager
    path = getattr(DatabaseManager(), 'db_path', None)
except Exception:
    pass
if not path or not os.path.exists(path):
    best, bestn = None, -1
    for c in glob.glob(os.path.join(BASE, '**', '*.db'), recursive=True):
        try:
            n = len(sqlite3.connect(c).execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
        except Exception:
            n = 0
        if n > bestn: bestn, best = n, c
    path = best
print('دیتابیس:', path)

conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row
tables = [r['name'] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]

# پیدا کردن جدولی که هم code و هم ستون موجودی دارد
tab = None
for t in tables:
    cols = [c['name'] for c in conn.execute(f"PRAGMA table_info({t})")]
    if 'code' in cols and any('balance' in c for c in cols):
        tab = t; break
if not tab:
    print('جدول مناسب پیدا نشد. جدول‌ها:', tables); conn.close(); raise SystemExit
print('جدول:', tab)

# ۱) حذف پیش‌فرض‌های تکراری
for code in ['TR-0001', 'TR-0002']:
    row = conn.execute(f"SELECT id FROM {tab} WHERE code=?", (code,)).fetchone()
    if not row:
        continue
    aid = row['id']
    used = False
    for tt in tables:
        c2 = [c['name'] for c in conn.execute(f"PRAGMA table_info({tt})")]
        acol = next((c for c in ['treasury_account_id','account_id','to_account_id','from_account_id'] if c in c2), None)
        if acol and tt != tab and conn.execute(f"SELECT 1 FROM {tt} WHERE {acol}=? LIMIT 1", (aid,)).fetchone():
            used = True; break
    if used:
        conn.execute(f"UPDATE {tab} SET is_active=0 WHERE id=?", (aid,))
        print(f'  – {code}: گردش دارد؛ غیرفعال شد.')
    else:
        conn.execute(f"DELETE FROM {tab} WHERE id=?", (aid,))
        print(f'  ✔ {code}: حذف شد.')

# ۲) فعال‌سازی صندوق اصلی
conn.execute(f"UPDATE {tab} SET is_active=1 WHERE code='CA-00001'")
print('  ✔ CA-00001 فعال شد.')

conn.commit()
print('\nفهرست نهایی:')
for r in conn.execute(f"SELECT code, name, is_active FROM {tab} ORDER BY code"):
    print(f"  {r['code']} | {r['name']} | {'فعال' if r['is_active'] else 'غیرفعال'}")
conn.close()
print('پاک‌سازی کامل شد.')