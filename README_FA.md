# پروژه مدیریت انبار پالت - فاز اول

این نسخه، شروع ماژولار پروژه بر اساس نیازمندی‌های شماست و فعلاً شامل این بخش‌ها می‌باشد:

- طراحی دیتابیس `SQLite3` با تمرکز روی صحت ساختار و توسعه‌پذیری
- اسکلت اولیه برنامه با `PyQt5`
- فرم لاگین اولیه
- داشبورد ساده با تم تیره
- مدل نقش‌محور کاربران
- ساختار اولیه رسید انبار / حواله خروج / مالی / حسابداری
- پشتیبانی از تاریخ ترکیبی: **ذخیره ISO در دیتابیس + نمایش شمسی در رابط کاربری**

## ساختار پروژه

```text
warehouse_app/
├── app/
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── jalali.py
│   │   ├── locations.py
│   │   ├── security.py
│   │   └── validators.py
│   ├── repositories/
│   │   ├── finance_repository.py
│   │   ├── issue_repository.py
│   │   ├── opening_inventory_repository.py
│   │   ├── pallet_repository.py
│   │   ├── person_repository.py
│   │   ├── receipt_repository.py
│   │   ├── report_repository.py
│   │   ├── treasury_repository.py
│   │   └── warehouse_repository.py
│   ├── reporting/
│   │   └── report_server.py
│   ├── services/
│   │   ├── finance_service.py
│   │   └── report_export_service.py
│   ├── ui/
│   │   ├── checks_window.py
│   │   ├── dashboard_charts.py
│   │   ├── finance_window.py
│   │   ├── issue_window.py
│   │   ├── login_window.py
│   │   ├── reports_window.py
│   │   ├── main_window.py
│   │   ├── pallets_window.py
│   │   ├── persons_window.py
│   │   ├── receipt_window.py
│   │   ├── treasury_window.py
│   │   ├── warehouses_window.py
│   │   └── styles.py
│   └── main.py
├── data/
│   ├── schema.sql
│   ├── seed.sql
│   ├── iran_provinces.json
│   ├── iran_cities.json
│   └── app.db
├── docs/
│   ├── 01_database_blueprint_fa.md
│   ├── 02_pallet_module_fa.md
│   ├── 03_persons_module_fa.md
│   ├── 04_warehouses_module_fa.md
│   ├── 05_receipts_module_fa.md
│   ├── 06_issues_module_fa.md
│   ├── 07_finance_integration_fa.md
│   ├── 08_financial_reports_fa.md
│   ├── 09_checks_management_fa.md
│   ├── 10_stock_value_reports_fa.md
│   ├── 11_stock_report_exports_fa.md
│   ├── 12_kardex_reports_fa.md
│   ├── 13_safe_rollback_fa.md
│   ├── 14_person_statement_exports_fa.md
│   ├── 15_aggregate_warehouses_report_fa.md
│   ├── 16_treasury_management_fa.md
│   ├── 17_financial_summary_exports_fa.md
│   ├── 18_management_dashboard_fa.md
│   ├── 19_dashboard_date_filter_fa.md
│   └── 20_opening_inventory_fa.md
├── init_db.py
└── requirements.txt
```

## راه اندازی

```bash
pip install -r requirements.txt
python init_db.py
python -m app.main
```

## اطلاعات ورود اولیه

- نام کاربری: `admin`
- رمز عبور: `admin123`

> لطفاً بعد از اولین ورود، رمز عبور پیش فرض تغییر داده شود.

## نکات مهم طراحی دیتابیس

### 1) اشخاص به صورت یکپارچه
چون یک شخص می‌تواند هم‌زمان **مشتری**، **تأمین‌کننده** و **راننده** باشد، ساختار به این صورت طراحی شده:

- `persons`
- `person_roles`
- `driver_profiles`
- `bank_accounts`

### 2) کنترل چندمرحله‌ای رسید / خروج
برای اینکه یک بار مثلاً `5000` عددی در چند مرحله `2000 + 1500 + 1500` ثبت شود، ساختار دو لایه در نظر گرفته شده:

