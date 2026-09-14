# -*- coding: utf-8 -*-
"""بازسازی کامل بلوک SELECT مرجع‌ها - اجرا: python fix_ref_clean2.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

p = os.path.join(ROOT, 'app/ui/issue_manager_window.py')
lines = open(p, encoding='utf-8').read().split('\n')
start = None
for i, l in enumerate(lines):
    if 'SELECT ol.id, ol.reference_no, ol.customer_id' in l:
        start = i
        break
if start is None:
    for i, l in enumerate(lines):
        if 'FROM outbound_load_items WHERE outbound_load_id = ol.id' in l:
            start = i - 1
            break
end = None
if start is not None:
    for j in range(start, min(len(lines), start + 25)):
        if 'ORDER BY ol.id DESC' in lines[j] or 'ORDER BY id DESC' in lines[j]:
            end = j
            break
if start is None or end is None:
    print('❌ بلوک پیدا نشد'); input(); raise SystemExit
sp = ' ' * (len(lines[start]) - len(lines[start].lstrip()))
block = [
    sp + '"SELECT ol.id, ol.reference_no, ol.customer_id, "  # REF-CLEAN',
    sp + '"(SELECT COALESCE(SUM(qty), 0) FROM outbound_load_items WHERE outbound_load_id = ol.id), "  # REF-CLEAN',
    sp + '"(SELECT COALESCE(SUM(wii.qty), 0) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id = wii.issue_id WHERE wi.outbound_load_id = ol.id AND wi.issue_status != \'CANCELLED\'), "  # REF-CLEAN',
    sp + '"(SELECT COUNT(*) FROM warehouse_issues wi WHERE wi.outbound_load_id = ol.id AND wi.issue_status != \'CANCELLED\'), "  # REF-CLEAN',
    sp + '"ol.warehouse_id "  # REF-CLEAN',
    sp + '"FROM outbound_loads ol "  # REF-CLEAN',
    sp + '"WHERE ol.is_active = 1 "  # REF-CLEAN',
    sp + '"ORDER BY ol.id DESC"  # REF-CLEAN',
]
lines[start:end + 1] = block
open(p, 'w', encoding='utf-8').write('\n'.join(lines))
py_compile.compile(p, doraise=True)
print('1) بلوک SELECT بازسازی شد ✔ (خطوط', start + 1, 'تا', end + 1, ')')
for b in block:
    print('   ', b.strip()[:80])

# 2) تازه‌سازی → بازسازی برچسب
p2 = os.path.join(ROOT, 'app/ui/combo_refresh_patch.py')
s2 = open(p2, encoding='utf-8').read()
if '# LABEL-REFRESH' not in s2:
    ls = s2.split('\n')
    st = None
    for i, l in enumerate(ls):
        if l.strip().startswith('def reload_open_references'):
            st = i
            break
    if st is not None:
        ind = len(ls[st]) - len(ls[st].lstrip())
        en = len(ls)
        for j in range(st + 1, len(ls)):
            if ls[j].strip() and (len(ls[j]) - len(ls[j].lstrip())) == ind and ls[j].lstrip().startswith('def '):
                en = j
                break
        ls[en:en] = ["    try:  # LABEL-REFRESH",
                     "        self._refresh_reference_combo()  # LABEL-REFRESH",
                     "    except Exception:  # LABEL-REFRESH",
                     "        pass  # LABEL-REFRESH"]
        open(p2, 'w', encoding='utf-8').write('\n'.join(ls))
        py_compile.compile(p2, doraise=True)
        print('2) LABEL-REFRESH ✔')
else:
    print('2) از قبل بود ✔')

# 3) بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
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