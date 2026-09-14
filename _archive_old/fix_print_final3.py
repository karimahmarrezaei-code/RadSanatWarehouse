# -*- coding: utf-8 -*-
"""پاکسازی کامل + درج دقیق بعد از خط 799 - اجرا: python fix_print_final3.py"""
import os, re, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

p = os.path.join(ROOT, 'app', 'repositories', 'issue_repository.py')
lines = open(p, encoding='utf-8').read().split('\n')

# 1) پاکسازی همه PRINT-FIX
before = len(lines)
lines = [l for l in lines if '# PRINT-FIX' not in l]
print('1) خطوط PRINT-FIX حذف شد:', before - len(lines))

# 2) helper بعد از آخرین import
HELPER = [
    "def _load_metrics(db, reference_no):",
    "    try:",
    "        with db.connect() as cn:",
    "            cn.row_factory = None",
    "            r = cn.execute(\"SELECT id FROM outbound_loads WHERE reference_no=?\", (reference_no,)).fetchone()",
    "            if not r:",
    "                return (0, 0)",
    "            pl = cn.execute(\"SELECT COALESCE(SUM(qty),0) FROM outbound_load_items WHERE outbound_load_id=?\", (r[0],)).fetchone()[0]",
    "            iss = cn.execute(\"SELECT COALESCE(SUM(wii.qty),0) FROM warehouse_issue_items wii JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=? AND wi.issue_status!='CANCELLED'\", (r[0],)).fetchone()[0]",
    "            return (int(pl or 0), int(iss or 0))",
    "    except Exception:",
    "        return (0, 0)",
    "",
]
last_imp = 0
for i, l in enumerate(lines[:80]):
    if l.startswith('import ') or l.startswith('from '):
        last_imp = i
lines[last_imp + 1:last_imp + 1] = HELPER

# 3) پیدا کردن خط دقیق render_issue_html
target_line = None
for i, l in enumerate(lines):
    if l.strip() == 'def render_issue_html(self, context: Dict[str, Any]) -> str:':
        target_line = i
        break
if target_line is None:
    print('❌ خط دقیق پیدا نشد'); input(); raise SystemExit
print('2) خط هدف:', target_line + 1, '->', lines[target_line].strip())

# 4) درج بلوک با تورفتگی 8 (چون body تابع با 8 فاصله شروع می‌شود)
sp = '        '
block = [
    sp + "try:",
    sp + "    _m_pl, _m_is = _load_metrics(self.db, context.get('reference_no'))",
    sp + "    context = dict(context)",
    sp + "    context['total_load_qty'] = _m_pl",
    sp + "    context['delivered_qty'] = _m_is",
    sp + "    context['discrepancy_qty'] = _m_pl - _m_is",
    sp + "except Exception:",
    sp + "    pass",
]
lines[target_line + 1:target_line + 1] = block

open(p, 'w', encoding='utf-8').write('\n'.join(lines))
py_compile.compile(p, doraise=True)
print('3) بلوک درج و کامپایل شد ✔')

# 5) بیلد با محافظ داده
db = os.path.join(ROOT, 'dist', 'RadSanatWarehouse', '_internal', 'data', 'app.db')
keep = os.path.join(ROOT, 'last_app.db')
if os.path.exists(db):
    shutil.copy2(db, keep)
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
    print('4) app.db برگشت ✔')
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('5) تمام ✔')
input('Enter...')