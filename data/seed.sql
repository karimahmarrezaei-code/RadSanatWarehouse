INSERT OR IGNORE INTO app_settings (key, value, description) VALUES
('app_name', 'Warehouse Pallet Manager', 'نام برنامه'),
('theme', 'dark', 'تم پیش فرض برنامه'),
('calendar_mode', 'mixed', 'ذخیره میلادی / نمایش شمسی'),
('currency', 'IRR', 'واحد پول');

INSERT OR IGNORE INTO sequences (name, prefix, current_value, width, updated_at) VALUES
('shipment_in_reference', 'GR-', 0, 4, CURRENT_TIMESTAMP),
('shipment_out_reference', 'GI-', 0, 4, CURRENT_TIMESTAMP),
('financial_document', 'FN-', 0, 4, CURRENT_TIMESTAMP),
('journal_entry', 'JE-', 0, 4, CURRENT_TIMESTAMP),
('treasury_account', 'TR-', 0, 4, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO roles (code, name, description, is_system, created_at) VALUES
('ADMIN', 'مدیر سیستم', 'دسترسی کامل به همه بخش ها', 1, CURRENT_TIMESTAMP),
('MANAGER', 'مدیر', 'مدیریت کلی عملیات', 1, CURRENT_TIMESTAMP),
('STOREKEEPER', 'انباردار', 'مدیریت ورود و خروج و موجودی', 1, CURRENT_TIMESTAMP),
('FINANCE', 'مالی', 'مدیریت تسویه و ثبت های مالی', 1, CURRENT_TIMESTAMP),
('OPERATOR', 'اپراتور', 'ثبت اطلاعات روزانه', 1, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO permissions (code, name, module_name, action_name, description, created_at) VALUES
('dashboard.view', 'مشاهده داشبورد', 'dashboard', 'view', 'نمایش صفحه اصلی', CURRENT_TIMESTAMP),
('users.view', 'مشاهده کاربران', 'users', 'view', 'لیست کاربران', CURRENT_TIMESTAMP),
('users.manage', 'مدیریت کاربران', 'users', 'manage', 'ثبت و ویرایش و حذف کاربران', CURRENT_TIMESTAMP),
('roles.manage', 'مدیریت نقش ها', 'roles', 'manage', 'تعریف نقش و دسترسی', CURRENT_TIMESTAMP),
('pallets.view', 'مشاهده پالت ها', 'pallets', 'view', 'لیست پالت ها', CURRENT_TIMESTAMP),
('pallets.manage', 'مدیریت پالت ها', 'pallets', 'manage', 'ثبت و ویرایش پالت', CURRENT_TIMESTAMP),
('persons.view', 'مشاهده اشخاص', 'persons', 'view', 'لیست اشخاص', CURRENT_TIMESTAMP),
('persons.manage', 'مدیریت اشخاص', 'persons', 'manage', 'ثبت و ویرایش اشخاص', CURRENT_TIMESTAMP),
('warehouses.view', 'مشاهده انبارها', 'warehouses', 'view', 'لیست انبارها', CURRENT_TIMESTAMP),
('warehouses.manage', 'مدیریت انبارها', 'warehouses', 'manage', 'ثبت و ویرایش انبارها', CURRENT_TIMESTAMP),
('openings.manage', 'مدیریت افتتاحیه انبار', 'openings', 'manage', 'ثبت و تایید موجودی اولیه انبار', CURRENT_TIMESTAMP),
('receipts.manage', 'مدیریت رسید انبار', 'receipts', 'manage', 'ثبت و تایید رسید انبار', CURRENT_TIMESTAMP),
('issues.manage', 'مدیریت حواله خروج', 'issues', 'manage', 'ثبت و تایید خروج انبار', CURRENT_TIMESTAMP),
('finance.manage', 'مدیریت مالی', 'finance', 'manage', 'ثبت اسناد مالی و تسویه', CURRENT_TIMESTAMP),
('reports.view', 'مشاهده گزارشات', 'reports', 'view', 'گزارشات سیستمی', CURRENT_TIMESTAMP),
('audit.view', 'مشاهده لاگ ها', 'audit', 'view', 'بررسی رویدادها و تغییرات', CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO payment_methods (code, name, description, created_at) VALUES
('CASH', 'نقدی', 'پرداخت یا دریافت نقدی', CURRENT_TIMESTAMP),
('CHECK', 'چکی', 'پرداخت یا دریافت با چک', CURRENT_TIMESTAMP),
('BANK_TRANSFER', 'واریز بانکی', 'انتقال بانکی', CURRENT_TIMESTAMP),
('TRUST', 'امانی', 'ثبت امانی / اعتباری', CURRENT_TIMESTAMP),
('OTHER', 'سایر', 'روش تسویه دیگر', CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
VALUES ('1000', 'دارایی ها', 'ASSET', NULL, 1, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
VALUES ('2000', 'بدهی ها', 'LIABILITY', NULL, 1, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
VALUES ('3000', 'حقوق مالکانه', 'EQUITY', NULL, 1, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
VALUES ('4000', 'درآمد فروش پالت', 'INCOME', NULL, 1, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
VALUES ('5000', 'هزینه حمل و نقل', 'EXPENSE', NULL, 1, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
SELECT '1100', 'صندوق', 'ASSET', id, 1, CURRENT_TIMESTAMP
FROM ledger_accounts WHERE code = '1000';

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
SELECT '1200', 'بانک', 'ASSET', id, 1, CURRENT_TIMESTAMP
FROM ledger_accounts WHERE code = '1000';

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
SELECT '1300', 'موجودی پالت', 'ASSET', id, 1, CURRENT_TIMESTAMP
FROM ledger_accounts WHERE code = '1000';

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
SELECT '2100', 'حساب پرداختنی تامین کنندگان', 'LIABILITY', id, 1, CURRENT_TIMESTAMP
FROM ledger_accounts WHERE code = '2000';

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
SELECT '2200', 'حساب دریافتنی مشتریان', 'ASSET', id, 1, CURRENT_TIMESTAMP
FROM ledger_accounts WHERE code = '1000';

INSERT OR IGNORE INTO ledger_accounts (code, name, account_type, parent_id, is_system, created_at)
SELECT '2300', 'حساب پرداختنی رانندگان', 'LIABILITY', id, 1, CURRENT_TIMESTAMP
FROM ledger_accounts WHERE code = '2000';

INSERT OR IGNORE INTO treasury_accounts (
    code, name, account_type, bank_name, account_number, iban, card_number,
    branch_name, branch_code, opening_balance, current_balance, is_active,
    description, created_at, updated_at
) VALUES
('TR-0001', 'صندوق اصلی', 'CASHBOX', NULL, NULL, NULL, NULL, NULL, NULL, 0, 0, 1, 'صندوق پیش فرض سیستم', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('TR-0002', 'بانک اصلی', 'BANK', 'بانک پیش فرض', NULL, NULL, NULL, NULL, NULL, 0, 0, 1, 'حساب بانکی پیش فرض سیستم', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT OR IGNORE INTO role_permissions (role_id, permission_id, granted_at)
SELECT r.id, p.id, CURRENT_TIMESTAMP
FROM roles r
CROSS JOIN permissions p
WHERE r.code = 'ADMIN';

INSERT OR IGNORE INTO role_permissions (role_id, permission_id, granted_at)
SELECT r.id, p.id, CURRENT_TIMESTAMP
FROM roles r
JOIN permissions p ON p.code IN (
    'dashboard.view', 'pallets.view', 'pallets.manage', 'persons.view', 'persons.manage',
    'warehouses.view', 'warehouses.manage', 'openings.manage', 'receipts.manage', 'issues.manage', 'reports.view'
)
WHERE r.code = 'STOREKEEPER';

INSERT OR IGNORE INTO role_permissions (role_id, permission_id, granted_at)
SELECT r.id, p.id, CURRENT_TIMESTAMP
FROM roles r
JOIN permissions p ON p.code IN (
    'dashboard.view', 'finance.manage', 'reports.view'
)
WHERE r.code = 'FINANCE';

INSERT OR IGNORE INTO role_permissions (role_id, permission_id, granted_at)
SELECT r.id, p.id, CURRENT_TIMESTAMP
FROM roles r
JOIN permissions p ON p.code IN (
    'dashboard.view', 'pallets.view', 'persons.view', 'warehouses.view',
    'openings.manage', 'receipts.manage', 'issues.manage'
)
WHERE r.code = 'OPERATOR';
