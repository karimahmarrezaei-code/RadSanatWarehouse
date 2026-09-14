# -*- coding: utf-8 -*-
"""پاکسازی داده + نرمال‌سازی نمایش پالت - اجرا: python fix_pallet_final.py"""
import os, re, sys, subprocess, shutil, py_compile, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) پاکسازی همهٔ دیتابیس‌ها
for db in (os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db'),
           os.path.join(ROOT, 'last_app.db'),
           os.path.join(ROOT, 'data', 'app.db')):
    if not os.path.exists(db):
        continue
    con = sqlite3.connect(db)
    try:
        for pid, code, name in con.execute("SELECT id, code, name FROM pallets").fetchall():
            c, n = (code or '').strip(), (name or '').strip()
            nc, nn = c, n
            m = re.match(r'^(\d+(?:-\d+)+)\s*(.*)$', nn)
            if m:
                nn = m.group(2).strip()
            if re.match(r'^\d+(?:-\d+)+$', nc):
                t = re.search(r'[A-Za-z]{2,}-\d+', nn)
                if t:
                    nc = t.group(0)
                    nn = nn.replace(t.group(0), '').strip(' |-,')
            if (nc, nn) != (c, n):
                con.execute("UPDATE pallets SET code=?, name=? WHERE id=?", (nc, nn, pid))
                print('اصلاح:', db.split(os.sep)[-2], (c, n), '->', (nc, nn))
        con.commit()
    finally:
        con.close()
print('1) پاکسازی داده ✔')

# 2) نمایش کدِ تبِ افزودن پالت (برای اصلاح دائمیِ بعدی)
for rel in ('app/ui/receipt_manager_window.py', 'app/ui/issue_manager_window.py'):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    lines = open(p, encoding='utf-8', errors='replace').read().split('\n')
    print('=' * 20, rel)
    n = 0
    for i, l in enumerate(lines):
        if 'create_pallet' in l:
            for j in range(max(0, i - 6), min(len(lines), i + 6)):
                print(f'{j+1:5} {lines[j].rstrip()}')
            print('-' * 40)
            n += 1
            if n > 2:
                break

# 3) نرمال‌سازی زمان بارگذاری در main.py
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# PALLET-NORM' not in s:
    anchor = '                _compact(self)  # COMPACT-UI\n'
    block = (
        "                try:  # PALLET-NORM\n"
        "                    if callable(getattr(self, '_load_pallets', None)) and not getattr(self, '_pn', False):  # PALLET-NORM\n"
        "                        self._pn = True  # PALLET-NORM\n"
        "                        _orig_lp = self._load_pallets  # PALLET-NORM\n"
        "                        def _lp_wrap(*a, _o=_orig_lp, _w=self, **k):  # PALLET-NORM\n"
        "                            _o(*a, **k)  # PALLET-NORM\n"
        "                            try:  # PALLET-NORM\n"
        "                                import re as _r4  # PALLET-NORM\n"
        "                                for it in getattr(_w, 'pallets', []):  # PALLET-NORM\n"
        "                                    d = it[0] if isinstance(it, tuple) and it and isinstance(it[0], dict) else (it if isinstance(it, dict) else None)  # PALLET-NORM\n"
        "                                    if d is None:  # PALLET-NORM\n"
        "                                        continue  # PALLET-NORM\n"
        "                                    c = str(d.get('code', '')); nn = str(d.get('name', ''))  # PALLET-NORM\n"
        "                                    if _r4.match(r'^\\d+(-\\d+)+$', c):  # PALLET-NORM\n"
        "                                        m2 = _r4.search(r'[A-Za-z]{2,}-\\d+', nn)  # PALLET-NORM\n"
        "                                        if m2:  # PALLET-NORM\n"
        "                                            d['code'] = m2.group(0); d['name'] = nn.replace(m2.group(0), '').strip(' |-,')  # PALLET-NORM\n"
        "                            except Exception:  # PALLET-NORM\n"
        "                                pass  # PALLET-NORM\n"
        "                        self._load_pallets = _lp_wrap  # PALLET-NORM\n"
        "                except Exception:  # PALLET-NORM\n"
        "                    pass  # PALLET-NORM\n"
    )
    if anchor in s:
        s = s.replace(anchor, block + anchor, 1)
        open(mp, 'w', encoding='utf-8').write(s)
        py_compile.compile(mp, doraise=True)
        print('3) PALLET-NORM نصب شد ✔')
else:
    print('3) از قبل بود ✔')

# 4) بیلد با محافظ داده
db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
print('4) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('❌ بیلد ناموفق'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql', '.py')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
good = os.path.join(ROOT, 'theme_manager.py')
if os.path.exists(good):
    for tgt in (os.path.join(DST, 'theme_manager.py'),
                os.path.join(DST, '_internal', 'theme_manager.py'),
                os.path.join(DST, '_internal', 'app', 'styles', 'theme_manager.py')):
        if os.path.isdir(os.path.dirname(tgt)):
            shutil.copy2(good, tgt)
if os.path.exists(keep):
    os.makedirs(os.path.join(DST, '_internal', 'data'), exist_ok=True)
    shutil.copy2(keep, db_dist)
    print('4) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('5) تمام ✔')
input('Enter...')