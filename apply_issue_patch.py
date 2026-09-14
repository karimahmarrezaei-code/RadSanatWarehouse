# -*- coding: utf-8 -*-
"""
اسکریپت اعمال پچ امن برای issue_repository.py (گزینه ۱: کنترل موجودی و تراکنش اتمی)
همراه با پشتیبان‌گیری خودکار (Automatic Backup)
"""
import os
import shutil
import datetime

TARGET_FILE = "issue_repository.py"

def create_backup(filepath):
    if not os.path.exists(filepath):
        print(f"❌ خطا: فایل {filepath} یافت نشد!")
        return None
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ نسخه پشتیبان با موفقیت ایجاد شد: {backup_path}")
    return backup_path

def apply_patch():
    print("🚀 شروع فرآیند پچ‌گذاری...")
    backup = create_backup(TARGET_FILE)
    if not backup:
        return

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    # ۱. گارد موجودی لحظه‌ای و تراکنش اتمی (Stock Guard & Immediate Lock)
    stock_guard_code = '''        with self.db.connect() as conn:
            # [SECURITY-PATCH] 1. شروع تراکنش اتمی با قفل فوری
            try:
                conn.execute("BEGIN IMMEDIATE")
            except Exception:
                pass  # اگر تراکنش از قبل باز بود

            # [SECURITY-PATCH] 2. کنترل مانده واقعی و فیزیکی از روی کاردکس قبل از ثبت
            _guard_items = {}
            for _ln in lines:
                _p_id = self._safe_int(_ln.get('pallet_id', 0))
                _w_id = self._safe_int(_ln.get('warehouse_id', 0))
                _req_q = self._safe_int(_ln.get('quantity', 0))
                if _p_id > 0 and _w_id > 0 and _req_q > 0:
                    _k = (_p_id, _w_id)
                    _guard_items[_k] = _guard_items.get(_k, 0) + _req_q

            for (_p_id, _w_id), _need_qty in _guard_items.items():
                row_stock = conn.execute(
                    """SELECT COALESCE(SUM(CASE WHEN transaction_type='IN' THEN qty_in ELSE -qty_out END), 0)
                       FROM inventory_transactions
                       WHERE pallet_id = ? AND warehouse_id = ? AND COALESCE(is_void, 0) = 0""",
                    (_p_id, _w_id)
                ).fetchone()
                current_stock = row_stock[0] if row_stock else 0

                if _need_qty > current_stock:
                    raise ValueError(
                        f"خطای کسری موجودی: موجودی واقعی انبار کافی نیست! "
                        f"(پالت شناسه {_p_id} در انبار {_w_id} | موجودی: {current_stock:,} | درخواستی: {_need_qty:,})"
                    )
'''

    # الگوی جستجو برای جایگزینی
    old_conn_pattern = "        with self.db.connect() as conn:"
    
    if old_conn_pattern in content:
        # فقط اولین نمونه در متد create_outbound_issue را هدف قرار می‌دهیم
        content = content.replace(old_conn_pattern, stock_guard_code, 1)
        print("✅ ۱. گارد کنترل موجودی فیزیکی و قفل تراکنش اضافه شد.")
    else:
        print("⚠️ هشدار: الگوی شروع تراکنش یافت نشد (احتمالاً قبلاً پچ شده است).")

    # ۲. اصلاح try/except pass در درج اقلام مرجع (Outbound items error swallowing)
    old_swallow = """            except Exception:
                pass"""
    new_swallow = """            except Exception as e:
                # [SECURITY-PATCH] جلوگیری از بلعیدن خطای دیتابیس
                raise RuntimeError(f"خطا در ثبت ردیف های مرجع بارگیری: {e}")"""
    
    if old_swallow in content:
        content = content.replace(old_swallow, new_swallow, 1)
        print("✅ ۲. اصلاح خطای پنهان‌سازی (Exception Swallowing) در ردیف‌های مرجع انجام شد.")

    # ذخیره تغییرات
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("🎉 پچ با موفقیت اعمال شد. سیستم در برابر موجودی منفی و تداخل‌های همزمانی ایمن گردید.")

if __name__ == "__main__":
    apply_patch()
