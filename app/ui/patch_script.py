import re
import os

file_path = 'issue_manager_window.py'

if not os.path.exists(file_path):
    print(f"❌ خطا: فایل {file_path} در کنار این اسکریپت یافت نشد!")
    exit(1)

print("🔄 در حال خواندن فایل...")
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# تغییر اول: تبدیل cust_map به self.cust_map در متد _load_lookups
content = re.sub(
    r'([ \t]*)# ساخت نقشه مشتری برای جستجوی سریع\s*\n\s*cust_map = \{\}\s*\n\s*for c in self\.customers:\s*\n\s*cid = c\.get\(\'id\'\)\s*\n\s*if cid:\s*\n\s*cname = "{} {}".format\(c\.get\(\'first_name\',\'\'\), c\.get\(\'last_name\',\'\'\)\)\.strip\(\)\s*\n\s*cust_map\[cid\] = cname',
    r'\1# ساخت نقشه مشتری برای جستجوی سریع\n\1self.cust_map = {}\n\1for c in self.customers:\n\1    cid = c.get(\'id\')\n\1    if cid:\n\1        cname = "{} {}".format(c.get(\'first_name\',\'\'), c.get(\'last_name\',\'\')).strip()\n\1        self.cust_map[cid] = cname',
    content
)

# تغییر دوم: اصلاح نحوه فراخوانی cust_map در همان متد
content = re.sub(
    r'cust_name = cust_map\.get\(cust_id, \'-\'\) if cust_id else \'-\'',
    r'cust_name = self.cust_map.get(cust_id, \'-\') if cust_id else \'-\'',
    content
)

# تغییر سوم: اصلاح فرمت نمایش در متد _refresh_reference_combo
old_loop_pattern = r'([ \t]*)for row in self\.open_references:\s*\n\s*rws = wh_map\.get\(row\[\'id\'\]\)\s*\n\s*if wid and rws and wid not in rws:\s*\n\s*continue\s*\n\s*self\.reference_selector_combo\.addItem\(\s*\n\s*"{} \| مانده: \{:\,\}".format\(row\[\'reference_no\'\], int\(row\[\'remaining_qty\'\]\)\), row\[\'id\'\]\)'

new_loop_code = r'''\1for row in self.open_references:
\1    rws = wh_map.get(row['id'])
\1    if wid and rws and wid not in rws:
\1        continue
\1    
\1    ref_no = row.get('reference_no', 'نامشخص')
\1    cust_id = row.get('customer_id')
\1    remaining = row.get('remaining_qty', 0)
\1    cust_name = self.cust_map.get(cust_id, '-') if cust_id and hasattr(self, 'cust_map') else '-'
\1    
\1    label = "{} | مشتری: {} | مانده: {:,}".format(ref_no, cust_name, int(remaining or 0))
\1    self.reference_selector_combo.addItem(label, row['id'])'''

content = re.sub(old_loop_pattern, new_loop_code, content)

print("💾 در حال ذخیره تغییرات روی فایل...")
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ تغییرات با موفقیت روی فایل issue_manager_window.py اعمال شد!")
print("🎉 اکنون می‌توانید برنامه را اجرا کنید و نام مشتری را در کامبو مرجع مشاهده نمایید.")