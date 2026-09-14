# force_fix_upload.py
import os

helper_path = os.path.join('app', 'core', 'doc_upload_helper.py')

def force_fix():
    print("🔧 در حال جایگزینی فایل doc_upload_helper.py با نسخه سالم...")
    
    # کد نسخه سالم و استاندارد (بدون وابستگی به فایل‌های UI حذف شده)
    new_code = '''# -*- coding: utf-8 -*-
"""
doc_upload_helper.py - نسخه اصلاح شده و مستقل
این ماژول از دیالوگ استاندارد ویندوز برای آپلود استفاده می‌کند.
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
            f'آیا می‌خواهید تصاویر سند {doc_no} را آپلود کنید؟ (حداکثر  عکس)',
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

        # . ذخیره فایل‌ها در پوشه uploads
        # ساخت مسیر: data/uploads/issues/123/image.jpg
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        upload_dir = os.path.join(base_dir, 'data', 'uploads', doc_type.lower(), str(doc_id))
        
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        saved_paths = []
        for f in files[:3]: # محدودیت ۳ عکس
            fname = os.path.basename(f)
            # تغییر نام فایل برای جلوگیری از تداخل (اضافه کردن تایم استمپ)
            ts = QDateTime.currentDateTime().toString('yyyyMMdd_HHmmss')
            new_name = f"{doc_id}_{ts}_{fname}"
            dest = os.path.join(upload_dir, new_name)
            
            shutil.copy2(f, dest)
            # ذخیره مسیر نسبی (برای نمایش بعدی)
            saved_paths.append(os.path.join(doc_type.lower(), str(doc_id), new_name))

        # ۴. ذخیره مسیرها در دیتابیس
        try:
            with db.connect() as conn:
                table = 'warehouse_issues' if doc_type == 'ISSUE' else 'warehouse_receipts'
                
                # آماده‌سازی مقادیر (اگر کمتر از ۳ عکس بود، بقیه None)
                vals = [None] * 3
                for i, p in enumerate(saved_paths):
                    if i < 3:
                        vals[i] = p
                
                # آپدیت رکورد (فرض بر وجود ستون‌های img_path1, img_path2, img_path3)
                conn.execute(
                    f"UPDATE {table} SET img_path1=?, img_path2=?, img_path3=? WHERE id=?",
                    vals + [doc_id]
                )
                conn.commit()
                print(f"✅ مسیر عکس‌ها در دیتابیس ذخیره شد.")
        except Exception as db_err:
            print(f"️ خطا در ذخیره مسیر در دیتابیس (ستون‌ها ممکن است وجود نداشته باشند): {db_err}")
            # نکته مهم: حتی اگر دیتابیس خطا داد، فایل‌ها در پوشه آپلود ذخیره شده‌اند.

        QMessageBox.information(parent, 'موفق', f'{len(saved_paths)} تصویر با موفقیت آپلود و ذخیره شد.')

    except Exception as e:
        print(f"❌ خطا در آپلود: {e}")
        import traceback
        traceback.print_exc()
'''

    try:
        with open(helper_path, 'w', encoding='utf-8') as f:
            f.write(new_code)
        print("✅ فایل doc_upload_helper.py با موفقیت بازنویسی شد.")
        print("   حالا دیالوگ آپلود با استفاده از پنجره استاندارد ویندوز باز می‌شود.")
    except Exception as e:
        print(f"❌ خطا در نوشتن فایل: {e}")

if __name__ == "__main__":
    force_fix()
    input("\n⏎ Enter بزنید...")