- `shipment_orders` → کلید اصلی بار / حواله / مرجع
- `stock_documents` → هر مرحله ثبت واقعی رسید یا خروج
- `stock_document_lines` → ردیف‌های جزئی پالت

به این شکل، شماره مرجع اصلی می‌تواند تا تکمیل بار دوباره فراخوانی شود.

### 3) کنترل ریالی
برای بخش ریالی و تسویه:

- `financial_documents`
- `payment_entries`
- `payment_methods`
- `ledger_accounts`
- `journal_entries`
- `journal_lines`

در این فاز، زیرساخت حسابداری تعبیه شده تا در مراحل بعدی ثبت‌های کامل دوبل و گردش حساب توسعه داده شود.

### 4) هشدار کمبود موجودی
در جدول `pallets` فیلدی با عنوان `low_stock_threshold` در نظر گرفته شده تا هنگام اجرای برنامه، موارد کم‌موجودی در داشبورد نمایش داده شوند.

## پیشنهاد گام بعدی
بهترین ادامه برای فاز بعد:

1. فرم مدیریت پالت‌ها
2. فرم اشخاص + نقش‌ها + حساب بانکی + راننده
3. فرم انبارها
4. فرم رسید انبار با دیتاگراید و شماره‌گذاری
5. پیش‌نمایش چاپی HTML/CSS
6. ثبت مالی و اسناد حسابداری مرتبط

اگر بخواهید، در پیام بعدی من مستقیم می‌روم سراغ **فرم مدیریت پالت‌ها + CRUD کامل + اعتبارسنجی**.


## بروزرسانی فاز دوم

در این مرحله، **ماژول مدیریت پالت‌ها** به برنامه اضافه شده است:

- فرم ثبت / ویرایش / حذف پالت
- جستجو و فیلتر وضعیت
- اعتبارسنجی دقیق ورودی‌ها
- ثبت لاگ تغییرات در `audit_logs`
- اتصال مستقیم از داشبورد به فرم پالت‌ها

### فایل‌های مهم این فاز

- `app/core/validators.py`
- `app/repositories/pallet_repository.py`
- `app/ui/pallets_window.py`
- `docs/02_pallet_module_fa.md`


## بروزرسانی فاز سوم

در این مرحله، **ماژول مدیریت اشخاص** به برنامه اضافه شده است:

- ثبت مشتری، تأمین‌کننده و راننده در یک فرم واحد
- پشتیبانی از چند نقش برای یک شخص
- استان/شهر از JSON ایران
- ثبت چند حساب بانکی و تعیین حساب پیش‌فرض
- ثبت اطلاعات خودرو و پلاک راننده
- جستجو، فیلتر و حذف امن

### فایل‌های مهم این فاز

- `app/core/locations.py`
- `app/repositories/person_repository.py`
- `app/ui/persons_window.py`
- `docs/03_persons_module_fa.md`


## بروزرسانی فاز چهارم

در این مرحله، **ماژول مدیریت انبارها** به برنامه اضافه شده است:

- فرم ثبت / ویرایش / حذف انبار
- جستجو و فیلتر وضعیت
- ظرفیت تعدادی و آدرس
- حذف امن و غیرفعالسازی در صورت وابستگی
- اتصال مستقیم از داشبورد به فرم انبارها

### فایل‌های مهم این فاز

- `app/repositories/warehouse_repository.py`
- `app/ui/warehouses_window.py`
- `docs/04_warehouses_module_fa.md`


## بروزرسانی فاز پنجم

در این مرحله، **ماژول رسید انبار** به برنامه اضافه شده است:

- شماره‌گذاری خودکار مرجع بار با فرمت `WH-تاریخ-0001`
- شماره رسید مرحله‌ای برای بارهای چندمرحله‌ای
- انتخاب تأمین‌کننده، راننده و خودرو
- ثبت ردیف‌های پالت و انبار مقصد
- بروزرسانی موجودی و حرکت انبار
- پیش‌نمایش چاپی HTML رسید

### فایل‌های مهم این فاز

- `app/repositories/receipt_repository.py`
- `app/ui/receipt_window.py`
- `docs/05_receipts_module_fa.md`


## بروزرسانی فاز ششم

