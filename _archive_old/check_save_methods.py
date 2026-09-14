# check_save_methods.py
import os
import re

def check_save_methods():
    print("=" * 70)
    print("🔍 بررسی متدهای save_issue و save_receipt")
    print("=" * 70)
    
    # ۱. بررسی issue_manager_window.py
    print("\n۱. بررسی issue_manager_window.py...")
    issue_file = os.path.join('app', 'ui', 'issue_manager_window.py')
    
    if os.path.exists(issue_file):
        with open(issue_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # پیدا کردن متد save_issue
        save_issue_match = re.search(r'def save_issue\(self\).*?(?=\n    def |\Z)', content, re.DOTALL)
        
        if save_issue_match:
            save_issue_code = save_issue_match.group(0)
            print("   ✅ متد save_issue پیدا شد")
            
            if 'open_upload_after_save' in save_issue_code:
                print("   ✅ تابع open_upload_after_save در save_issue فراخوانی شده")
                # نمایش خطوط مربوطه
                lines = save_issue_code.split('\n')
                for i, line in enumerate(lines):
                    if 'open_upload_after_save' in line or 'doc_upload_helper' in line:
                        print(f"      خط {i}: {line.strip()}")
            else:
                print("   ❌ تابع open_upload_after_save در save_issue فراخوانی نشده!")
                print("\n   💡 باید این کد را به انتهای متد save_issue اضافه کنید:")
                print("   " + "=" * 60)
                print("""
    try:
        from app.core.doc_upload_helper import open_upload_after_save
        open_upload_after_save(self, 'ISSUE', saved, self.db, self.user_data)
    except Exception as _img_exc:
        print('[doc-images] upload error:', _img_exc)
                """)
                print("   " + "=" * 60)
        else:
            print("   ❌ متد save_issue پیدا نشد")
    else:
        print("   ❌ فایل issue_manager_window.py یافت نشد")
    
    # ۲. بررسی receipt_manager_window.py
    print("\n. بررسی receipt_manager_window.py...")
    receipt_file = os.path.join('app', 'ui', 'receipt_manager_window.py')
    
    if os.path.exists(receipt_file):
        with open(receipt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # پیدا کردن متد save_receipt
        save_receipt_match = re.search(r'def save_receipt\(self\).*?(?=\n    def |\Z)', content, re.DOTALL)
        
        if save_receipt_match:
            save_receipt_code = save_receipt_match.group(0)
            print("   ✅ متد save_receipt پیدا شد")
            
            if 'open_upload_after_save' in save_receipt_code:
                print("   ✅ تابع open_upload_after_save در save_receipt فراخوانی شده")
                # نمایش خطوط مربوطه
                lines = save_receipt_code.split('\n')
                for i, line in enumerate(lines):
                    if 'open_upload_after_save' in line or 'doc_upload_helper' in line:
                        print(f"      خط {i}: {line.strip()}")
            else:
                print("   ❌ تابع open_upload_after_save در save_receipt فراخوانی نشده!")
                print("\n   💡 باید این کد را به انتهای متد save_receipt اضافه کنید:")
                print("   " + "=" * 60)
                print("""
    try:
        from app.core.doc_upload_helper import open_upload_after_save
        open_upload_after_save(self, 'RECEIPT', saved, self.db, self.user_data)
    except Exception as _img_exc:
        print('[doc-images] upload error:', _img_exc)
                """)
                print("   " + "=" * 60)
        else:
            print("   ❌ متد save_receipt پیدا نشد")
    else:
        print("   ❌ فایل receipt_manager_window.py یافت نشد")
    
    print("\n" + "=" * 70)
    print("✅ بررسی به پایان رسید")
    print("=" * 70)

if __name__ == "__main__":
    check_save_methods()
    input("\n⏎ Enter بزنید...")