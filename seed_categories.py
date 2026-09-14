import sqlite3

# مسیر دیتابیس خود را اینجا وارد کنید (مثلاً warehouse.db)
DB_PATH = 'warehouse.db' 

categories = [
    ('مواد اولیه', '#ff6384'),
    ('هزینه‌های جاری', '#36a2eb'),
    ('حمل و نقل', '#ffce56'),
    ('تعمیرات و نگهداری', '#4bc0c0'),
    ('حقوق و دستمزد', '#9966ff'),
    ('ملزومات اداری', '#c9cbcf')
]

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for name, color in categories:
        # درج اگر وجود نداشت (برای جلوگیری از تکرار)
        cursor.execute('''
            INSERT OR IGNORE INTO expense_categories (name, color, is_active)
            VALUES (?, ?, 1)
        ''', (name, color))
        
    conn.commit()
    print("✅ دسته‌بندی‌ها با موفقیت اضافه شدند. حالا برنامه را اجرا کنید.")
except Exception as e:
    print(f"❌ خطا: {e}")
finally:
    conn.close()
