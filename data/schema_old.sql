PRAGMA foreign_keys = ON;

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
);

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
    operation_type TEXT NOT NULL CHECK (operation_type IN ('INBOUND_RECEIPT', 'INBOUND_FREIGHT', 'OUTBOUND_ISSUE', 'OUTBOUND_FREIGHT')),
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
    created_by INTEGER,
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


CREATE TABLE IF NOT EXISTS payment_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    financial_document_id INTEGER NOT NULL,
    payment_method_id INTEGER NOT NULL,
    payer_payee_person_id INTEGER,
    bank_account_id INTEGER,
    treasury_account_id INTEGER,
    amount INTEGER NOT NULL CHECK (amount > 0),
    due_date TEXT,
    check_no TEXT,
    check_serial TEXT,
    check_bank_name TEXT,
    check_branch_name TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'CLEARED', 'BOUNCED', 'CANCELLED')),
    description TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (financial_document_id) REFERENCES financial_documents(id) ON DELETE CASCADE,
    FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id) ON DELETE RESTRICT,
    FOREIGN KEY (payer_payee_person_id) REFERENCES persons(id) ON DELETE SET NULL,
    FOREIGN KEY (bank_account_id) REFERENCES bank_accounts(id) ON DELETE SET NULL,
    FOREIGN KEY (treasury_account_id) REFERENCES treasury_accounts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS treasury_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    treasury_account_id INTEGER NOT NULL,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('IN', 'OUT')),
    source_type TEXT NOT NULL CHECK (source_type IN ('PAYMENT_ENTRY', 'ADJUSTMENT')),
    source_id INTEGER,
    amount INTEGER NOT NULL CHECK (amount > 0),
    balance_after INTEGER NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (treasury_account_id) REFERENCES treasury_accounts(id) ON DELETE CASCADE
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
CREATE INDEX IF NOT EXISTS idx_payment_entries_financial_document_id ON payment_entries(financial_document_id);
CREATE INDEX IF NOT EXISTS idx_payment_entries_treasury_account_id ON payment_entries(treasury_account_id);
CREATE INDEX IF NOT EXISTS idx_treasury_accounts_code ON treasury_accounts(code);
CREATE INDEX IF NOT EXISTS idx_treasury_transactions_account_date ON treasury_transactions(treasury_account_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_journal_lines_journal_entry_id ON journal_lines(journal_entry_id);

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

CREATE TABLE IF NOT EXISTS warehouse_receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inbound_load_id INTEGER NOT NULL,
    receipt_no TEXT NOT NULL UNIQUE,
    stage_no INTEGER NOT NULL CHECK (stage_no >= 1),
    receipt_date TEXT NOT NULL,
    jalali_date_text TEXT,
    waybill_no TEXT,
    supplier_id INTEGER NOT NULL,
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
    receipt_status TEXT NOT NULL DEFAULT 'CONFIRMED' CHECK (receipt_status IN ('DRAFT', 'CONFIRMED', 'CANCELLED')),
    description TEXT,
    print_html TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL,
    UNIQUE (inbound_load_id, stage_no),
    FOREIGN KEY (inbound_load_id) REFERENCES inbound_loads(id) ON DELETE CASCADE,
    FOREIGN KEY (supplier_id) REFERENCES persons(id) ON DELETE RESTRICT,
    FOREIGN KEY (driver_id) REFERENCES persons(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS warehouse_receipt_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id INTEGER NOT NULL,
    row_no INTEGER NOT NULL CHECK (row_no >= 1),
    pallet_id INTEGER NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    unit_price INTEGER NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    total_price INTEGER NOT NULL DEFAULT 0 CHECK (total_price >= 0),
    warehouse_id INTEGER NOT NULL,
    defect_description TEXT,
    description TEXT,
    UNIQUE (receipt_id, row_no),
    FOREIGN KEY (receipt_id) REFERENCES warehouse_receipts(id) ON DELETE CASCADE,
    FOREIGN KEY (pallet_id) REFERENCES pallets(id) ON DELETE RESTRICT,
    FOREIGN KEY (warehouse_id) REFERENCES warehouses(id) ON DELETE RESTRICT
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
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
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
    created_at TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS inventory_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('IN', 'OUT')),
    reference_type TEXT NOT NULL CHECK (reference_type IN ('RECEIPT', 'ISSUE', 'OPENING')),
    reference_id INTEGER NOT NULL,
    pallet_id INTEGER NOT NULL,
    warehouse_id INTEGER NOT NULL,
    qty_in INTEGER NOT NULL DEFAULT 0 CHECK (qty_in >= 0),
    qty_out INTEGER NOT NULL DEFAULT 0 CHECK (qty_out >= 0),
    unit_price INTEGER NOT NULL DEFAULT 0 CHECK (unit_price >= 0),
    total_price INTEGER NOT NULL DEFAULT 0 CHECK (total_price >= 0),
    description TEXT,
    created_at TEXT NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_inbound_loads_reference_no ON inbound_loads(reference_no);
CREATE INDEX IF NOT EXISTS idx_inbound_loads_status ON inbound_loads(load_status, is_active);
CREATE INDEX IF NOT EXISTS idx_warehouse_receipts_load_id ON warehouse_receipts(inbound_load_id);
CREATE INDEX IF NOT EXISTS idx_warehouse_receipts_receipt_no ON warehouse_receipts(receipt_no);
CREATE INDEX IF NOT EXISTS idx_warehouse_receipt_items_receipt_id ON warehouse_receipt_items(receipt_id);
CREATE INDEX IF NOT EXISTS idx_outbound_loads_reference_no ON outbound_loads(reference_no);
CREATE INDEX IF NOT EXISTS idx_outbound_loads_status ON outbound_loads(load_status, is_active);
CREATE INDEX IF NOT EXISTS idx_warehouse_issues_load_id ON warehouse_issues(outbound_load_id);
CREATE INDEX IF NOT EXISTS idx_warehouse_issues_issue_no ON warehouse_issues(issue_no);
CREATE INDEX IF NOT EXISTS idx_warehouse_issue_items_issue_id ON warehouse_issue_items(issue_id);
CREATE INDEX IF NOT EXISTS idx_inventory_transactions_lookup ON inventory_transactions(pallet_id, warehouse_id, transaction_date);
CREATE INDEX IF NOT EXISTS idx_opening_inventory_documents_warehouse_id ON opening_inventory_documents(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_opening_inventory_documents_opening_no ON opening_inventory_documents(opening_no);
CREATE INDEX IF NOT EXISTS idx_opening_inventory_items_document_id ON opening_inventory_items(opening_document_id);
