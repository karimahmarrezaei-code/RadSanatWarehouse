CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);
CREATE TABLE IF NOT EXISTS sequences (
    name TEXT PRIMARY KEY,
    prefix TEXT NOT NULL,
    current_value INTEGER NOT NULL DEFAULT 0 CHECK (current_value >= 0),
    width INTEGER NOT NULL DEFAULT 4 CHECK (width >= 1),
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    module_name TEXT NOT NULL,
    action_name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    granted_at TEXT NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    mobile TEXT,
    email TEXT,
    role_id INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    last_login_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    entity_name TEXT NOT NULL,
    entity_id TEXT,
    action_name TEXT NOT NULL,
    old_values_json TEXT,
    new_values_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS pallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    material_type TEXT NOT NULL,
    length_cm INTEGER NOT NULL CHECK (length_cm > 0),
    width_cm INTEGER NOT NULL CHECK (width_cm > 0),
    height_cm INTEGER NOT NULL CHECK (height_cm > 0),
    opening_stock INTEGER NOT NULL DEFAULT 0 CHECK (opening_stock >= 0),
    low_stock_threshold INTEGER NOT NULL DEFAULT 0 CHECK (low_stock_threshold >= 0),
    image_path TEXT,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS warehouses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    capacity_count INTEGER NOT NULL DEFAULT 0 CHECK (capacity_count >= 0),
    address TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS inventory_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pallet_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    UNIQUE (pallet_id, warehouse_id),
    FOREIGN KEY (pallet_id) REFERENCES pallets(id) ON DELETE CASCADE,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    national_id TEXT UNIQUE,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    mobile TEXT,
    email TEXT,
    province_code INTEGER,
    province_name TEXT,
    city_code INTEGER,
    city_name TEXT,
    address TEXT,
    notes TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT
, role TEXT DEFAULT 'CUSTOMER', bank_name TEXT, account_number TEXT, iban TEXT);
CREATE TABLE IF NOT EXISTS person_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    role_type TEXT NOT NULL CHECK (role_type IN ('CUSTOMER', 'SUPPLIER', 'DRIVER')),
    created_at TEXT NOT NULL,
    UNIQUE (person_id, role_type),
    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS driver_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL UNIQUE,
    vehicle_type TEXT NOT NULL CHECK (vehicle_type IN ('سواری', 'وانت', 'خاور', 'کامیون سبک', 'کامیون سنگین', 'تریلی', 'کفی 12 متری')),
    vehicle_plate TEXT NOT NULL,
    notes TEXT,
    updated_at TEXT,
    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER NOT NULL,
    bank_name TEXT NOT NULL,
    account_number TEXT,
    iban TEXT,
    card_number TEXT,
    branch_name TEXT,
    branch_code TEXT,
    is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS shipment_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_no TEXT NOT NULL UNIQUE,
    direction TEXT NOT NULL CHECK (direction IN ('IN', 'OUT')),
    waybill_no TEXT,
    party_person_id INTEGER,
    party_role_hint TEXT CHECK (party_role_hint IN ('CUSTOMER', 'SUPPLIER', 'DRIVER', 'OTHER')),
    source_location TEXT,
    destination_location TEXT,
    driver_person_id INTEGER,
    vehicle_type_snapshot TEXT,
    vehicle_plate_snapshot TEXT,
    declared_total_qty INTEGER NOT NULL DEFAULT 0 CHECK (declared_total_qty >= 0),
    processed_total_qty INTEGER NOT NULL DEFAULT 0 CHECK (processed_total_qty >= 0),
    quantity_status TEXT NOT NULL DEFAULT 'OPEN' CHECK (quantity_status IN ('OPEN', 'PARTIAL', 'COMPLETE')),
    expected_total_amount INTEGER NOT NULL DEFAULT 0 CHECK (expected_total_amount >= 0),
    settled_total_amount INTEGER NOT NULL DEFAULT 0 CHECK (settled_total_amount >= 0),
    financial_status TEXT NOT NULL DEFAULT 'OPEN' CHECK (financial_status IN ('OPEN', 'PARTIAL', 'SETTLED')),
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT,
    created_by INTEGER,
    FOREIGN KEY (party_person_id) REFERENCES persons(id) ON DELETE SET NULL,
    FOREIGN KEY (driver_person_id) REFERENCES persons(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS stock_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_order_id INTEGER NOT NULL,
    stage_no INTEGER NOT NULL CHECK (stage_no >= 1),
    document_no TEXT NOT NULL UNIQUE,
    direction TEXT NOT NULL CHECK (direction IN ('IN', 'OUT')),
    operation_date TEXT NOT NULL,
    daily_jalali_label TEXT,
    stage_declared_qty INTEGER NOT NULL DEFAULT 0 CHECK (stage_declared_qty >= 0),
    stage_received_qty INTEGER NOT NULL DEFAULT 0 CHECK (stage_received_qty >= 0),
    discrepancy_qty INTEGER NOT NULL DEFAULT 0,
    freight_amount INTEGER NOT NULL DEFAULT 0 CHECK (freight_amount >= 0),
    destination_location TEXT,
    notes TEXT,
    physical_receipt_html TEXT,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')),
    printed_at TEXT,
    confirmed_at TEXT,
    confirmed_by INTEGER,
    created_at TEXT NOT NULL,
    created_by INTEGER,
    UNIQUE (shipment_order_id, stage_no),
    FOREIGN KEY (shipment_order_id) REFERENCES shipment_orders(id) ON DELETE CASCADE,
    FOREIGN KEY (confirmed_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS stock_document_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_document_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL CHECK (line_no >= 1),
    pallet_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price INTEGER NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    line_total_amount INTEGER NOT NULL DEFAULT 0 CHECK (line_total_amount >= 0),
    warehouse_id INTEGER NOT NULL,
    defect_notes TEXT,
    notes TEXT,
    UNIQUE (stock_document_id, line_no),
    FOREIGN KEY (stock_document_id) REFERENCES stock_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (pallet_id) REFERENCES pallets(id) ON DELETE RESTRICT,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS stock_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movement_date TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('IN', 'OUT')),
    pallet_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    quantity_delta INTEGER NOT NULL,
    unit_price INTEGER NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    line_total_amount INTEGER NOT NULL DEFAULT 0 CHECK (line_total_amount >= 0),
    source_document_line_id INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY (pallet_id) REFERENCES pallets(id) ON DELETE RESTRICT,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE RESTRICT,
    FOREIGN KEY (source_document_line_id) REFERENCES stock_document_lines(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS payment_methods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS financial_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finance_no TEXT NOT NULL UNIQUE,
    operation_type TEXT NOT NULL CHECK (operation_type IN ('INBOUND_RECEIPT', 'INBOUND_FREIGHT', 'OUTBOUND_ISSUE', 'OUTBOUND_FREIGHT', 'PAYROLL', 'EXPENSE')),
    direction TEXT NOT NULL CHECK (direction IN ('RECEIVABLE', 'PAYABLE')),
    inbound_load_id INTEGER,
    outbound_load_id INTEGER,
    receipt_id INTEGER,
    issue_id INTEGER,
    counterparty_person_id INTEGER,
    finance_date TEXT NOT NULL,
    total_amount INTEGER NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    settled_amount INTEGER NOT NULL DEFAULT 0 CHECK (settled_amount >= 0),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'PARTIAL', 'SETTLED', 'CANCELLED')),
    description TEXT,
    created_at TEXT NOT NULL,
    created_by INTEGER, vehicle_no TEXT, cancel_reason TEXT,
    FOREIGN KEY (inbound_load_id) REFERENCES inbound_loads(id) ON DELETE SET NULL,
    FOREIGN KEY (outbound_load_id) REFERENCES outbound_loads(id) ON DELETE SET NULL,
    FOREIGN KEY (receipt_id) REFERENCES warehouse_receipts(id) ON DELETE SET NULL,
    FOREIGN KEY (issue_id) REFERENCES warehouse_issues(id) ON DELETE SET NULL,
    FOREIGN KEY (counterparty_person_id) REFERENCES persons(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS treasury_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL CHECK (account_type IN ('CASHBOX', 'BANK')),
    bank_name TEXT,
    account_number TEXT,
    iban TEXT,
    card_number TEXT,
    branch_name TEXT,
    branch_code TEXT,
    opening_balance INTEGER NOT NULL DEFAULT 0,
    current_balance INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS ledger_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL CHECK (account_type IN ('ASSET', 'LIABILITY', 'EQUITY', 'INCOME', 'EXPENSE')),
    parent_id INTEGER,
    is_system INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES ledger_accounts(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS journal_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_no TEXT NOT NULL UNIQUE,
    entry_date TEXT NOT NULL,
    reference_type TEXT,
    reference_id INTEGER,
    description TEXT,
    created_at TEXT NOT NULL,
    created_by INTEGER,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS journal_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_entry_id INTEGER NOT NULL,
    line_no INTEGER NOT NULL CHECK (line_no >= 1),
    account_id INTEGER NOT NULL,
    person_id INTEGER,
    bank_account_id INTEGER,
    debit_amount INTEGER NOT NULL DEFAULT 0 CHECK (debit_amount >= 0),
    credit_amount INTEGER NOT NULL DEFAULT 0 CHECK (credit_amount >= 0),
    description TEXT,
    UNIQUE (journal_entry_id, line_no),
    CHECK (debit_amount = 0 OR credit_amount = 0),
    FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
    FOREIGN KEY (account_id) REFERENCES ledger_accounts(id) ON DELETE RESTRICT,
    FOREIGN KEY (person_id) REFERENCES persons(id) ON DELETE SET NULL,
    FOREIGN KEY (bank_account_id) REFERENCES bank_accounts(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS inbound_loads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_no TEXT NOT NULL UNIQUE,
    waybill_no TEXT,
    supplier_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    vehicle_type TEXT,
    vehicle_plate TEXT,
    source_location TEXT,
    destination_location TEXT,
    total_load_qty INTEGER NOT NULL CHECK (total_load_qty > 0),
    received_qty_total INTEGER NOT NULL DEFAULT 0 CHECK (received_qty_total >= 0),
    remaining_qty INTEGER NOT NULL DEFAULT 0 CHECK (remaining_qty >= 0),
    load_status TEXT NOT NULL DEFAULT 'OPEN' CHECK (load_status IN ('OPEN', 'PARTIAL', 'COMPLETE', 'CANCELLED')),
    description TEXT,
    register_date TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (supplier_id) REFERENCES persons(id) ON DELETE RESTRICT,
    FOREIGN KEY (driver_id) REFERENCES persons(id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS outbound_loads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_no TEXT NOT NULL UNIQUE,
    waybill_no TEXT,
    customer_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    vehicle_type TEXT,
    vehicle_plate TEXT,
    source_location TEXT,
    destination_location TEXT,
    total_load_qty INTEGER NOT NULL CHECK (total_load_qty > 0),
    issued_qty_total INTEGER NOT NULL DEFAULT 0 CHECK (issued_qty_total >= 0),
    remaining_qty INTEGER NOT NULL DEFAULT 0 CHECK (remaining_qty >= 0),
    load_status TEXT NOT NULL DEFAULT 'OPEN' CHECK (load_status IN ('OPEN', 'PARTIAL', 'COMPLETE', 'CANCELLED')),
    description TEXT,
    register_date TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)), warehouse_id INTEGER,
    FOREIGN KEY (customer_id) REFERENCES persons(id) ON DELETE RESTRICT,
    FOREIGN KEY (driver_id) REFERENCES persons(id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS warehouse_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outbound_load_id INTEGER NOT NULL,
    issue_no TEXT NOT NULL UNIQUE,
    stage_no INTEGER NOT NULL CHECK (stage_no >= 1),
    issue_date TEXT NOT NULL,
    jalali_date_text TEXT,
    waybill_no TEXT,
    customer_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    vehicle_type TEXT,
    vehicle_plate TEXT,
    stage_load_qty INTEGER NOT NULL CHECK (stage_load_qty > 0),
    delivered_qty INTEGER NOT NULL CHECK (delivered_qty > 0),
    discrepancy_qty INTEGER NOT NULL,
    freight_amount INTEGER NOT NULL DEFAULT 0 CHECK (freight_amount >= 0),
    source_location TEXT,
    destination_location TEXT,
    warehouse_keeper_name TEXT,
    receiver_name TEXT,
    issue_status TEXT NOT NULL DEFAULT 'CONFIRMED' CHECK (issue_status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')),
    description TEXT,
    print_html TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL, total_qty INTEGER DEFAULT 0, vat_amount INTEGER NOT NULL DEFAULT 0, extra_costs INTEGER NOT NULL DEFAULT 0, cancel_reason TEXT,
    UNIQUE (outbound_load_id, stage_no),
    FOREIGN KEY (outbound_load_id) REFERENCES outbound_loads(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES persons(id) ON DELETE RESTRICT,
    FOREIGN KEY (driver_id) REFERENCES persons(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS warehouse_issue_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id INTEGER NOT NULL,
    row_no INTEGER NOT NULL CHECK (row_no >= 1),
    pallet_id INTEGER NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    unit_price INTEGER NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    total_price INTEGER NOT NULL DEFAULT 0 CHECK (total_price >= 0),
    warehouse_id INTEGER NOT NULL,
    defect_description TEXT,
    description TEXT,
    UNIQUE (issue_id, row_no),
    FOREIGN KEY (issue_id) REFERENCES warehouse_issues(id) ON DELETE CASCADE,
    FOREIGN KEY (pallet_id) REFERENCES pallets(id) ON DELETE RESTRICT,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS opening_inventory_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opening_no TEXT NOT NULL UNIQUE,
    opening_date TEXT NOT NULL,
    jalali_date_text TEXT,
    warehouse_id INTEGER NOT NULL,
    document_status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (document_status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')),
    total_types_count INTEGER NOT NULL DEFAULT 0 CHECK (total_types_count >= 0),
    total_qty INTEGER NOT NULL DEFAULT 0 CHECK (total_qty >= 0),
    total_amount INTEGER NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    description TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    confirmed_by INTEGER,
    confirmed_at TEXT,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (confirmed_by) REFERENCES users(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS opening_inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    opening_document_id INTEGER NOT NULL,
    row_no INTEGER NOT NULL CHECK (row_no >= 1),
    pallet_id INTEGER NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    unit_price INTEGER NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    total_price INTEGER NOT NULL DEFAULT 0 CHECK (total_price >= 0),
    description TEXT,
    UNIQUE (opening_document_id, row_no),
    FOREIGN KEY (opening_document_id) REFERENCES opening_inventory_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (pallet_id) REFERENCES pallets(id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS company_profile (
    id INTEGER PRIMARY KEY DEFAULT 1,
    
    company_name TEXT,
    show_company_name INTEGER DEFAULT 1,
    
    ceo_name TEXT,
    show_ceo_name INTEGER DEFAULT 1,
    
    national_id TEXT,
    show_national_id INTEGER DEFAULT 1,
    
    economic_code TEXT,
    show_economic_code INTEGER DEFAULT 1,
    
    registration_number TEXT,
    show_registration_number INTEGER DEFAULT 1,
    
    phone TEXT,
    show_phone INTEGER DEFAULT 1,
    
    mobile TEXT,
    show_mobile INTEGER DEFAULT 1,
    
    email TEXT,
    show_email INTEGER DEFAULT 1,
    
    website TEXT,
    show_website INTEGER DEFAULT 1,
    
    address TEXT,
    show_address INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS expense_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                color TEXT DEFAULT '#2563eb',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date DATE NOT NULL,
                category_id INTEGER NOT NULL,
                description TEXT,
                amount INTEGER NOT NULL,
                paid_amount INTEGER DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                reference_doc_id INTEGER,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expense_no TEXT, paid_from_account_id INTEGER, quantity INTEGER DEFAULT 1, consumable_item_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES expense_categories(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            );
CREATE TABLE IF NOT EXISTS box_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_code TEXT UNIQUE NOT NULL,
                length_cm REAL NOT NULL,
                width_cm REAL NOT NULL,
                height_cm REAL NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                cost_price INTEGER NOT NULL,
                wood_type TEXT,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            , warehouse_id INTEGER);
CREATE TABLE IF NOT EXISTS box_production (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_code TEXT UNIQUE NOT NULL,
                length_cm REAL NOT NULL,
                width_cm REAL NOT NULL,
                height_cm REAL NOT NULL,
                quantity INTEGER NOT NULL,
                materials_cost INTEGER NOT NULL,
                labor_cost INTEGER NOT NULL,
                total_cost INTEGER NOT NULL,
                wood_type TEXT,
                user_id INTEGER,
                production_date DATE NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            , warehouse_id INTEGER);
CREATE TABLE IF NOT EXISTS box_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_no TEXT UNIQUE NOT NULL,
                customer_id INTEGER NOT NULL,
                sale_date DATE NOT NULL,
                total_amount INTEGER NOT NULL,
                paid_amount INTEGER DEFAULT 0,
                status TEXT DEFAULT 'OPEN',
                notes TEXT,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES persons(id)
            );
CREATE TABLE IF NOT EXISTS "box_sale_items_old" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                box_code TEXT NOT NULL,
                length_cm REAL NOT NULL,
                width_cm REAL NOT NULL,
                height_cm REAL NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price INTEGER NOT NULL,
                total_price INTEGER NOT NULL, sale_doc_id INTEGER, row_no INTEGER, part_name TEXT, count INTEGER, thickness_cm REAL,
                FOREIGN KEY (sale_id) REFERENCES box_sales(id),
                FOREIGN KEY (box_code) REFERENCES box_inventory(box_code)
            );
CREATE TABLE IF NOT EXISTS stock_takes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_take_no TEXT UNIQUE NOT NULL,
                take_date DATE NOT NULL,
                total_system_qty INTEGER DEFAULT 0,
                total_actual_qty INTEGER DEFAULT 0,
                total_difference INTEGER DEFAULT 0,
                total_value_loss INTEGER DEFAULT 0,
                status TEXT DEFAULT 'DRAFT' 
                    CHECK(status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED')),
                user_id INTEGER,
                approver_id INTEGER,
                approval_date DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
CREATE TABLE IF NOT EXISTS stock_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adjustment_no TEXT UNIQUE NOT NULL,
                pallet_id INTEGER NOT NULL,
                adjustment_type TEXT NOT NULL 
                    CHECK(adjustment_type IN ('IN', 'OUT')),
                quantity INTEGER NOT NULL,
                unit_price INTEGER DEFAULT 0,
                total_value INTEGER DEFAULT 0,
                reason TEXT,
                reference_stock_take_id INTEGER,
                adjustment_date DATE NOT NULL,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (pallet_id) REFERENCES pallets(id),
                FOREIGN KEY (reference_stock_take_id) REFERENCES stock_takes(id)
            );
CREATE TABLE IF NOT EXISTS box_material_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                material_type TEXT NOT NULL,
                price_per_unit INTEGER NOT NULL,
                unit TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, material_type)
            );
CREATE TABLE IF NOT EXISTS cash_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,           -- نام حساب (صندوق اصلی، بانک ملی)
    type TEXT NOT NULL CHECK(type IN ('CASH', 'BANK')),  -- نوع: CASH یا BANK
    account_number TEXT,                 -- شماره حساب (اختیاری)
    bank_name TEXT,                      -- نام بانک (اختیاری)
    balance REAL DEFAULT 0,             -- موجودی فعلی
    description TEXT,                    -- توضیحات
    is_active INTEGER DEFAULT 1,        -- فعال/غیرفعال
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cash_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date DATE NOT NULL,
    transaction_type TEXT NOT NULL CHECK(transaction_type IN 
        ('INCOME', 'EXPENSE', 'TRANSFER_OUT', 'TRANSFER_IN')),
    amount REAL NOT NULL,
    from_account_id INTEGER,             -- حساب مبدأ (برای خروجی و انتقال)
    to_account_id INTEGER,               -- حساب مقصد (برای ورودی و انتقال)
    reference_type TEXT,                 -- نوع مرجع: EXPENSE, INCOME, TRANSFER
    reference_id INTEGER,                -- شناسه رکورد مرجع
    description TEXT,                    -- توضیحات
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_account_id) REFERENCES cash_accounts(id),
    FOREIGN KEY (to_account_id) REFERENCES cash_accounts(id)
);
CREATE TABLE IF NOT EXISTS "stock_take_items" (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_take_id INTEGER NOT NULL,
        pallet_id INTEGER NOT NULL,
        system_qty INTEGER NOT NULL,
        actual_qty INTEGER NOT NULL,
        difference INTEGER NOT NULL,
        unit_price INTEGER DEFAULT 0,
        total_value_diff INTEGER DEFAULT 0,
        reason TEXT,
        status TEXT DEFAULT 'COUNTED'
            CHECK(status IN ('COUNTED', 'REVIEWED', 'APPROVED', 'REJECTED', 'PENDING')),
        FOREIGN KEY (stock_take_id) REFERENCES stock_takes(id),
        FOREIGN KEY (pallet_id) REFERENCES pallets(id)
    );
CREATE TABLE IF NOT EXISTS "payment_entries" (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        financial_document_id INTEGER NOT NULL,
        payment_method_id INTEGER NOT NULL,
        payer_payee_person_id INTEGER,
        bank_account_id INTEGER,
        treasury_account_id INTEGER,
        amount INTEGER NOT NULL,
        due_date TEXT,
        check_no TEXT,
        check_serial TEXT,
        check_bank_name TEXT,
        check_branch_name TEXT,
        status TEXT DEFAULT 'PENDING',
        description TEXT,
        created_at TEXT,
        FOREIGN KEY (financial_document_id) REFERENCES financial_documents(id),
        FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id)
    );
CREATE TABLE IF NOT EXISTS proforma_invoices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        proforma_no TEXT UNIQUE NOT NULL,
                        proforma_date TEXT NOT NULL,
                        customer_id INTEGER,
                        validity_days INTEGER DEFAULT 30,
                        total_amount INTEGER DEFAULT 0,
                        description TEXT,
                        status TEXT DEFAULT 'DRAFT',
                        created_by INTEGER,
                        created_at TEXT
                    , outbound_load_id INTEGER, vat_exempt INTEGER DEFAULT 0, vat_amount INTEGER DEFAULT 0, total_with_vat INTEGER DEFAULT 0, warehouse_id INTEGER);
CREATE TABLE IF NOT EXISTS proforma_invoice_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        proforma_id INTEGER NOT NULL,
                        row_no INTEGER NOT NULL,
                        pallet_id INTEGER,
                        quantity INTEGER DEFAULT 0,
                        unit_price INTEGER DEFAULT 0,
                        total_amount INTEGER DEFAULT 0,
                        note TEXT,
                        FOREIGN KEY (proforma_id) REFERENCES proforma_invoices(id)
                    );
