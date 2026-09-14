# check_and_fix_upload.py
import os
import re

def check_and_fix():
    print("=" * 60)
    print("🔍 بررسی سیستم آپلود تصاویر")
    print("=" * 60)
    
    # ۱. بررسی فایل doc_upload_helper.py
    helper_path = os.path.join('app', 'core', 'doc_upload_helper.py')
    print("\n۱. بررسی فایل doc_upload_helper.py...")
    
    if os.path.exists(helper_path):
        with open(helper_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'QFileDialog' in content and 'QMessageBox' in content:
            print("   ✅ فایل سالم است (از QFileDialog استفاده می‌کند)")
        elif 'DocumentUploadDialog' in content:
            print("   ❌ فایل قدیمی است (به DocumentUploadDialog وابسته است)")
            print("    در حال بازنویسی...")
            # اینجا می‌توانید کد بازنویسی را قرار دهید
        else:
            print("   ⚠️  فایل خالی یا نامشخص است")
    else:
        print("   ❌ فایل وجود ندارد!")
    
    # ۲. بررسی فراخوانی در issue_manager_window.py
    print("\n۲. بررسی issue_manager_window.py...")
    issue_path = os.path.join('app', 'ui', 'issue_manager_window.py')
    if os.path.exists(issue_path):
        with open(issue_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'open_upload_after_save' in content and "'ISSUE'" in content:
            print("   ✅ تابع open_upload_after_save فراخوانی شده")
        else:
            print("   ❌ تابع open_upload_after_save فراخوانی نشده!")
            
            # پیدا کردن متد save_issue
            if 'def save_issue' in content:
                print("   💡 راهنمایی: در متد save_issue، بعد از QMessageBox.information این خط را اضافه کنید:")
                print("""
    try:
        from app.core.doc_upload_helper import open_upload_after_save
        open_upload_after_save(self, 'ISSUE', saved, self.db, self.user_data)
    except Exception as _img_exc:
        print('[doc-images] upload error:', _img_exc)
""")
    else:
        print("   ❌ فایل issue_manager_window.py یافت نشد")
    
    # ۳. بررسی فراخوانی در receipt_manager_window.py
    print("\n۳. بررسی receipt_manager_window.py...")
    receipt_path = os.path.join('app', 'ui', 'receipt_manager_window.py')
    if os.path.exists(receipt_path):
        with open(receipt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'open_upload_after_save' in content and "'RECEIPT'" in content:
            print("   ✅ تابع open_upload_after_save فراخوانی شده")
        else:
            print("   ❌ تابع open_upload_after_save فراخوانی نشده!")
            
            # پیدا کردن متد save_receipt
            if 'def save_receipt' in content:
                print("   💡 راهنمایی: در متد save_receipt، بعد از QMessageBox.information این خط را اضافه کنید:")
                print("""
    try:
        from app.core.doc_upload_helper import open_upload_after_save
        open_upload_after_save(self, 'RECEIPT', saved, self.db, self.user_data)
    except Exception as _img_exc:
        print('[doc-images] upload error:', _img_exc)
""")
    else:
        print("   ❌ فایل receipt_manager_window.py یافت نشد")
    
    print("\n" + "=" * 60)
    print("✅ بررسی به پایان رسید")
    print("=" * 60)

if __name__ == "__main__":
    check_and_fix()
    input("\n⏎ Enter بزنید...")