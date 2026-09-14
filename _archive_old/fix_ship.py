# -*- coding: utf-8 -*-
"""نسخه نهایی: بدون مقیاس سراسری + جا و اسکرول خودکار - اجرا: python fix_ship.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

# 1) خاموش کردن مقیاس سراسری (رندر فریزن با آن خراب است)
old = "if _AUTO_FACTOR != 1.0:\n    _os2.environ['QT_SCALE_FACTOR'] = str(_AUTO_FACTOR)\n"
if old in s:
    s = s.replace(old, "# SAFE-FIT: بدون مقیاس سراسری (رندر امن)\n")
    print('1) مقیاس سراسری خاموش شد')

# 2) حذف کف لاگین (لاگین با اندازه طبیعی کامل است)
s = s.replace('    login_dlg.setMinimumSize(620, 500)  # LOGIN-FIX2\n', '')

# 3) SAFE-FIT: جا + اسکرول خودکار برای صفحه‌های کوچک
if '# SAFE-FIT-CODE' not in s:
    anchor = 'from PyQt5.QtGui import QIcon'
    j = s.find(anchor)
    nl = s.find('\n', j) + 1
    block = (
        "# SAFE-FIT-CODE: جا و اسکرول خودکار در صفحه کوچک - SAFE-FIT-CODE\n"
        "try:\n"
        "    from PyQt5.QtWidgets import QMainWindow as _QM, QScrollArea as _QS, QVBoxLayout as _QV, QWidget as _QW\n"
        "    _orig_show = _QW.show\n"
        "    def _safe_show(self):\n"
        "        try:\n"
        "            if self.isWindow() and not self.isMaximized() and not getattr(self, '_safe_done', False):\n"
        "                self._safe_done = True\n"
        "                scr = QApplication.desktop().availableGeometry()\n"
        "                w = min(self.width(), scr.width())\n"
        "                h = min(self.height(), scr.height())\n"
        "                if (w, h) != (self.width(), self.height()):\n"
        "                    self.resize(w, h)\n"
        "                if self.sizeHint().height() > scr.height():\n"
        "                    if isinstance(self, _QM) and self.centralWidget() is not None:\n"
        "                        cw = self.takeCentralWidget()\n"
        "                        sa = _QS(); sa.setWidgetResizable(True); sa.setWidget(cw)\n"
        "                        self.setCentralWidget(sa)\n"
        "                    elif self.layout() is not None:\n"
        "                        lay = self.layout()\n"
        "                        inner = _QW(); inner.setLayout(lay)\n"
        "                        sa = _QS(); sa.setWidgetResizable(True); sa.setWidget(inner)\n"
        "                        outer = _QV(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(sa)\n"
        "        except Exception:\n"
        "            pass\n"
        "        return _orig_show(self)\n"
        "    _QW.show = _safe_show\n"
        "except Exception:\n"
        "    pass\n"
        "\n"
    )
    s = s[:nl] + block + s[nl:]
    print('3) SAFE-FIT اضافه شد')

open(mp, 'w', encoding='utf-8').write(s)
py_compile.compile(mp, doraise=True)

print('4) بیلد...')
r = subprocess.run([sys.executable, '-m', 'PyInstaller', 'RadSanatWarehouse.spec', '--noconfirm'], cwd=ROOT)
if r.returncode != 0:
    print('بیلد ناموفق؛ اول taskkill /f /im RadSanatWarehouse.exe'); input(); raise SystemExit
DST = os.path.join(ROOT, 'dist', 'RadSanatWarehouse')
idata = os.path.join(DST, '_internal', 'data'); os.makedirs(idata, exist_ok=True)
for fn in os.listdir(os.path.join(ROOT, 'data')):
    if fn.endswith(('.sql', '.json')):
        shutil.copy2(os.path.join(ROOT, 'data', fn), os.path.join(idata, fn))
db = os.path.join(idata, 'app.db')
if os.path.exists(db): os.remove(db)
dst_app = os.path.join(DST, '_internal', 'app')
exts = ('.qss', '.json', '.png', '.ico', '.ttf', '.css', '.svg', '.html', '.sql')
for dp, ds, fs in os.walk(os.path.join(ROOT, 'app')):
    for fn in fs:
        if fn.endswith(exts):
            src = os.path.join(dp, fn); rel = os.path.relpath(src, os.path.join(ROOT, 'app')); tgt = os.path.join(dst_app, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True); shutil.copy2(src, tgt)
for fn in os.listdir(ROOT):
    if fn.endswith(('.ico', '.png')) and ('icon' in fn.lower() or 'rad_sanat' in fn.lower()):
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, fn))
        shutil.copy2(os.path.join(ROOT, fn), os.path.join(DST, '_internal', fn))
with open(os.path.join(DST, 'run.bat'), 'w') as f:
    f.write('@echo off\r\nset QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox --disable-gpu --single-process --disable-software-rasterizer\r\nset QTWEBENGINE_DISABLE_SANDBOX=1\r\ncd /d "%~dp0"\r\nstart "" "%~dp0RadSanatWarehouse.exe"\r\n')
sc = ('@echo off\r\nset "d=%~dp0"\r\npowershell -NoProfile -Command "'
      "$w=New-Object -ComObject WScript.Shell;"
      "$s=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\RadSanatWarehouse.lnk');"
      "$s.TargetPath='%d%run.bat';$s.WorkingDirectory='%d%';"
      "$s.IconLocation='%d%RadSanatWarehouse.exe,0';"
      '$s.Save()"'
      '\r\necho Shortcut created\r\npause\r\n')
with open(os.path.join(DST, 'make_shortcut.bat'), 'w') as f:
    f.write(sc)
scl = os.path.join(DST, 'scale.txt')
if os.path.exists(scl): os.remove(scl)
print('4) تمام')
print('=== رزولوشن 1366x768 → run.bat ===')
input('Enter...')