CREATE TABLE IF NOT EXISTS outbound_load_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outbound_load_id INTEGER NOT NULL,
    row_no INTEGER NOT NULL CHECK (row_no >= 1),
    pallet_id INTEGER NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    unit_price INTEGER NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    total_price INTEGER NOT NULL DEFAULT 0 CHECK (total_price >= 0),
    notes TEXT,
    UNIQUE (outbound_load_id, row_no),
    FOREIGN KEY (outbound_load_id) REFERENCES outbound_loads(id) ON DELETE CASCADE,
    FOREIGN KEY (pallet_id) REFERENCES pallets(id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS return_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        financial_document_id INTEGER NOT NULL,
                        smart_no TEXT NOT NULL,
                        return_type TEXT NOT NULL,           -- 'RECEIPT' یا 'ISSUE'
                        source_doc_id INTEGER NOT NULL,      -- شناسه سند مبدأ
                        source_doc_no TEXT,                  -- شماره سند مبدأ
                        row_no INTEGER NOT NULL,
                        pallet_id INTEGER NOT NULL,
                        pallet_code TEXT,
                        pallet_name TEXT,
                        qty INTEGER NOT NULL,
                        unit_price INTEGER NOT NULL DEFAULT 0,
                        total_price INTEGER NOT NULL DEFAULT 0,
                        warehouse_id INTEGER,
                        warehouse_name TEXT,
                        reason TEXT,
                        return_date TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (financial_document_id) REFERENCES financial_documents(id) ON DELETE CASCADE
                    );
