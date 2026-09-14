# -*- coding: utf-8 -*-
"""حذف نگهبان ref_no + ماندهٔ واقعی + نرمال‌سازی مسیر خروج - اجرا: python fix_rescue.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) حذف کامل نگهبان‌های ref_no (بازگشت به کد اصلی)
p = os.path.join(ROOT, 'app', 'repositories', 'issue_repository.py')
s = open(p, encoding='utf-8').read()
for bad in (
    "_base_ref = NumberingService.next('LOAD_OUT', conn, iso_date=operation_date)  # REF-SAFE\n"
    "            ref_no = _base_ref  # REF-SAFE\n"
    "            _k = 2  # REF-SAFE\n"
    "            while conn.execute(\"SELECT 1 FROM outbound_loads WHERE reference_no = ?\", (ref_no,)).fetchone():  # REF-SAFE\n"
    "                ref_no = f\"{_base_ref}-{_k}\"  # REF-SAFE\n"
    "                _k += 1  # REF-SAFE\n",
    "ref_no = NumberingService.next('LOAD_OUT', conn, iso_date=operation_date)\n"
    "            _k = 2  # REF-RETRY\n"
    "            while conn.execute(\"SELECT 1 FROM outbound_loads WHERE reference_no = ?\", (ref_no,)).fetchone():  # REF-RETRY\n"
    "                ref_no = f\"{ref_no}-{_k}\"  # REF-RETRY\n"
    "                _k += 1  # REF-RETRY\n"):
    s = s.replace(bad, "ref_no = NumberingService.next('LOAD_OUT', conn, iso_date=operation_date)\n")
open(p, 'w', encoding='utf-8').write(s); py_compile.compile(p, doraise=True)
print('1) issue_repository به کد اصلی برگشت ✔')

p = os.path.join(ROOT, 'app', 'ui', 'proforma_window.py')
s = open(p, encoding='utf-8').read()
for bad in (
    '_base_ref = f"EX-{_jy}-" + str(proforma_id).zfill(4)  # REF-SAFE\n'
    '                ref_no = _base_ref  # REF-SAFE\n'
    '                _k = 2  # REF-SAFE\n'
    '                while conn.execute("SELECT 1 FROM outbound_loads WHERE reference_no = ?", (ref_no,)).fetchone():  # REF-SAFE\n'
    '                    ref_no = f"{_base_ref}-{_k}"  # REF-SAFE\n'
    '                    _k += 1  # REF-SAFE\n',
    'ref_no = f"EX-{_jy}-" + str(proforma_id).zfill(4)\n'
    '                _k = 2  # REF-RETRY\n'
    '                while conn.execute("SELECT 1 FROM outbound_loads WHERE reference_no = ?", (ref_no,)).fetchone():  # REF-RETRY\n'
    '                    ref_no = f"{ref_no}-{_k}"  # REF-RETRY\n'
    '                    _k += 1  # REF-RETRY\n'):
    s = s.replace(bad, 'ref_no = f"EX-{_jy}-" + str(proforma_id).zfill(4)\n')
open(p, 'w', encoding='utf-8').write(s); py_compile.compile(p, doraise=True)
print('1) proforma_window به کد اصلی برگشت ✔')

# 2) PN2: نرمال‌سازی + کسر رزروها در مسیر خروج
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
if '# PN2' not in s:
    anchor = '                        self._load_pallets = _lp_wrap  # PALLET-NORM\n'
    block = (
        "                try:  # PN2\n"
        "                    if callable(getattr(self, '_pallet_options', None)) and not getattr(self, '_pn2', False):  # PN2\n"
        "                        self._pn2 = True  # PN2\n"
        "                        _orig_po = self._pallet_options  # PN2\n"
        "                        def _po_wrap(*a, _o=_orig_po, _w=self, **k):  # PN2\n"
        "                            res = _o(*a, **k)  # PN2\n"
        "                            try:  # PN2\n"
        "                                import re as _r5  # PN2\n"
        "                                reserved = {}  # PN2\n"
        "                                with _w.db.connect() as _cn5:  # PN2\n"
        "                                    _cn5.row_factory = None  # PN2\n"
        "                                    for _pid5, _q5 in _cn5.execute(\"SELECT oli.pallet_id, SUM(oli.qty) FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id = oli.outbound_load_id WHERE ol.load_status = 'OPEN' AND ol.is_active = 1 GROUP BY oli.pallet_id\").fetchall():  # PN2\n"
        "                                        reserved[_pid5] = int(_q5 or 0)  # PN2\n"
        "                                out = []  # PN2\n"
        "                                for it in res:  # PN2\n"
        "                                    if isinstance(it, tuple) and it and isinstance(it[0], dict):  # PN2\n"
        "                                        d = it[0]; c = str(d.get('code', '')); nn = str(d.get('name', ''))  # PN2\n"
        "                                        if _r5.match(r'^\\d+(-\\d+)+$', c):  # PN2\n"
        "                                            m2 = _r5.search(r'[A-Za-z]{2,}-\\d+', nn)  # PN2\n"
        "                                            if m2:  # PN2\n"
        "                                                d['code'] = m2.group(0); d['name'] = nn.replace(m2.group(0), '').strip(' |-,')  # PN2\n"
        "                                        s5 = (it[1] or 0) - reserved.get(d.get('id'), 0)  # PN2\n"
        "                                        out.append((d, s5) + tuple(it[2:]))  # PN2\n"
        "                                    else:  # PN2\n"
        "                                        out.append(it)  # PN2\n"
        "                                ps5 = getattr(_w, 'pallet_stock', None)  # PN2\n"
        "                                if isinstance(ps5, dict):  # PN2\n"
        "                                    for _k5 in list(ps5.keys()):  # PN2\n"
        "                                        ps5[_k5] = (ps5[_k5] or 0) - reserved.get(_k5, 0)  # PN2\n"
        "                                return out  # PN2\n"
        "                            except Exception:  # PN2\n"
        "                                return res  # PN2\n"
        "                        self._pallet_options = _po_wrap  # PN2\n"
        "                except Exception:  # PN2\n"
        "                    pass  # PN2\n"
    )
    if anchor in s:
        s = s.replace(anchor, anchor + block, 1)
    # 3) تأخیر رنگِ مجدد پیش‌نمایش
    s = s.replace('singleShot(500,', 'singleShot(1200,')
    open(mp, 'w', encoding='utf-8').write(s)
    py_compile.compile(mp, doraise=True)
    print('2) PN2 + تأخیر پیش‌نمایش ✔')
else:
    print('2) از قبل بود ✔')

# 4) بیلد با محافظ داده
db_dist = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db_dist):
    shutil.copy2(db_dist, keep)
print('3) بیلد...')
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
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')