# -*- coding: utf-8 -*-
"""ابعاد آزاد + کامبوی گویا + ستون عریض - اجرا: python fix_pallet_row.py"""
import os, re, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)

# 1) فرم پالت: سقف اسپین‌ها آزاد (اول self.* بعد محلی‌ها)
p = os.path.join(ROOT, 'app', 'ui', 'pallets_window.py')
s = open(p, encoding='utf-8').read()
s, n_self = re.subn(r'(self\.[A-Za-z_][A-Za-z0-9_]*)\s*=\s*QSpinBox\(\)',
                    lambda m: f'{m.group(1)} = QSpinBox(); {m.group(1)}.setRange(0, 1000000)', s)
def _rng(m):
    nm = m.group(1)
    lo = '1' if any(k in nm.lower() for k in ('length', 'width', 'height')) else '0'
    return f'{nm} = QSpinBox(); {nm}.setRange({lo}, 1000000)'
s, n_loc = re.subn(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*QSpinBox\(\)', _rng, s)
open(p, 'w', encoding='utf-8').write(s); py_compile.compile(p, doraise=True)
print('1) اسپین‌های آزاد:', n_self, n_loc)

# 2) کامبوهای گویا + ستون عریض در رسید و موجودی اول دوره
ADD = ("{ind}_s = 0\n{ind}_a = 0\n"
       "{ind}try: _s = int(getattr(self, 'pallet_stock', {{}}).get({v}['id'], 0) or 0)\n"
       "{ind}except Exception: pass\n"
       "{ind}try: _a = int(getattr(self, 'avg_pallet_prices', {{}}).get({v}['id'], 0) or 0)\n"
       "{ind}except Exception: pass\n"
       "{ind}_txt = f\"{v}['code'] | {v}['name'] | مانده: {_s:,}\"\n"
       "{ind}if _a > 0: _txt += f\" | میانگین: {_a:,}\"\n"
       "{ind}pallet_combo.addItem(_txt, {v}['id'])")
for rel in ('app/ui/receipt_manager_window.py', 'app/ui/opening_inventory_window.py'):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        continue
    s = open(p, encoding='utf-8').read()
    pat = re.compile(r"(?P<ind>[ \t]*)pallet_combo\.addItem\(f\"(?P<v>[a-z_]+)\['code'\]\} \| (?P=v)\['name'\]\}\", (?P=v)\['id'\]\)")
    def _rep(m):
        return ADD.format(ind=m.group('ind'), v=m.group('v'))
    s, n = pat.subn(_rep, s)
    s, n2 = re.subn(r'(?P<ind>[ \t]*)pallet_combo = QComboBox\(\)',
                    lambda m: m.group(0) + '\n' + m.group('ind') + 'try: self.lines_table.setColumnWidth(1, 430)\n' + m.group('ind') + 'except Exception: pass', s)
    open(p, 'w', encoding='utf-8').write(s); py_compile.compile(p, doraise=True)
    print('2)', rel, '| combo:', n, '| width:', n2)

# 3) بیلد + تزریق
print('3) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق؛ اول: taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
idata = os.path.join(DST, '_internal', 'data'); os.makedirs(idata, exist_ok=True)
for fn in os.listdir(os.path.join(ROOT, 'data')):
    if fn.endswith(('.sql', '.json', '.key')):
        shutil.copy2(os.path.join(ROOT, 'data', fn), os.path.join(idata, fn))
db = os.path.join(idata, 'app.db')
if os.path.exists(db): os.remove(db)
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
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
print('3) تمام ✔')
input('Enter...')