CREATE TABLE IF NOT EXISTS accounts (
          id                INTEGER PRIMARY KEY AUTOINCREMENT,
          code              TEXT    NOT NULL UNIQUE,
          name              TEXT    NOT NULL,
          account_type      TEXT    NOT NULL CHECK(account_type IN ('CASHBOX','BANK')),
          bank_name         TEXT,
          account_number    TEXT,
          iban              TEXT,
          card_number       TEXT,
          branch_name       TEXT,
          branch_code       TEXT,
          opening_balance   INTEGER NOT NULL DEFAULT 0,
          current_balance   INTEGER NOT NULL DEFAULT 0,
          is_active         INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
          description       TEXT,
          created_at        TEXT    NOT NULL,
          updated_at        TEXT
        );
CREATE TABLE IF NOT EXISTS document_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT NOT NULL,           -- RECEIPT / ISSUE / PROFORMA / OTHER
            doc_id INTEGER NOT NULL,          -- شناسه سند
            person_id INTEGER,                -- مشتری/تامین‌کننده
            file_path TEXT NOT NULL,          -- مسیر فایل (مطلق یا نسبی)
            original_name TEXT,               -- نام اصلی فایل
            uploaded_at TEXT NOT NULL,
            uploaded_by INTEGER
        );
CREATE TABLE IF NOT EXISTS "treasury_transactions" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                treasury_account_id INTEGER NOT NULL,
                transaction_date TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                source_type TEXT,
                source_id INTEGER,
                amount INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                description TEXT,
                created_at TEXT,
                FOREIGN KEY (treasury_account_id) REFERENCES treasury_accounts(id)
            );
CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT
        );
CREATE TABLE IF NOT EXISTS consumable_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            unit_id INTEGER,
            warehouse_id INTEGER,
            opening_qty INTEGER DEFAULT 0,
            current_qty INTEGER DEFAULT 0,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        );
CREATE TABLE IF NOT EXISTS "inventory_transactions" (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_date DATE NOT NULL,
        transaction_type TEXT NOT NULL CHECK(transaction_type IN ('IN', 'OUT')),
        reference_type TEXT NOT NULL ,
        reference_id INTEGER,
        pallet_id INTEGER NOT NULL,
        warehouse_id INTEGER NOT NULL,
        qty_in INTEGER DEFAULT 0,
        qty_out INTEGER DEFAULT 0,
        unit_price REAL DEFAULT 0,
        total_price REAL DEFAULT 0,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, is_void INTEGER DEFAULT 0,
        FOREIGN KEY (pallet_id) REFERENCES pallets(id),
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(id)
    );
CREATE TABLE IF NOT EXISTS pallet_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_no TEXT, transfer_date TEXT,
                from_warehouse_id INTEGER, to_warehouse_id INTEGER,
                description TEXT, created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS pallet_transfer_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transfer_id INTEGER, pallet_id INTEGER, qty INTEGER, unit_price INTEGER NOT NULL DEFAULT 0, total_price INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS checkbook_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_no TEXT, sayyad_no TEXT, bank_name TEXT, branch TEXT,
                amount INTEGER NOT NULL DEFAULT 0,
                issue_date TEXT, due_date TEXT,
                issuer_person_id INTEGER,
                direction TEXT NOT NULL DEFAULT 'RECEIVED',
                status TEXT NOT NULL DEFAULT 'IN_HAND',
                source_type TEXT, source_id INTEGER,
                created_at TEXT, created_by INTEGER);
