# rewrite_upload_helper.py
import os

helper_path = os.path.join('app', 'core', 'doc_upload_helper.py')

print("🔧 در حال بازنویسی کامل doc_upload_helper.py...")

new_code = '''# -*- coding: utf-8 -*-
"""
doc_upload_helper.py - نسخه سالم و بدون خطا
"""
import os
import shutil
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PyQt5.QtCore import QDateTime

def open_upload_after_save(parent, doc_type, saved, db, user_data):
    """
    باز کردن دیالوگ انتخاب عکس و آپلود فایل‌ها
    doc_type: 'ISSUE' یا 'RECEIPT'
    """
    try:
        doc_id = saved.get('id')
        doc_no = saved.get('receipt_no') or saved.get('issue_no') or str(doc_id)
        
        if not doc_id:
            return

        # ۱. پرسش از کاربر
        reply = QMessageBox.question(
            parent, 'آپلود تصاویر', 
            'آیا می‌خواهید تصاویر سند ' + str(doc_no) + ' را آپلود کنید؟ (حداکثر ۳ عکس)',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.No:
            return

        # . انتخاب فایل‌ها با دیالوگ استاندارد ویندوز
        files, _ = QFileDialog.getOpenFileNames(
            parent, 'انتخاب تصاویر', '', 'تصاویر (*.png *.jpg *.jpeg *.bmp)'
        )
        if not files:
            return

        # ۳. ذخیره فایل‌ها در پوشه uploads
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_dir = os.path.join(base_dir, 'data', 'uploads', doc_type.lower(), str(doc_id))
        
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        saved_paths = []
        for f in files[:3]:
            fname = os.path.basename(f)
            ts = QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')
            new_name = str(doc_id) + '_' + ts + '_' + fname
            dest = os.path.join(upload_dir, new_name)
            
            shutil.copy2(f, dest)
            saved_paths.append(os.path.join(doc_type.lower(), str(doc_id), new_name))

        # ۴. ذخیره مسیرها در دیتابیس
        try:
            with db.connect() as conn:
                table = 'warehouse_issues' if doc_type == 'ISSUE' else 'warehouse_receipts'
                
                vals = [None] * 3
                for i, p in enumerate(saved_paths):
                    if i < 3:
                        vals[i] = p
                
                conn.execute(
                    "UPDATE " + table + " SET img_path1=?, img_path2=?, img_path3=? WHERE id=?",
                    vals + [doc_id]
                )
                conn.commit()
        except Exception as db_err:
            print("خطا در ذخیره مسیر در دیتابیس:", db_err)

        QMessageBox.information(parent, 'موفق', str(len(saved_paths)) + ' تصویر با موفقیت آپلود شد.')

    except Exception as e:
        print("خطا در آپلود:", e)
        import traceback
        traceback.print_exc()
'''

try:
    with open(helper_path, 'w', encoding='utf-8') as f:
        f.write(new_code)
    print("✅ فایل با موفقیت بازنویسی شد.")
    print("   حالا برنامه را تست کنید.")
except Exception as e:
    print("❌ خطا:", e)

input("\\n⏎ Enter بزنید...")