در این مرحله، **ماژول حواله خروج** به برنامه اضافه شده است:

- شماره‌گذاری خودکار مرجع خروج با فرمت `EX-تاریخ-0001`
- حواله مرحله‌ای برای بارهای خروج چندمرحله‌ای
- کنترل موجودی قبل از ثبت خروج
- کاهش موجودی و ثبت گردش خروج
- پیش‌نمایش چاپی HTML حواله خروج

### فایل‌های مهم این فاز

- `app/repositories/issue_repository.py`
- `app/ui/issue_window.py`
- `docs/06_issues_module_fa.md`


## بروزرسانی فاز هفتم

در این مرحله، **اتصال مالی به ورود و خروج** اضافه شده است:

- ایجاد خودکار سند مالی از رسید انبار و حواله خروج
- تفکیک سند مالی کالا و کرایه حمل
- ایجاد خودکار سند روزنامه
- پنجره مالی برای مشاهده اسناد و ثبت تسویه

### فایل‌های مهم این فاز

- `app/services/finance_service.py`
- `app/repositories/finance_repository.py`
- `app/ui/finance_window.py`
- `docs/07_finance_integration_fa.md`


## بروزرسانی فاز هشتم

در این مرحله، **گزارشات مالی و گردش حساب اشخاص** اضافه شده است:

- گزارش خلاصه اسناد مالی
- گزارش فیلترشونده اسناد مالی
- گزارش گردش حساب اشخاص
- مانده بدهکار / بستانکار جاری هر شخص

### فایل‌های مهم این فاز

- `app/ui/reports_window.py`
- `docs/08_financial_reports_fa.md`


## بروزرسانی فاز نهم

در این مرحله، **مدیریت چک‌ها و سررسیدها** اضافه شده است:

- ثبت چک به‌عنوان تسویه غیرنقدی
- پنجره مستقل مدیریت چک‌ها
- فیلتر وضعیت و سررسید
- وصول، برگشتی و لغو چک
- تسویه واقعی فقط در زمان وصول چک

### فایل‌های مهم این فاز

- `app/ui/checks_window.py`
- `docs/09_checks_management_fa.md`


## بروزرسانی فاز دهم

در این مرحله، **گزارش موجودی و ارزش ریالی انبار با Flask** اضافه شده است:

- انتخاب انبار از کمبوباکس
- نمایش تعداد کل پالت و ارزش ریالی کل
- محاسبه ورود ریالی و خروج ریالی برای هر پالت
- پیش‌نمایش گریدی گزارش در مرورگر با Flask

### فایل‌های مهم این فاز

- `app/repositories/report_repository.py`
- `app/reporting/report_server.py`
- `app/ui/reports_window.py`
- `docs/10_stock_value_reports_fa.md`


## بروزرسانی فاز یازدهم

در این مرحله، **خروجی Excel / PDF برای گزارش ارزش ریالی انبار** اضافه شده است:

- خروجی Excel از گزارش انبار
- خروجی PDF از همان گزارش
- استفاده از همان داده‌های ارزش ریالی و موجودی

### فایل‌های مهم این فاز

- `app/services/report_export_service.py`
- `app/ui/reports_window.py`
- `docs/11_stock_report_exports_fa.md`


## بروزرسانی فاز دوازدهم

در این مرحله، **گزارش کاردکس کامل پالت و انبار** اضافه شده است:

- انتخاب انبار و پالت از کمبوباکس
- نمایش ریزگردش ورود/خروج با مانده تعدادی و ریالی
- پیش‌نمایش Flask برای کاردکس
- خروجی Excel / PDF برای کاردکس

### فایل‌های مهم این فاز

- `app/repositories/report_repository.py`
- `app/services/report_export_service.py`
- `app/ui/reports_window.py`
- `docs/12_kardex_reports_fa.md`


## بروزرسانی فاز سیزدهم

در این مرحله، **rollback امن اسناد عملیاتی و مالی** اضافه شده است:

- rollback امن رسید انبار
- rollback امن حواله خروج
- ابطال امن سند مالی
- ایجاد گردش معکوس و سند روزنامه معکوس

