# -*- coding: utf-8 -*-
import sqlite3, os, glob
BASE = os.path.dirname(os.path.abspath(__file__))

# 👇 مبالغ واقعی هر حساب را اینجا وارد کنید (به ریال)
# اگر حسابی را نگذارید، تغییر نمی‌کند
OPENING = {
    'TR-0001': 50000000,            # بانک
    'TR-0002': 1000000000,            # بانک
    'CA-00001': 1500000000,           # صندوق ۱
    'CA-00002': 500000000,
    'CA-00003': 0,
    'CA-00004': 2000000000,
    'CA-00005': 1500000000,
    'CA-00006': 500000000,
    'CA-00007': 1000000000,
    'CA-00008': 2500000000,           # بانک شهر
    'CA-00009': 1000000000,
}

# پیدا کردن DB واقعی
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
tab = next((t for t in ['treasury_accounts','cash_accounts','finance_treasury_accounts'] if t in tables), None)
if not tab:
    tab = next((t for t in tables if 'treasury' in t.lower() or 'cash' in t.lower() or 'account' in t.lower()), None)
print('جدول:', tab)

cols = [r['name'] for r in conn.execute(f"PRAGMA table_info({tab})")]
code_col = 'code' if 'code' in cols else 'account_code'
init_col = next((c for c in ['initial_balance','opening_balance'] if c in cols), None)
cur_col  = next((c for c in ['current_balance','balance'] if c in cols), None)

print('\n=== وضعیت فعلی ===')
for r in conn.execute(f"SELECT * FROM {tab} ORDER BY {code_col}"):
    d = dict(r)
    print(f"  {d.get(code_col)} | موجودی فعلی: {d.get(cur_col, 0):,} ریال")

print('\n=== اعمال افتتاحیه ===')
for code, amount in OPENING.items():
    cur = conn.execute(
        f"UPDATE {tab} SET {init_col}=?, {cur_col}=? WHERE {code_col}=?",
        (int(amount), int(amount), code))
    if cur.rowcount:
        print(f"  ✔ {code}: {int(amount):,} ریال")
    else:
        print(f"  – {code}: یافت نشد")

conn.commit()

print('\n=== وضعیت نهایی ===')
for r in conn.execute(f"SELECT * FROM {tab} ORDER BY {code_col}"):
    d = dict(r)
    print(f"  {d.get(code_col)} | اولیه: {d.get(init_col, 0):,} | فعلی: {d.get(cur_col, 0):,}")
conn.close()
print('\n✅ افتتاحیه کامل شد.')