import os
import shutil
import re

# جستجوی خودکار برای یافتن فایل پنجره پیش‌فاکتور
candidate_paths = [
    os.path.join("app", "ui", "proforma_invoice_window.py"),
    os.path.join("app", "ui", "proforma_window.py"),
    os.path.join("app", "ui", "proforma.py"),
]

target_file = None
for p in candidate_paths:
    if os.path.exists(p):
        target_file = p
        break

if not target_file:
    # جستجوی عمیق‌تر در صورت متفاوت بودن نام
    for root, dirs, files in os.walk("app"):
        for f in files:
            if "proforma" in f.lower() and f.endswith(".py"):
                target_file = os.path.join(root, f)
                break
        if target_file:
            break

if not target_file:
    print("❌ خطا: فایل پنجره پیش‌فاکتور پیدا نشد! لطفاً نام و مسیر دقیق فایل را بررسی کنید.")
    exit(1)

print(f"🔍 فایل هدف پیدا شد: {target_file}")

# ۱. تهیه نسخه پشتیبان
backup_file = target_file + ".bak"
shutil.copyfile(target_file, backup_file)
print(f"📦 نسخه پشتیبان ایجاد شد: {backup_file}")

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# ۲. پچ ۱: اضافه کردن فلگ‌های پنجره (دکمه‌های ماکسیمایز و مینیمایز) در __init__
pattern_init = r"(def __init__\s*\(self,\s*db,\s*user_data\):[\r\n]+\s+super\(\)\.__init__\(\))"
replacement_init = r"""\1
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )"""

if "Qt.WindowMinMaxButtonsHint" not in content:
    content, count = re.subn(pattern_init, replacement_init, content, count=1)
    if count > 0:
        print("✅ ۱. فلگ‌های ماکسیمایز/مینیمایز با موفقیت اضافه شد.")
    else:
        print("⚠️ ۱. الگو برای __init__ تطبیق پیدا نکرد (ممکن است ساختار متفاوتی داشته باشد).")
else:
    print("ℹ️ ۱. فلگ‌های پنجره قبلاً اعمال شده بودند.")

# ۳. پچ ۲: اصلاح متد showEvent (برداشتن ماکسیمایز اجباری مکرر)
old_show_event = """    def showEvent(self, event):
        super().showEvent(event)
        self.setWindowState(Qt.WindowMaximized)"""

new_show_event = """    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, '_shown_once', False):
            self._shown_once = True
            self.resize(1200, 750)"""

if old_show_event in content:
    content = content.replace(old_show_event, new_show_event, 1)
    print("✅ ۲. متد showEvent اصلاح شد و ماکسیمایز اجباری برداشته شد.")
else:
    print("ℹ️ ۲. متد showEvent با الگوی دقیق یافت نشد یا قبلاً اصلاح شده است.")

# ۴. پچ ۳: اضافه کردن QScrollArea به تب‌ها در _build_ui
old_tabs_code = """        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_new_tab(), 'ثبت پیش‌فاکتور جدید')
        self.tabs.addTab(self._build_list_tab(), 'لیست پیش‌فاکتورها')
        root.addWidget(self.tabs)"""

new_tabs_code = """        self.tabs = QTabWidget()
        
        def _wrap_in_scroll(widget):
            from PyQt5.QtWidgets import QScrollArea
            sa = QScrollArea()
            sa.setWidgetResizable(True)
            sa.setWidget(widget)
            sa.setFrameShape(QScrollArea.NoFrame)
            return sa

        self.tabs.addTab(_wrap_in_scroll(self._build_new_tab()), 'ثبت پیش‌فاکتور جدید')
        self.tabs.addTab(_wrap_in_scroll(self._build_list_tab()), 'لیست پیش‌فاکتورها')
        root.addWidget(self.tabs)"""

if old_tabs_code in content:
    content = content.replace(old_tabs_code, new_tabs_code, 1)
    print("✅ ۳. اسکرول‌بار خودکار (QScrollArea) به تب‌ها اضافه شد.")
else:
    # تلاش با گیومه دوتایی در صورت تفاوت در کوتیشن‌ها
    old_tabs_code_double = old_tabs_code.replace("'", '"')
    if old_tabs_code_double in content:
        content = content.replace(old_tabs_code_double, new_tabs_code, 1)
        print("✅ ۳. اسکرول‌بار خودکار (QScrollArea) به تب‌ها اضافه شد.")
    else:
        print("ℹ️ ۳. بخش تب‌ها قبلاً اصلاح شده یا ساختار تغییر یافته است.")

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)

print("\n🚀 عملیات پچ با موفقیت انجام شد! می‌توانید برنامه را تست کنید.")