### فایل‌های مهم این فاز

- `app/repositories/finance_repository.py`
- `app/repositories/receipt_repository.py`
- `app/repositories/issue_repository.py`
- `app/ui/finance_window.py`
- `app/ui/receipt_window.py`
- `app/ui/issue_window.py`
- `docs/13_safe_rollback_fa.md`


## بروزرسانی فاز چهاردهم

در این مرحله، **خروجی Excel / PDF برای گردش حساب اشخاص** اضافه شده است:

- خروجی Excel برای شخص انتخاب‌شده
- خروجی PDF برای شخص انتخاب‌شده
- خلاصه و ریزگردش کامل در فایل خروجی

### فایل‌های مهم این فاز

- `app/services/report_export_service.py`
- `app/ui/reports_window.py`
- `docs/14_person_statement_exports_fa.md`


## بروزرسانی فاز پانزدهم

در این مرحله، **گزارش تجمیعی موجودی و ارزش همه انبارها** اضافه شده است:

- خلاصه کل سیستم
- خلاصه به تفکیک انبار
- خلاصه پالت‌ها در همه انبارها
- پیش‌نمایش Flask و خروجی Excel / PDF

### فایل‌های مهم این فاز

- `app/repositories/report_repository.py`
- `app/services/report_export_service.py`
- `app/ui/reports_window.py`
- `docs/15_aggregate_warehouses_report_fa.md`


## بروزرسانی فاز شانزدهم

در این مرحله، **مدیریت صندوق / بانک تفصیلی** اضافه شده است:

- تعریف صندوق و حساب بانکی شرکت
- ثبت مانده و گردش خزانه
- اتصال تسویه‌های مالی به صندوق / بانک
- کنترل وصول چک روی حساب بانکی انتخاب‌شده

### فایل‌های مهم این فاز

- `app/repositories/treasury_repository.py`
- `app/ui/treasury_window.py`
- `docs/16_treasury_management_fa.md`


## بروزرسانی فاز هفدهم

در این مرحله، **خروجی Excel / PDF برای اسناد مالی خلاصه** اضافه شده است:

- خروجی Excel از گزارش مالی فیلترشده
- خروجی PDF از همان گزارش
- خلاصه دریافتنی/پرداختنی و ریز اسناد مالی در فایل خروجی

### فایل‌های مهم این فاز

- `app/services/report_export_service.py`
- `app/ui/reports_window.py`
- `docs/17_financial_summary_exports_fa.md`


## بروزرسانی فاز هجدهم

در این مرحله، **داشبورد مدیریتی با نمودارها** اضافه شده است:

- نمودار مالی مدیریتی
- نمودار ارزش ریالی انبارها
- نمودار مانده صندوق / بانک
- نمودار روند 7 روز اخیر عملیات

### فایل‌های مهم این فاز

- `app/ui/dashboard_charts.py`
- `app/core/database.py`
- `app/ui/main_window.py`
- `docs/18_management_dashboard_fa.md`


## بروزرسانی فاز نوزدهم

در این مرحله، **فیلتر بازه زمانی برای داشبورد مدیریتی** اضافه شده است:

- انتخاب تاریخ شروع و پایان در بالای داشبورد
- اعمال بازه روی کارت‌های آماری دوره‌ای
- اعمال بازه روی نمودارهای مدیریتی
- دکمه بازگشت سریع به 7 روز اخیر

### فایل‌های مهم این فاز

- `app/core/database.py`
- `app/ui/dashboard_charts.py`
- `app/ui/main_window.py`
- `docs/19_dashboard_date_filter_fa.md`


## بروزرسانی فاز بیستم

در این مرحله، **ماژول افتتاحیه انبار** اضافه شده است:

- ثبت دستی افتتاحیه برای هر انبار
- تعیین تعداد و ارزش ریالی اولیه هر پالت
- ثبت گردش انبار با نوع OPENING
- پیش‌نمایش و ذخیره سند افتتاحیه

### فایل‌های مهم این فاز

- `app/repositories/opening_inventory_repository.py`
- `app/ui/opening_inventory_window.py`
- `docs/20_opening_inventory_fa.md`
