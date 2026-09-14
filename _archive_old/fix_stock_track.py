# -*- coding: utf-8 -*-
"""پاکسازی نام پالت + تعقیب رزروها در موجودی - اجرا: python fix_stock_track.py"""
import os, re, sys, subprocess, shutil, py_compile, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) پاکسازی داده: پیشوند ابعاد از نام بیرون، کد/نام جابه‌جا اگر لازم
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
                nn = m.group(2).strip(' |-,')
            if re.match(r'^\d+(?:-\d+)+$', nc):
                t = re.search(r'[A-Za-z]{2,}-\d+', nn)
                if t:
                    nc = t.group(0)
                    nn = nn.replace(t.group(0), '').strip(' |-,')
            if (nc, nn) != (c, n):
                con.execute("UPDATE pallets SET code=?, name=? WHERE id=?", (nc, nn, pid))
                print('اصلاح:', (c, n), '->', (nc, nn))
        con.commit()
    finally:
        con.close()
print('1) پاکسازی داده ✔')

# 2) حذف کسرِ تکراری از PN2 (مالکِ کسر: بلوک STOCK-REFRESH)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()
old_ps5 = ("                    ps = getattr(win, 'pallet_stock', None)  # PN2B\n"
           "                    if isinstance(ps, dict):  # PN2B\n"
           "                        for kk in list(ps.keys()):  # PN2B\n"
           "                            ps[kk] = (ps[kk] or 0) - rsv.get(kk, 0)  # PN2B\n")
if old_ps5 in s:
    s = s.replace(old_ps5, '')
    print('2) کسر تکراری PN2 حذف شد ✔')
old_ps5b = ("                ps = getattr(w, 'pallet_stock', None)\n"
            "                if isinstance(ps, dict):\n"
            "                    for kk in list(ps.keys()):\n"
            "                        ps[kk] = (ps[kk] or 0) - rsv.get(kk, 0)\n")
if old_ps5b in s:
    s = s.replace(old_ps5b, '')
    print('2) کسر تکراری PN2 (نسخه بازنویسی) حذف شد ✔')

# 3) کسر رزروها روی موجودیِ سرویس هنگام نمایش هر فرم
old_sr = ("            try:\n"
          "                ps = getattr(self, 'pallet_service', None)\n"
          "                if ps is not None and callable(getattr(ps, 'reload', None)):\n"
          "                    ps.reload()\n"
          "                    if callable(getattr(self, '_refresh_pallet_combos', None)):\n"
          "                        self._refresh_pallet_combos()\n"
          "            except Exception:\n"
          "                pass\n")
new_sr = ("            try:\n"
          "                ps = getattr(self, 'pallet_service', None)\n"
          "                if ps is not None and callable(getattr(ps, 'reload', None)):\n"
          "                    ps.reload()\n"
          "                    try:  # STOCK-TRACK\n"
          "                        rsv = _reserved_map(self.db)  # STOCK-TRACK\n"
          "                        stk = getattr(self, 'pallet_stock', None)  # STOCK-TRACK\n"
          "                        if isinstance(stk, dict):  # STOCK-TRACK\n"
          "                            for kk in list(stk.keys()):  # STOCK-TRACK\n"
          "                                stk[kk] = (stk[kk] or 0) - rsv.get(kk, 0)  # STOCK-TRACK\n"
          "                        pst = getattr(ps, 'pallet_stock', None)  # STOCK-TRACK\n"
          "                        if isinstance(pst, dict):  # STOCK-TRACK\n"
          "                            for kk in list(pst.keys()):  # STOCK-TRACK\n"
          "                                pst[kk] = (pst[kk] or 0) - rsv.get(kk, 0)  # STOCK-TRACK\n"
          "                    except Exception:  # STOCK-TRACK\n"
          "                        pass  # STOCK-TRACK\n"
          "                    if callable(getattr(self, '_refresh_pallet_combos', None)):\n"
          "                        self._refresh_pallet_combos()\n"
          "            except Exception:\n"
          "                pass\n")
if old_sr in s:
    s = s.replace(old_sr, new_sr, 1)
    print('3) STOCK-TRACK نصب شد ✔')
open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

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