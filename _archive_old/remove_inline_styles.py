# -*- coding: utf-8 -*-
"""حذف استایل‌های inline از فرم‌ها"""

import os
import re

def remove_inline_styles():
    print(" در حال حذف استایل‌های inline...")
    
    # پیدا کردن فایل‌های UI
    ui_files = []
    for root, dirs, files in os.walk('app/ui'):
        for file in files:
            if file.endswith('.py'):
                ui_files.append(os.path.join(root, file))
    
    print(f"📁 {len(ui_files)} فایل پیدا شد")
    
    # الگوهای استایل inline
    patterns_to_remove = [
        # استایل گرادیانت در About
        r"dlg\.setStyleSheet\(\"QDialog\{background:qlineargradient\([^}]+\}\)\"\)",
        
        # استایل‌های رنگی دکمه‌ها
        r"\.setStyleSheet\('QPushButton\{background:#[^}]+\}'\)",
        r"\.setStyleSheet\(\"QPushButton\{background:#[^}]+\}\"",
        
        # استایل‌های inline دیگر
        r"setStyleSheet\(['\"][^)]*background[^)]*['\"]\)",
    ]
    
    files_modified = 0
    
    for filepath in ui_files:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # حذف استایل‌های خاص
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content)
        
        # اصلاح خاص برای فرم About
        if '_show_about' in content:
            # حذف استایل گرادیانت
            content = content.replace(
                "dlg.setStyleSheet(\"QDialog{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0d2a50,stop:1 #123a6d);}\")",
                "dlg.setObjectName('AboutDialog')"
            )
            
            # تغییر objectName برای لیبل‌ها
            content = content.replace(
                "t = QLabel('سیستم انبارداری هوشمند'); t.setStyleSheet('color:#243144;font-size:20px;font-weight:bold;');",
                "t = QLabel('سیستم انبارداری هوشمند'); t.setObjectName('AboutTitle');"
            )
            
            content = content.replace(
                "s.setStyleSheet('color:#f59e0b;font-size:17px;font-weight:bold;')",
                "s.setObjectName('AboutCompany')"
            )
            
            content = content.replace(
                "ver.setStyleSheet('color:#1f6feb;font-size:12px;')",
                "ver.setObjectName('AboutVersion')"
            )
            
            content = content.replace(
                "body.setStyleSheet('color:#5b6b7f;font-size:13px;')",
                "body.setObjectName('AboutBody')"
            )
        
        # اصلاح دکمه‌های فرم رسید
        if 'ReceiptManagerWindow' in content or 'IssueManagerWindow' in content:
            # حذف استایل inline دکمه‌های بالا
            content = re.sub(
                r"top_save\.setStyleSheet\('[^']+'\);",
                "top_save.setObjectName('SuccessButton');",
                content
            )
            content = re.sub(
                r"top_new\.setStyleSheet\('[^']+'\);",
                "top_new.setObjectName('SecondaryButton');",
                content
            )
            content = re.sub(
                r"top_list\.setStyleSheet\('[^']+'\);",
                "top_list.setObjectName('SecondaryButton');",
                content
            )
            
            # حذف استایل تب‌ها
            content = re.sub(
                r"self\.tabs\.setStyleSheet\('[^']+'\)",
                "",
                content
            )
            
            # حذف استایل لیبل‌های قیمت
            content = re.sub(
                r"self\.avg_price_lbl\.setStyleSheet\([^)]+\)",
                "self.avg_price_lbl.setObjectName('AvgPriceLabel')",
                content
            )
            content = re.sub(
                r"self\.avg_price_value\.setStyleSheet\([^)]+\)",
                "self.avg_price_value.setObjectName('AvgPriceValue')",
                content
            )
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            files_modified += 1
            print(f"✅ {filepath}")
    
    print(f"\n✅ {files_modified} فایل اصلاح شد")
    print("\nحالا برنامه را اجرا کنید:")
    print("python main.py")


if __name__ == "__main__":
    remove_inline_styles()