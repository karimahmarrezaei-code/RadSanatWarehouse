"""
اسکریپت اعمال پچ جراحی روی main.py
"""
import py_compile
import sys

TARGET = "main.py"

try:
    with open(TARGET, "r", encoding="utf-8") as f:
        code = f.read()

    # ۱. اصلاح خطای w و Recursion در _safe_show
    old_show = """        if isinstance(w, _QD3):  # SHOW-SKIP
            w.show()  # SHOW-SKIP
            return  # SHOW-SKIP"""

    new_show = """        if isinstance(self, _QD3):  # SHOW-SKIP
            return _orig_show(self)  # SHOW-SKIP"""

    # ۲. اصلاح ایمپورت _QWV در _safe_fit
    old_fit = """    try:  # PREV-FIX
        if w.findChildren(_QWV):  # PREV-FIX
            return  # PREV-FIX
    except Exception:  # PREV-FIX
        pass  # PREV-FIX"""

    new_fit = """    try:  # PREV-FIX
        from PyQt5.QtWebEngineWidgets import QWebEngineView as _QWV  # PREV-FIX
        if _QWV is not None and w.findChildren(_QWV):  # PREV-FIX
            return  # PREV-FIX
    except Exception:  # PREV-FIX
        pass  # PREV-FIX"""

    if old_show in code:
        code = code.replace(old_show, new_show, 1)
        print("✓ بخش _safe_show با موفقیت پچ شد.")
    else:
        print("- بخش _safe_show قبلاً پچ شده یا الگوی آن تغییر کرده است.")

    if old_fit in code:
        code = code.replace(old_fit, new_fit, 1)
        print("✓ بخش _safe_fit با موفقیت پچ شد.")
    else:
        print("- بخش _safe_fit قبلاً پچ شده یا الگوی آن تغییر کرده است.")

    with open(TARGET, "w", encoding="utf-8") as f:
        f.write(code)

    py_compile.compile(TARGET, doraise=True)
    print("✓ فایل main.py بدون خطای سینتکس کامپایل شد.")

except Exception as e:
    print(f"خطا در اعمال پچ: {e}")
    sys.exit(1)
