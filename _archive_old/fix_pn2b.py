# -*- coding: utf-8 -*-
"""PN2 به‌صورت تابع ماژولی + یک خط صدا - اجرا: python fix_pn2b.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

# 1) حذف بلوک خراب PN2
i = s.find('                try:  # PN2\n')
j = s.find('                    pass  # PN2\n')
if i != -1 and j != -1:
    j += len('                    pass  # PN2\n')
    s = s[:i] + s[j:]
    print('1) بلوک خراب حذف شد')

# 2) تابع ماژولی PN2B
if '# PN2B' not in s:
    func = (
        "def _pn2_attach(win):  # PN2B\n"
        "    try:  # PN2B\n"
        "        if not callable(getattr(win, '_pallet_options', None)) or getattr(win, '_pn2', False):  # PN2B\n"
        "            return  # PN2B\n"
        "        win._pn2 = True  # PN2B\n"
        "        orig = win._pallet_options  # PN2B\n"
        "        def wrap(*a, **k):  # PN2B\n"
        "            res = orig(*a, **k)  # PN2B\n"
        "            try:  # PN2B\n"
        "                import re as _r5  # PN2B\n"
        "                reserved = {}  # PN2B\n"
        "                with win.db.connect() as cn:  # PN2B\n"
        "                    cn.row_factory = None  # PN2B\n"
        "                    for pid, q in cn.execute(\"SELECT oli.pallet_id, SUM(oli.qty) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id WHERE ol.load_status='OPEN' AND ol.is_active=1 GROUP BY oli.pallet_id\").fetchall():  # PN2B\n"
        "                        reserved[pid] = int(q or 0)  # PN2B\n"
        "                out = []  # PN2B\n"
        "                for it in res:  # PN2B\n"
        "                    if isinstance(it, tuple) and it and isinstance(it[0], dict):  # PN2B\n"
        "                        d = it[0]; c = str(d.get('code', '')); nn = str(d.get('name', ''))  # PN2B\n"
        "                        if _r5.match(r'^\\d+(-\\d+)+$', c):  # PN2B\n"
        "                            m2 = _r5.search(r'[A-Za-z]{2,}-\\d+', nn)  # PN2B\n"
        "                            if m2:  # PN2B\n"
        "                                d['code'] = m2.group(0); d['name'] = nn.replace(m2.group(0), '').strip(' |-,')  # PN2B\n"
        "                        out.append((d, (it[1] or 0) - reserved.get(d.get('id'), 0)) + tuple(it[2:]))  # PN2B\n"
        "                    else:  # PN2B\n"
        "                        out.append(it)  # PN2B\n"
        "                ps = getattr(win, 'pallet_stock', None)  # PN2B\n"
        "                if isinstance(ps, dict):  # PN2B\n"
        "                    for kk in list(ps.keys()):  # PN2B\n"
        "                        ps[kk] = (ps[kk] or 0) - reserved.get(kk, 0)  # PN2B\n"
        "                return out  # PN2B\n"
        "            except Exception:  # PN2B\n"
        "                return res  # PN2B\n"
        "        win._pallet_options = wrap  # PN2B\n"
        "    except Exception:  # PN2B\n"
        "        pass  # PN2B\n"
        "\n"
    )
    anchor = 'from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox\n'
    if anchor in s:
        s = s.replace(anchor, func + anchor, 1)
        print('2) تابع PN2B اضافه شد')

# 3) یک خط صدا در _safe_show
if '# PN2B-CALL' not in s:
    anchor2 = '                    pass  # PALLET-NORM\n'
    if anchor2 in s:
        s = s.replace(anchor2, anchor2 + '                _pn2_attach(self)  # PN2B-CALL\n', 1)
        print('3) خط صدا اضافه شد')

open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)
print('4) main.py سالم است ✔')

db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
print('5) بیلد...')
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
    print('5) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('6) تمام ✔')
input('Enter...')