CREATE TABLE IF NOT EXISTS checkbook_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_id INTEGER NOT NULL,
                move_type TEXT NOT NULL,
                move_date TEXT,
                from_person_id INTEGER, to_person_id INTEGER,
                ref_type TEXT, ref_id INTEGER,
                amount INTEGER, note TEXT,
                created_at TEXT, created_by INTEGER);
CREATE TABLE IF NOT EXISTS fiscal_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                start_date TEXT NOT NULL, end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN','CLOSED')),
                created_by INTEGER, created_at TEXT,
                closed_by INTEGER, closed_at TEXT);
CREATE TABLE IF NOT EXISTS bank_reconciliations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                treasury_account_id INTEGER NOT NULL,
                statement_date TEXT,
                book_balance INTEGER, statement_balance INTEGER, difference INTEGER,
                note TEXT, created_at TEXT, created_by INTEGER);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_pallets_name ON pallets(name);
CREATE INDEX IF NOT EXISTS idx_persons_national_id ON persons(national_id);
CREATE INDEX IF NOT EXISTS idx_persons_mobile ON persons(mobile);
CREATE INDEX IF NOT EXISTS idx_person_roles_person_id ON person_roles(person_id);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_person_id ON bank_accounts(person_id);
CREATE INDEX IF NOT EXISTS idx_inventory_levels_lookup ON inventory_levels(pallet_id, warehouse_id);
CREATE INDEX IF NOT EXISTS idx_shipment_orders_direction_status ON shipment_orders(direction, quantity_status, financial_status);
CREATE INDEX IF NOT EXISTS idx_stock_documents_shipment_order_id ON stock_documents(shipment_order_id);
CREATE INDEX IF NOT EXISTS idx_stock_document_lines_doc_id ON stock_document_lines(stock_document_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_lookup ON stock_movements(pallet_id, warehouse_id, movement_date);
CREATE INDEX IF NOT EXISTS idx_financial_documents_inbound_load_id ON financial_documents(inbound_load_id);
CREATE INDEX IF NOT EXISTS idx_financial_documents_outbound_load_id ON financial_documents(outbound_load_id);
CREATE INDEX IF NOT EXISTS idx_financial_documents_receipt_id ON financial_documents(receipt_id);
CREATE INDEX IF NOT EXISTS idx_financial_documents_issue_id ON financial_documents(issue_id);
CREATE INDEX IF NOT EXISTS idx_financial_documents_status_direction ON financial_documents(status, direction);
CREATE INDEX IF NOT EXISTS idx_treasury_accounts_code ON treasury_accounts(code);
CREATE INDEX IF NOT EXISTS idx_journal_lines_journal_entry_id ON journal_lines(journal_entry_id);
CREATE INDEX IF NOT EXISTS idx_inbound_loads_reference_no ON inbound_loads(reference_no);
CREATE INDEX IF NOT EXISTS idx_inbound_loads_status ON inbound_loads(load_status, is_active);
CREATE INDEX IF NOT EXISTS idx_outbound_loads_reference_no ON outbound_loads(reference_no);
CREATE INDEX IF NOT EXISTS idx_outbound_loads_status ON outbound_loads(load_status, is_active);
CREATE INDEX IF NOT EXISTS idx_warehouse_issues_load_id ON warehouse_issues(outbound_load_id);
CREATE INDEX IF NOT EXISTS idx_warehouse_issues_issue_no ON warehouse_issues(issue_no);
CREATE INDEX IF NOT EXISTS idx_warehouse_issue_items_issue_id ON warehouse_issue_items(issue_id);
CREATE INDEX IF NOT EXISTS idx_opening_inventory_documents_warehouse_id ON opening_inventory_documents(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_opening_inventory_documents_opening_no ON opening_inventory_documents(opening_no);
CREATE INDEX IF NOT EXISTS idx_opening_inventory_items_document_id ON opening_inventory_items(opening_document_id);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id);
CREATE INDEX IF NOT EXISTS idx_expenses_status ON expenses(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_expenses_no ON expenses(expense_no);
CREATE INDEX IF NOT EXISTS idx_box_inventory_code 
            ON box_inventory(box_code);
CREATE INDEX IF NOT EXISTS idx_box_production_date 
            ON box_production(production_date);
CREATE INDEX IF NOT EXISTS idx_box_sales_customer 
            ON box_sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_box_sales_date 
            ON box_sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_box_sales_status 
            ON box_sales(status);
CREATE INDEX IF NOT EXISTS idx_box_sale_items_sale 
            ON "box_sale_items_old"(sale_id);
CREATE INDEX IF NOT EXISTS idx_box_sale_items_box 
            ON "box_sale_items_old"(box_code);
CREATE INDEX IF NOT EXISTS idx_stock_takes_no 
            ON stock_takes(stock_take_no);
CREATE INDEX IF NOT EXISTS idx_stock_takes_status 
            ON stock_takes(status);
CREATE INDEX IF NOT EXISTS idx_stock_takes_date 
            ON stock_takes(take_date);
CREATE INDEX IF NOT EXISTS idx_stock_adjustments_pallet 
            ON stock_adjustments(pallet_id);
CREATE INDEX IF NOT EXISTS idx_stock_adjustments_ref 
            ON stock_adjustments(reference_stock_take_id);
CREATE INDEX IF NOT EXISTS idx_box_material_prices_user 
            ON box_material_prices(user_id);
CREATE INDEX IF NOT EXISTS idx_cash_trans_date ON cash_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_cash_trans_type ON cash_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_cash_trans_from ON cash_transactions(from_account_id);
CREATE INDEX IF NOT EXISTS idx_cash_trans_to ON cash_transactions(to_account_id);
CREATE INDEX IF NOT EXISTS idx_cash_trans_ref ON cash_transactions(reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_expenses_paid_from ON expenses(paid_from_account_id);
CREATE INDEX IF NOT EXISTS idx_stock_take_items_take ON stock_take_items(stock_take_id);
CREATE INDEX IF NOT EXISTS idx_stock_take_items_pallet ON stock_take_items(pallet_id);
CREATE INDEX IF NOT EXISTS idx_payment_entries_financial_document_id ON payment_entries(financial_document_id);
CREATE INDEX IF NOT EXISTS idx_payment_entries_treasury_account_id ON payment_entries(treasury_account_id);
CREATE INDEX IF NOT EXISTS idx_outbound_load_items_load_id ON outbound_load_items(outbound_load_id);
CREATE INDEX IF NOT EXISTS idx_return_items_fd ON return_items(financial_document_id);
CREATE INDEX IF NOT EXISTS idx_return_items_smart_no ON return_items(smart_no);
CREATE INDEX IF NOT EXISTS idx_treasury_transactions_account_date ON treasury_transactions(treasury_account_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_inv_trans_pallet ON inventory_transactions(pallet_id);
CREATE INDEX IF NOT EXISTS idx_inv_trans_warehouse ON inventory_transactions(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_inv_trans_date ON inventory_transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_inv_trans_ref ON inventory_transactions(reference_type, reference_id);
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_lookup ON inventory_transactions(pallet_id, warehouse_id, transaction_date);
CREATE TABLE IF NOT EXISTS scrap_products(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, name TEXT NOT NULL, unit TEXT DEFAULT 'KG', is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS scrap_sales(id INTEGER PRIMARY KEY AUTOINCREMENT, sale_no TEXT, sale_date TEXT, buyer_id INTEGER, total_amount INTEGER DEFAULT 0, status TEXT DEFAULT 'OPEN', financial_document_id INTEGER, description TEXT, vehicle_no TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS scrap_sale_items(id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER, product_id INTEGER, name TEXT, gross_weight REAL DEFAULT 0, tare_weight REAL DEFAULT 0, net_weight REAL DEFAULT 0, unit_price INTEGER DEFAULT 0, total INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS scrap_sale_photos(id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER, path TEXT);
CREATE TABLE IF NOT EXISTS fiscal_years(id INTEGER PRIMARY KEY AUTOINCREMENT, year INTEGER, status TEXT DEFAULT 'OPEN', opened_at TEXT, closed_at TEXT, opening_inventory_value INTEGER DEFAULT 0, opening_treasury_value INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS payroll_workers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    national_id TEXT UNIQUE,
                    phone TEXT,
                    job_title TEXT,
                    hire_date TEXT,
                    agreed_salary INTEGER DEFAULT 0,
                    bank_account TEXT,
                    payment_method_default TEXT DEFAULT 'نقدی',
                    is_active INTEGER DEFAULT 1,
                    notes TEXT,
                    created_at TEXT
                , bank_name TEXT, card_number TEXT);
CREATE TABLE IF NOT EXISTS payroll_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker_id INTEGER NOT NULL,
                    transaction_date TEXT NOT NULL,
                    payment_type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    payment_method TEXT NOT NULL,
                    reference_no TEXT,
                    description TEXT,
                    is_signed INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY (worker_id) REFERENCES payroll_workers(id)
                );
CREATE TABLE IF NOT EXISTS "warehouse_receipts" ("id" INTEGER PRIMARY KEY, "inbound_load_id" INTEGER NOT NULL, "receipt_no" TEXT NOT NULL, "stage_no" INTEGER NOT NULL, "receipt_date" TEXT NOT NULL, "jalali_date_text" TEXT, "waybill_no" TEXT, "supplier_id" INTEGER NOT NULL, "driver_id" INTEGER NOT NULL, "vehicle_type" TEXT, "vehicle_plate" TEXT, "stage_load_qty" INTEGER NOT NULL, "delivered_qty" INTEGER NOT NULL, "discrepancy_qty" INTEGER NOT NULL, "freight_amount" INTEGER NOT NULL DEFAULT 0, "source_location" TEXT, "destination_location" TEXT, "warehouse_keeper_name" TEXT, "receiver_name" TEXT, "receipt_status" TEXT NOT NULL DEFAULT 'CONFIRMED', "description" TEXT, "print_html" TEXT, "created_by" INTEGER, "created_at" TEXT NOT NULL, "total_qty" INTEGER DEFAULT 0, "vat_amount" INTEGER NOT NULL DEFAULT 0, "extra_costs" INTEGER NOT NULL DEFAULT 0, UNIQUE("inbound_load_id", "stage_no"), UNIQUE("receipt_no"));
CREATE INDEX IF NOT EXISTS idx_warehouse_receipts_load_id ON warehouse_receipts(inbound_load_id);
CREATE INDEX IF NOT EXISTS idx_warehouse_receipts_receipt_no ON warehouse_receipts(receipt_no);
CREATE INDEX IF NOT EXISTS idx_receipts_status ON warehouse_receipts(receipt_status);
CREATE TABLE IF NOT EXISTS "warehouse_receipt_items" ("id" INTEGER PRIMARY KEY, "receipt_id" INTEGER NOT NULL, "row_no" INTEGER NOT NULL, "pallet_id" INTEGER NOT NULL, "qty" INTEGER NOT NULL, "unit_price" INTEGER NOT NULL DEFAULT 0, "total_price" INTEGER NOT NULL DEFAULT 0, "warehouse_id" INTEGER NOT NULL, "defect_description" TEXT, "description" TEXT, UNIQUE("receipt_id", "row_no"));
CREATE INDEX IF NOT EXISTS idx_warehouse_receipt_items_receipt_id ON warehouse_receipt_items(receipt_id);
CREATE INDEX IF NOT EXISTS idx_receipt_items_pallet ON warehouse_receipt_items(pallet_id);
CREATE TABLE IF NOT EXISTS box_production_items (id INTEGER PRIMARY KEY AUTOINCREMENT, box_production_id INTEGER, row_no INTEGER, part_name TEXT, count INTEGER, length_cm REAL, width_cm REAL, thickness_cm REAL);
CREATE TABLE IF NOT EXISTS box_sale_docs (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_no TEXT, sale_date TEXT, jalali_date_text TEXT, warehouse_id INTEGER, customer_id INTEGER, box_code TEXT, quantity INTEGER, unit_price INTEGER, total_amount INTEGER, total_cost INTEGER, status TEXT DEFAULT 'CONFIRMED', seller_name TEXT, buyer_name TEXT, notes TEXT, created_by INTEGER, created_at TEXT);
CREATE TABLE IF NOT EXISTS box_sale_items (id INTEGER PRIMARY KEY AUTOINCREMENT, sale_doc_id INTEGER, row_no INTEGER, part_name TEXT, count INTEGER, length_cm REAL, width_cm REAL, thickness_cm REAL);

-- ==== VIEWS (auto-appended) ====
CREATE VIEW IF NOT EXISTS v_issue_payments AS
    SELECT
        wi.id AS issue_id,
        wi.issue_no AS issue_no,
        COALESCE(ol.reference_no,'-') AS reference_no,
        wi.issue_date AS issue_date,
        wi.customer_id AS customer_id,
        ol.driver_id AS driver_id,
        COALESCE(p.first_name||' '||p.last_name,'-') AS customer_name,
        COALESCE(wi.issue_status,'CONFIRMED') AS issue_status,
        pe.id AS pay_id,
        pe.due_date AS payment_date,
        pe.amount AS amount,
        'RECEIPT' AS payment_type,
        COALESCE(pm.name, pm.code, '-') AS method_name,
        pe.status AS pay_status,
        pe.description AS description
    FROM warehouse_issues wi
    LEFT JOIN outbound_loads ol ON ol.id = wi.outbound_load_id
    LEFT JOIN persons p ON p.id = wi.customer_id
    LEFT JOIN financial_documents fd ON fd.issue_id = wi.id
    LEFT JOIN payment_entries pe ON pe.financial_document_id = fd.id
    LEFT JOIN payment_methods pm ON pm.id = pe.payment_method_id;
CREATE VIEW IF NOT EXISTS v_combined_issues AS
    SELECT
      wi.id AS issue_id, wi.issue_no AS issue_no,
      COALESCE(ol.reference_no,'-') AS reference_no, wi.issue_date AS issue_date,
      wi.customer_id AS customer_id,
      COALESCE(pc.first_name||' '||pc.last_name,'-') AS customer_name,
      ol.driver_id AS driver_id,
      COALESCE(pd.first_name||' '||pd.last_name,'-') AS driver_name,
      (SELECT COUNT(*) FROM warehouse_issues w2 WHERE w2.outbound_load_id=wi.outbound_load_id
         AND COALESCE(w2.issue_status,'CONFIRMED')!='CANCELLED') AS stage_count,
      (SELECT COALESCE(SUM(wii.total_price),0) FROM warehouse_issue_items wii WHERE wii.issue_id=wi.id) + COALESCE(wi.vat_amount,0) + COALESCE(wi.extra_costs,0) AS amount,
      (SELECT COALESCE(SUM(pe.amount),0) FROM payment_entries pe JOIN financial_documents fd ON fd.id=pe.financial_document_id WHERE fd.issue_id=wi.id AND fd.direction='RECEIVABLE') AS paid_amount,
      (SELECT COALESCE(pm.code,'-') FROM payment_entries pe JOIN financial_documents fd ON fd.id=pe.financial_document_id JOIN payment_methods pm ON pm.id=pe.payment_method_id WHERE fd.issue_id=wi.id LIMIT 1) AS payment_method,
      '' AS last_payment_date,
      COALESCE(wi.delivered_qty,0) AS delivered_qty,
      COALESCE(ol.total_load_qty,0) AS total_load_qty,
      COALESCE(ol.remaining_qty,0) AS remaining_qty,
      COALESCE(wi.issue_status,'CONFIRMED') AS issue_status
    FROM warehouse_issues wi
    LEFT JOIN outbound_loads ol ON ol.id=wi.outbound_load_id
    LEFT JOIN persons pc ON pc.id=wi.customer_id
    LEFT JOIN persons pd ON pd.id=ol.driver_id;
