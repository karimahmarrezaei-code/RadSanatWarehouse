# -*- coding: utf-8 -*-
import os

def find_db():
    base = os.path.dirname(os.path.abspath(__file__))
    for b in (base, os.path.dirname(base)):
        for p in (os.path.join(b, '_internal', 'data', 'app.db'),
                  os.path.join(b, 'data', 'app.db')):
            if os.path.exists(p):
                return p
    return None

"""پرکردن cash_accounts از treasury_accounts - لپ‌تاپ"""
import re, sqlite3

dbp = find_db()
print('دیتابیس:', dbp)
c = sqlite3.connect(dbp)
cols = [r[1] for r in c.execute("PRAGMA table_info(cash_accounts)")]
create_sql = c.execute("SELECT sql FROM sqlite_master WHERE name='cash_accounts'").fetchone()[0]
m = re.search(r"IN\s*\(([^)]*)\)", create_sql)
vals = [v.strip().strip("'\"") for v in m.group(1).split(',')] if m else ['CASH', 'BANK']
cash_type = 'CASH' if 'CASH' in vals else vals[0]
bank_type = 'BANK' if 'BANK' in vals else (vals[1] if len(vals) > 1 else vals[0])
before = c.execute("SELECT COUNT(*) FROM cash_accounts").fetchone()[0]
for name, atype, bal in c.execute(
        "SELECT name, account_type, current_balance FROM treasury_accounts WHERE is_active=1"):
    t = cash_type if atype == 'CASHBOX' else bank_type
    if c.execute("SELECT 1 FROM cash_accounts WHERE name=?", (name,)).fetchone():
        c.execute("UPDATE cash_accounts SET is_active=1 WHERE name=?", (name,))
        continue
    names, vals2 = [], []
    for col in cols:
        if col == 'name':
            names.append(col); vals2.append(name)
        elif col == 'type':
            names.append(col); vals2.append(t)
        elif col == 'balance':
            names.append(col); vals2.append(int(bal or 0))
        elif col == 'is_active':
            names.append(col); vals2.append(1)
    c.execute("INSERT INTO cash_accounts ({}) VALUES ({})".format(
        ','.join(names), ','.join('?' * len(names))), vals2)
    print('✔ +', name, t)
c.commit()
print('✔ cash_accounts: قبل {} → بعد {}'.format(
    before, c.execute("SELECT COUNT(*) FROM cash_accounts").fetchone()[0]))
c.close()
input('Enter...')
