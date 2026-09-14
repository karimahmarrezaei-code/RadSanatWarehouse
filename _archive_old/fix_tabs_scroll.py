# -*- coding: utf-8 -*-
"""SAFE-FIT v2: اسکرول خودکار با توجه به تعویض تب - اجرا: python fix_tabs_scroll.py"""
import os, sys, subprocess, shutil, py_compile
ROOT = os.path.dirname(os.path.abspath(__file__)); os.chdir(ROOT)
mp = os.path.join(ROOT, 'main.py'); s = open(mp, encoding='utf-8').read()

NEW = (
    "# SAFE-FIT-CODE v2: جا و اسکرول خودکار + توجه به تب‌ها - SAFE-FIT-CODE\n"
    "try:\n"
    "    from PyQt5.QtWidgets import QMainWindow as _QM, QScrollArea as _QS, QVBoxLayout as _QV, QWidget as _QW, QTabWidget as _QTW\n"
    "    _orig_show = _QW.show\n"
    "    def _safe_fit(self):\n"
    "        try:\n"
    "            if not self.isWindow() or getattr(self, '_safe_wrapped', False):\n"
    "                return\n"
    "            scr = QApplication.desktop().availableGeometry()\n"
    "            if self.sizeHint().height() > scr.height():\n"
    "                self._safe_wrapped = True\n"
    "                if isinstance(self, _QM) and self.centralWidget() is not None:\n"
    "                    cw = self.takeCentralWidget()\n"
    "                    sa = _QS(); sa.setWidgetResizable(True); sa.setWidget(cw)\n"
    "                    self.setCentralWidget(sa)\n"
    "                elif self.layout() is not None:\n"
    "                    lay = self.layout()\n"
    "                    inner = _QW(); inner.setLayout(lay)\n"
    "                    sa = _QS(); sa.setWidgetResizable(True); sa.setWidget(inner)\n"
    "                    outer = _QV(self); outer.setContentsMargins(0, 0, 0, 0); outer.addWidget(sa)\n"
    "        except Exception:\n"
    "            pass\n"
    "    def _safe_show(self):\n"
    "        try:\n"
    "            if self.isWindow() and not getattr(self, '_safe_done', False):\n"
    "                self._safe_done = True\n"
    "                scr = QApplication.desktop().availableGeometry()\n"
    "                w = min(self.width(), scr.width())\n"
    "                h = min(self.height(), scr.height())\n"
    "                if (w, h) != (self.width(), self.height()):\n"
    "                    self.resize(w, h)\n"
    "                _safe_fit(self)\n"
    "                for tw in self.findChildren(_QTW):\n"
    "                    tw.currentChanged.connect(lambda _i, _w=self: _safe_fit(_w))\n"
    "        except Exception:\n"
    "            pass\n"
    "        return _orig_show(self)\n"
    "    _QW.show = _safe_show\n"
    "except Exception:\n"
    "    pass\n"
)

start = s.find('# SAFE-FIT-CODE:')
if start >= 0 and 'SAFE-FIT-CODE v2' not in s:
    i2 = s.find('_QW.show = _safe_show')
    i3 = s.find('except Exception:\n    pass\n', i2)
    end = i3 + len('except Exception:\n    pass\n')
    s = s[:start] + NEW + s[end:]
    open(mp, 'w', encoding='utf-8').write(s)
    py_compile.compile(mp, doraise=True)
    print('1) SAFE-FIT v2 جایگزین شد')
else:
    print('1) نیازی به جایگزینی نبود')

print('2) بیلد...')
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
print('2) تمام')
print('=== تست در 1366x768: پیش‌فاکتور و سند مالی → تب تسویه ===')
input('Enter...')