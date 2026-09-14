# final_upload_test.py
import os
import sys

print("=" * 70)
print(" بررسی نهایی - تست import و اجرای تابع")
print("=" * 70)

# ۱. تست import
print("\n. تست import فایل doc_upload_helper...")
try:
    sys.path.insert(0, os.path.abspath('.'))
    from app.core.doc_upload_helper import open_upload_after_save
    print("   ✅ import موفقیت‌آمیز بود")
    print(f"   آدرس تابع: {open_upload_after_save}")
except Exception as e:
    print(f"   ❌ import با خطا مواجه شد: {e}")
    import traceback
    traceback.print_exc()

# ۲. بررسی محتوای فایل
print("\n۲. بررسی محتوای doc_upload_helper.py...")
helper_file = os.path.join('app', 'core', 'doc_upload_helper.py')

if os.path.exists(helper_file):
    with open(helper_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'def open_upload_after_save' in content:
        print("   ✅ تابع در فایل وجود دارد")
        
        # بررسی اندازه تابع
        import re
        func_match = re.search(r'def open_upload_after_save.*?$', content, re.MULTILINE)
        if func_match:
            print("   ✅ تعریف تابع پیدا شد")
        else:
            print("   ❌ تعریف تابع پیدا نشد")
    else:
        print("   ❌ تابع در فایل وجود ندارد")
        
    # بررسی وجود QFileDialog
    if 'QFileDialog' in content:
        print("   ✅ از QFileDialog استفاده می‌کند")
    else:
        print("   ⚠️  از QFileDialog استفاده نمی‌کند (ممکن است قدیمی باشد)")
else:
    print("   ❌ فایل یافت نشد")

print("\n" + "=" * 70)
print("✅ بررسی به پایان رسید")
print("=" * 70)
print("\n💡 اگر import موفق بود اما دیالوگ باز نمی‌شود،")
print("   احتمالاً متد save قبل از رسیدن به آن خط return دارد.")
print("\n   پیشنهاد: در doc_upload_helper.py، در ابتدای تابع این خط را اضافه کنید:")
print("   print('🔍 [DEBUG] open_upload_after_save صدا زده شد!')")

input("\n⏎ Enter بزنید...")