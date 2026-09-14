# -*- coding: utf-8 -*-
"""
apply_preview_patch.py — پچ جراحی‌شده برای فایل‌های ReceiptManagerWindow (و مشابه آن)

کارهایی که انجام می‌دهد:
  1) گرفتن مسیر فایل هدف از آرگومان خط فرمان
  2) تهیه نسخه پشتیبان با پسوند زمانی (.bak-YYYYmmdd-HHMMSS) کنار خود فایل
  3) رفع خطای نحوی شناخته‌شده: تبدیل {line[8] or '-'} به {line[8] or "-"}
     فقط داخل همان خط raise ValidationError (بررسی می‌شود که واقعاً داخل یک
     خط ValidationError باشد تا ویرایش‌های ناخواسته انجام نشود)
  4) بازنویسی بدنه متد _open_html_in_browser (در صورت وجود) تا ترجیحاً از
     app.ui.webengine_preview → webengine_preview → app.ui.html_preview_dialog
     → html_preview_dialog استفاده کند
  5) افزودن dlg.setAttribute(Qt.WA_DeleteOnClose, True) قبل از exec_() به شرطی
     که Qt در فایل قابل دسترسی باشد؛ در غیر این صورت فایل دست‌نخورده می‌ماند
  6) چاپ پیام‌های موفقیت/شکست به فارسی + یادآوری نحوه اجرا

نحوه اجرا (از ریشه پروژه):
    python apply_preview_patch.py app/ui/receipt_manager_window.py
یا با مسیر کامل:
    python /path/to/apply_preview_patch.py /path/to/receipt_manager_window.py
اگر در روت نیستید، اول به ریشه پروژه بروید:
    cd /path/to/project
سپس دستور بالا را اجرا کنید.
"""

import argparse
import datetime
import os
import re
import shutil
import sys

# ---------------------------------------------------------------- ثابت‌ها

SYNTAX_LINE8_PATTERN = re.compile(
    r"""
    (?P<indent>[ \t]*)                 # تورفتگی خط
    raise\s+ValidationError\(\s*f?['"]  # شروع raise ValidationError
    (?P<body>.*?)                      # کل محتوای داخل رشته
    ['"]\s*\)\s*$                      # پایان فراخوانی
    """,
    re.VERBOSE | re.DOTALL | re.MULTILINE,
)

# فقط جایی که دقیقاً {line[8] or '-'} است را عوض می‌کنیم
LINE8_BAD = "{line[8] or '-'}"
LINE8_GOOD = '{line[8] or "-"}'

NEW_PREVIEW_BODY = '''    def _open_html_in_browser(self, html: str) -> None:  # DLG-FINAL
        """پیش‌نمایش HTML با ترجیح WebEngine و بازگشت به دیالوگ ساده."""
        parent = self
        candidates = (
            ('app.ui.webengine_preview', 'HtmlPreviewDialog'),
            ('webengine_preview', 'HtmlPreviewDialog'),
            ('app.ui.html_preview_dialog', 'HtmlPreviewDialog'),
            ('html_preview_dialog', 'HtmlPreviewDialog'),
        )
        for mod_name, cls_name in candidates:
            try:
                module = __import__(mod_name, fromlist=[cls_name])
            except Exception:
                continue
            cls = getattr(module, cls_name, None)
            if cls is None:
                continue
            try:
                dlg = cls(html, '', parent)
                try:
                    dlg.setAttribute(Qt.WA_DeleteOnClose, True)  # PATCH-DELETEONCLOSE
                except Exception:
                    pass
                dlg.exec_()
            except Exception:
                continue
            return
        # هیچ پیش‌نمایشی در دسترس نبود
        try:
            import webbrowser
            import tempfile
            fd, path = tempfile.mkstemp(suffix='.html')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(html or '')
            webbrowser.open('file://' + path)
        except Exception:
            pass
'''

# ---------------------------------------------------------------- توابع


def make_backup(path: str) -> str:
    """تهیه نسخه پشتیبان با پسوند زمانی، کنار خود فایل هدف."""
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup_path = f"{path}.bak-{stamp}"
    shutil.copy2(path, backup_path)
    return backup_path


def fix_validationerror_syntax(text: str):
    """رفع {line[8] or '-'} → {line[8] or "-"} فقط در خط ValidationError."""
    count = 0

    def _fix_line(m):
        nonlocal count
        line = m.group(0)
        if LINE8_BAD in line:
            new_line = line.replace(LINE8_BAD, LINE8_GOOD)
            count += 1
            return new_line
        return line

    new_text = SYNTAX_LINE8_PATTERN.sub(_fix_line, text)
    return new_text, count


