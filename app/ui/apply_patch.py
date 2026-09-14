import os

def patch_file(filename):
    if not os.path.exists(filename):
        print(f"خطا: فایل {filename} پیدا نشد!")
        return

    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # ۱. اصلاح خطای Syntax (f-string)
    target_syntax = "raise ValidationError(f'موجودی پالت «{line[7]}» در انبار «{line[8] or '-'}» کافی نیست."
    if target_syntax in content:
        content = content.replace(target_syntax, "raise ValidationError(f'موجودی پالت «{line[7]}» در انبار «{line[8] or \"-\"}» کافی نیست.")
        print("✅ خطای f-string اصلاح شد.")
    
    # ۲. اصلاح متد پیش‌نمایش (WebEngine)
    old_preview = """    def _open_html_in_browser(self, html: str) -> None:
        from app.ui.html_preview_dialog import HtmlPreviewDialog
        HtmlPreviewDialog(html, '', self).exec_()"""
    
    new_preview = """    def _open_html_in_browser(self, html: str) -> None:
        try:
            from app.ui.webengine_preview import HtmlPreviewDialog
        except ImportError:
            from webengine_preview import HtmlPreviewDialog
        HtmlPreviewDialog(html, 'پیش‌نمایش', self).exec_()"""
    
    if old_preview in content:
        content = content.replace(old_preview, new_preview)
        print("✅ متد پیش‌نمایش به موتور مدرن ارتقا یافت.")
    else:
        print("⚠️ متد پیش‌نمایش پیدا نشد (شاید قبلاً تغییر داده‌اید).")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print("🚀 تمام شد! فایل با موفقیت پچ شد.")

# نام فایلی که فرم ورود/خروج شما در آن است را اینجا بنویسید:
patch_file("receipt_manager_window.py")
