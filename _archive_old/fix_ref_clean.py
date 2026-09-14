# -*- coding: utf-8 -*-
"""منطق واحد مانده در تابع برچسب - اجرا: python fix_ref_clean.py"""
import os, sys, subprocess, shutil, py_compile, sqlite3
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 0) شفاف‌سازی ستون‌های شناور
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
if os.path.exists(db):
    con = sqlite3.connect(db)
    print('=== outbound_loads ===')
    try:
        for r in con.execute("SELECT id, reference_no, total_load_qty, issued_qty_total, remaining_qty FROM outbound_loads").fetchall():
            print('   ', r)
    except Exception as e:
        print('   ', e)
    print('=== warehouse_issues ===')
    try:
        for r in con.execute("SELECT id, issue_no, outbound_load_id, total_load_qty FROM warehouse_issues").fetchall():
            print('   ', r)
    except Exception as e:
        print('   ', e)
    con.close()

# 1) بازنویسی منبع مانده در تابع برچسب
p = os.path.join(ROOT, 'app/ui/issue_manager_window.py')
lines = open(p, encoding='utf-8').read().split('\n')
n = 0
for i, l in enumerate(lines):
    if 'COALESCE(ol.total_load_qty, 0)' in l and '# REF-CLEAN' not in l:
        lines[i:i + 3] = [
            "                       (SELECT COALESCE(SUM(qty), 0) FROM outbound_load_items WHERE outbound_load_id = ol.id),  # REF-CLEAN",
            "                       (SELECT COALESCE(SUM(wii.qty), 0) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id = wii.issue_id WHERE wi.outbound_load_id = ol.id AND wi.issue_status != 'CANCELLED'),  # REF-CLEAN",
            "                       (SELECT COUNT(*) FROM warehouse_issues wi WHERE wi.outbound_load_id = ol.id AND wi.issue_status != 'CANCELLED'),  # REF-CLEAN",
        ]
        n += 1
        break
for i, l in enumerate(lines):
    if 'total_load = int(row[3] or 0)' in l and '# REF-CLEAN' not in l:
        lines[i:i + 4] = [
            "                planned = int(row[3] or 0)  # REF-CLEAN",
            "                issued = int(row[4] or 0)  # REF-CLEAN",
            "                issue_cnt = int(row[5] or 0)  # REF-CLEAN",
            "                remaining = max(planned - issued, 0)  # REF-CLEAN",
        ]
        n += 1
        break
for i, l in enumerate(lines):
    if 'if issue_cnt' in l and 'remaining' in l and '# REF-CLEAN' not in l:
        if l.rstrip().endswith('continue'):
            lines[i:i + 1] = ["                if remaining <= 0:  # REF-CLEAN", "                    continue  # REF-CLEAN"]
        else:
            lines[i:i + 1] = ["                if remaining <= 0:  # REF-CLEAN"]
        n += 1
        break
if n:
    open(p, 'w', encoding='utf-8').write('\n'.join(lines))
    py_compile.compile(p, doraise=True)
print('1) تابع برچسب بازنویسی شد؛ موارد:', n)

# 2) تازه‌سازی → بازسازی برچسب
p2 = os.path.join(ROOT, 'app/ui/combo_refresh_patch.py')
s2 = open(p2, encoding='utf-8').read()
if '# LABEL-REFRESH' not in s2:
    ls = s2.split('\n')
    start = None
    for i, l in enumerate(ls):
        if l.strip().startswith('def reload_open_references'):
            start = i
            break
    if start is not None:
        ind = len(ls[start]) - len(ls[start].lstrip())
        end = len(ls)
        for j in range(start + 1, len(ls)):
            if ls[j].strip() and (len(ls[j]) - len(ls[j].lstrip())) == ind and ls[j].lstrip().startswith('def '):
                end = j
                break
        add = ["    try:  # LABEL-REFRESH",
               "        self._refresh_reference_combo()  # LABEL-REFRESH",
               "    except Exception:  # LABEL-REFRESH",
               "        pass  # LABEL-REFRESH"]
        ls[end:end] = add
        open(p2, 'w', encoding='utf-8').write('\n'.join(ls))
        py_compile.compile(p2, doraise=True)
        print('2) برچسب پس از تازه‌سازی بازسازی می‌شود ✔')
else:
    print('2) از قبل بود ✔')

# 3) بیلد با محافظ داده
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
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
            src = os.path.join(dp, fn); rel2 = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel2)
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
    shutil.copy2(keep, db)
    print('3) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('4) تمام ✔')
input('Enter...')