def replace_preview_method(text: str):
    """جایگزینی بدنه متد _open_html_in_browser با نسخه چند‌مرحله‌ای."""
    pattern = re.compile(
        r"(?P<indent>[ \t]*)def _open_html_in_browser\(self,\s*html:\s*str\)\s*->\s*None:.*?"
        r"(?=\n(?:[ \t]*)def |\n(?:[ \t]*)class |\Z)",
        re.DOTALL,
    )
    m = pattern.search(text)
    if not m:
        return text, False
    indent = m.group('indent') or '    '
    new_method = NEW_PREVIEW_BODY.rstrip('\n')
    # اگر بدنه قدیمی تورفتگی متفاوتی داشت، تنظیمش می‌کنیم
    new_method = '\n'.join(
        (indent + ln[len(indent):]) if ln.startswith(indent) else (indent + ln if ln.strip() else ln)
        for ln in new_method.split('\n')
    )
    start, end = m.start(), m.end()
    replacement = new_method + '\n\n'
    new_text = text[:start] + replacement + text[end:]
    return new_text, True


def qt_is_available(text: str) -> bool:
    """تشخیص اینکه آیا Qt در فایل قابل دسترسی است یا نه."""
    return bool(re.search(r'\bQt\b', text) and
                re.search(r'from\s+PyQt5\.QtCore\s+import[^\n]*\bQt\b|'
                          r'from\s+PyQt6\.QtCore\s+import[^\n]*\bQt\b|'
                          r'from\s+PySide6\.QtCore\s+import[^\n]*\bQt\b', text))


def add_delete_on_close(text: str) -> tuple:
    """افزودن dlg.setAttribute(Qt.WA_DeleteOnClose, True) قبل از dlg.exec_() (فقط یکی)."""
    if 'Qt.WA_DeleteOnClose' in text:
        return text, False  # قبلاً موجود است
    if not qt_is_available(text):
        return text, False
    pattern = re.compile(
        r"(?P<indent>[ \t]*)(?P<dlgvar>dlg|dialog)\.exec_\(\)"
    )
    m = pattern.search(text)
    if not m:
        return text, False
    indent = m.group('indent')
    dlgvar = m.group('dlgvar')
    insert = f"{indent}{dlgvar}.setAttribute(Qt.WA_DeleteOnClose, True)\n"
    start = m.start()
    new_text = text[:start] + insert + text[start:]
    return new_text, True


def apply_patch(path: str) -> bool:
    if not os.path.isfile(path):
        print(f"[خطا] فایل هدف پیدا نشد: {path}")
        print("یادآوری: مسیر را نسبت به ریشه پروژه بدهید، مثلاً:")
        print("    python apply_preview_patch.py app/ui/receipt_manager_window.py")
        return False

    with open(path, 'r', encoding='utf-8') as f:
        original = f.read()
    text = original
    changed_any = False

    # ---------- ۱) تهیه نسخه پشتیبان ----------
    try:
        backup = make_backup(path)
        print(f"[موفق] نسخه پشتیبان ساخته شد: {backup}")
    except Exception as exc:
        print(f"[خطا] ساخت نسخه پشتیبان ناموفق بود: {exc}")
        return False

    # ---------- ۲) رفع خطای نحوی ValidationError ----------
    text, n_fixed = fix_validationerror_syntax(text)
    if n_fixed:
        print(f"[موفق] {n_fixed} مورد از الگوی {{line[8] or '-'}} در خط ValidationError اصلاح شد.")
        changed_any = True
    else:
        print("[نکته] الگوی {{line[8] or '-'}} در خط ValidationError پیدا نشد (احتمالاً قبلاً اصلاح شده).")

    # ---------- ۳) بازنویسی متد _open_html_in_browser ----------
    text, replaced = replace_preview_method(text)
    if replaced:
        print("[موفق] بدنه متد _open_html_in_browser با نسخه WebEngine-محور جایگزین شد.")
        changed_any = True
    else:
        print("[نکته] متد _open_html_in_browser در فایل یافت نشد؛ این مرحله رد شد.")

    # ---------- ۴) افزودن WA_DeleteOnClose ----------
    text, added = add_delete_on_close(text)
    if added:
        print("[موفق] dlg.setAttribute(Qt.WA_DeleteOnClose, True) قبل از exec_() اضافه شد.")
        changed_any = true if False else True  # keep flag True
    else:
        print("[نکته] افزودن WA_DeleteOnClose انجام نشد (یا Qt در دسترس نیست یا قبلاً موجود است).")

    # ---------- ۵) ذخیره فایل ----------
    if changed_any:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"[موفق] فایل هدف با موفقیت پچ شد: {path}")
        print("یادآوری نحوه اجرا (اگر در روت پروژه نیستید):")
        print("    cd /path/to/project")
        print("    python apply_preview_patch.py app/ui/receipt_manager_window.py")
    else:
        print("[نکته] هیچ تغییری لازم نبود یا اعمال نشد؛ فایل دست‌نخورده باقی ماند.")
        print("یادآوری نحوه اجرا: python apply_preview_patch.py <مسیر فایل هدف>")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='پچ جراحی‌شده برای فایل‌های ReceiptManagerWindow')
    parser.add_argument('target', help='مسیر فایل هدف (مثلاً app/ui/receipt_manager_window.py)')
    args = parser.parse_args()
    ok = apply_patch(args.target)
    if not ok:
        print("[شکست] پچ اعمال نشد. لطفاً پیام‌های بالا را بررسی کنید.")
        sys.exit(1)
    print("[پایان] عملیات پچ تمام شد.")


if __name__ == '__main__':
    main()
