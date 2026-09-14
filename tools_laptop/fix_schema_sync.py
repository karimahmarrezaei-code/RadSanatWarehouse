# -*- coding: utf-8 -*-
"""همگام‌سازی ستون‌های جامانده با schema.sql - لپ‌تاپ"""
import os, re, sqlite3

def find_data():
    base = os.path.dirname(os.path.abspath(__file__))
    for b in (base, os.path.dirname(base)):
        for p in (os.path.join(b, '_internal', 'data'), os.path.join(b, 'data')):
            if os.path.isdir(p):
                return p
    return None

d = find_data()
sp = os.path.join(d, 'schema.sql')
dbp = os.path.join(d, 'app.db')
print('schema:', sp)
print('db:', dbp)
sql = open(sp, encoding='utf-8', errors='replace').read()

# استخراج بلوک‌های CREATE TABLE با پرانتزِ متوازن
tables = {}
for m in re.finditer(r'CREATE TABLE (?:IF NOT EXISTS )?"?(\w+)"?\s*\(', sql, re.I):
    name = m.group(1)
    i = m.end() - 1
    depth, j = 0, i
    while j < len(sql):
        if sql[j] == '(':
            depth += 1
        elif sql[j] == ')':
            depth -= 1
            if depth == 0:
                break
        j += 1
    tables[name] = sql[i + 1:j]

SKIP = ('PRIMARY', 'FOREIGN', 'UNIQUE', 'CHECK', 'CONSTRAINT')
c = sqlite3.connect(dbp)
added = 0
for tname, body in tables.items():
    if not c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (tname,)).fetchone()[0]:
        continue
    have = set(r[1] for r in c.execute('PRAGMA table_info({})'.format(tname)))
    # شکستن به ستون‌ها با عمقِ پرانتز
    parts, buf, depth = [], '', 0
    for ch in body:
        if ch == '(':
            depth += 1; buf += ch
        elif ch == ')':
            depth -= 1; buf += ch
        elif ch == ',' and depth == 0:
            parts.append(buf.strip()); buf = ''
        else:
            buf += ch
    if buf.strip():
        parts.append(buf.strip())
    for coldef in parts:
        mm = re.match(r'^"?(\w+)"?\s+([A-Za-z]+)', coldef)
        if not mm:
            continue
        cname, ctype = mm.group(1), mm.group(2).upper()
        if cname.upper() in SKIP or cname in have:
            continue
        dm = re.search(r"DEFAULT\s+(-?\d+(?:\.\d+)?|'[^']*'|\"[^\"]*\"|NULL|CURRENT_TIMESTAMP)", coldef, re.I)
        stmt = 'ALTER TABLE {} ADD COLUMN {} {}'.format(tname, cname, ctype)
        if dm:
            stmt += ' DEFAULT ' + dm.group(1)
        try:
            c.execute(stmt)
            added += 1
            print('✔ +{}.{}'.format(tname, cname))
        except Exception as e:
            print('⚠ {}.{} : {}'.format(tname, cname, str(e)[:60]))
c.commit()
c.close()
print('✔ مجموع ستون‌های افزوده:', added)
input('Enter...')