# -*- coding: utf-8 -*-
"""اصحاب اعداد چاپ حواله از اقلام - اجرا: python fix_print_final.py"""
import os, re, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

HELPER = (
    "def _load_metrics(db, reference_no):  # PRINT-FIX\n"
    "    try:  # PRINT-FIX\n"
    "        with db.connect() as cn:  # PRINT-FIX\n"
    "            cn.row_factory = None  # PRINT-FIX\n"
    "            r = cn.execute(\"SELECT id FROM outbound_loads WHERE reference_no=?\", (reference_no,)).fetchone()  # PRINT-FIX\n"
    "            if not r:  # PRINT-FIX\n"
    "                return (0, 0)  # PRINT-FIX\n"
    "            pl = cn.execute(\"SELECT COALESCE(SUM(qty),0) FROM outbound_load_items WHERE outbound_load_id=?\", (r[0],)).fetchone()[0]  # PRINT-FIX\n"
    "            iss = cn.execute(\"SELECT COALESCE(SUM(wii.qty),0) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=? AND wi.issue_status!='CANCELLED'\", (r[0],)).fetchone()[0]  # PRINT-FIX\n"
    "            return (int(pl or 0), int(iss or 0))  # PRINT-FIX\n"
    "    except Exception:  # PRINT-FIX\n"
    "        return (0, 0)  # PRINT-FIX\n"
    "\n"
)

p = os.path.join(ROOT, 'app', 'repositories', 'issue_repository.py')
s = open(p, encoding='utf-8').read()
if '# PRINT-FIX' not in s:
    # 1) helper بعد از آخرین import
    last_imp = 0
    for i, l in enumerate(s.split('\n')[:60]):
        if l.startswith('import ') or l.startswith('from '):
            last_imp = i
    lines = s.split('\n')
    lines[last_imp + 1:last_imp + 1] = HELPER.split('\n')
    s = '\n'.join(lines)
    # 2) بازمحاسبه context داخل تابع چاپ
    m = re.search(r'(?m)^(\s*)def \w*(render|print|html)\w*\(', s)
    if m:
        ind = len(m.group(1)) + 4
        sp = ' ' * ind
        block = (sp + "try:  # PRINT-FIX\n" +
                 sp + "    _m_pl, _m_is = _load_metrics(self.db, context.get('reference_no'))  # PRINT-FIX\n" +
                 sp + "    context = dict(context)  # PRINT-FIX\n" +
                 sp + "    context['total_load_qty'] = _m_pl  # PRINT-FIX\n" +
                 sp + "    context['delivered_qty'] = _m_is  # PRINT-FIX\n" +
                 sp + "    context['discrepancy_qty'] = _m_pl - _m_is  # PRINT-FIX\n" +
                 sp + "except Exception:  # PRINT-FIX\n" +
                 sp + "    pass  # PRINT-FIX\n")
        j = s.find('\n', m.end()) + 1
        s = s[:j] + block + s[j:]
        print('1) helper + بازمحاسبه نصب شد ✔')
    else:
        print('1) ⚠ تابع چاپ پیدا نشد')
    open(p, 'w', encoding='utf-8').write(s)
    py_compile.compile(p, doraise=True)
else:
    print('1) از قبل بود ✔')

# بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
print('2) بیلد...')
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
    print('2) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('3) تمام ✔')
input('Enter...')