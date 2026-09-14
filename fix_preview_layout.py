import os
import re

file_path = os.path.join("app", "ui", "html_preview_dialog.py")
if not os.path.exists(file_path):
    file_path = "html_preview_dialog.py"

if not os.path.exists(file_path):
    print(f"❌ فایل پیدا نشد: {file_path}")
    exit(1)

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# ۱. افزودن QSizePolicy به ایمپورت‌ها در صورت عدم وجود
if "QSizePolicy" not in content:
    content = content.replace("from PyQt5.QtWidgets import ", "from PyQt5.QtWidgets import QSizePolicy, ")

# ۲. تغییر ابعاد اولیه پنجره و تنظیم WindowFlags در __init__
init_patch = """        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint | Qt.WindowMaximizeButtonHint)
        self.setLayoutDirection(Qt.RightToLeft)"""

content = re.sub(r"super\(\)\.__init__\(parent\)\s+self\.setWindowTitle\(title\)\s+self\.resize\(\d+,\s*\d+\)\s+self\.setLayoutDirection\(Qt\.RightToLeft\)", init_patch, content)

# ۳. اصلاح _build_ui برای تنظیم QSizePolicy و stretch صحیح QTextBrowser
build_ui_patch = """        self.browser = QTextBrowser()
        self.browser.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.browser.setOpenExternalLinks(False)
        self.browser.setFont(QFont('Tahoma', 10))
        self.browser.setStyleSheet('QTextBrowser{background:#ffffff;color:#000000;}')
        self.browser.setHtml(self.html_content)
        layout.addWidget(self.browser, 1)"""

content = re.sub(r"self\.browser = QTextBrowser\(\)\s+self\.browser\.setOpenExternalLinks\(False\).*?layout\.addWidget\(self\.browser\)", build_ui_patch, content, flags=re.DOTALL)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("✅ پچ دیالوگ پیش‌نمایش با موفقیت اعمال شد!")
