# -*- coding: utf-8 -*-
from app.core.jalali import now_iso

class ScrapRepository:
    def __init__(self, db):
        self.db = db
        self._ensure()

    def _ensure(self):
        with self.db.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS scrap_products(id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT, name TEXT NOT NULL, unit TEXT DEFAULT 'KG', is_active INTEGER DEFAULT 1)")
            conn.execute("CREATE TABLE IF NOT EXISTS scrap_sales(id INTEGER PRIMARY KEY AUTOINCREMENT, sale_no TEXT, sale_date TEXT, buyer_id INTEGER, total_amount INTEGER DEFAULT 0, status TEXT DEFAULT 'OPEN', financial_document_id INTEGER, description TEXT, vehicle_no TEXT, created_at TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS scrap_sale_items(id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER, product_id INTEGER, name TEXT, gross_weight REAL DEFAULT 0, tare_weight REAL DEFAULT 0, net_weight REAL DEFAULT 0, unit_price INTEGER DEFAULT 0, total INTEGER DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS scrap_sale_photos(id INTEGER PRIMARY KEY AUTOINCREMENT, sale_id INTEGER, path TEXT)")
            try:
                conn.execute("ALTER TABLE scrap_sales ADD COLUMN vehicle_no TEXT")
            except Exception:
                pass
            if not conn.execute("SELECT id FROM scrap_products LIMIT 1").fetchone():
                for c, n in (('SC-001', 'خرده چوب'), ('SC-002', 'خاک اره'), ('SC-003', 'ضایعات MDF')):
                    conn.execute("INSERT INTO scrap_products(code, name) VALUES(?,?)", (c, n))
            conn.commit()

    def list_products(self):
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT id, code, name FROM scrap_products WHERE is_active=1 ORDER BY code")]

    def list_persons(self):
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT id, first_name||' '||last_name AS name FROM persons ORDER BY name")]

    def register_sale(self, items, buyer_id, sale_date, description, user_id, vehicle_no=''):
        total = sum(i['total'] for i in items)
        with self.db.connect() as conn:
            cur = conn.execute("INSERT INTO scrap_sales(sale_no, sale_date, buyer_id, total_amount, status, description, vehicle_no, created_at) VALUES('','',?,?,'OPEN',?,?,?)",
                               (buyer_id, total, description, vehicle_no, now_iso()))
            sale_id = cur.lastrowid
            sale_no = f"WP-{sale_id:04d}"
            conn.execute("UPDATE scrap_sales SET sale_no=? WHERE id=?", (sale_no, sale_id))
            for i in items:
                conn.execute("INSERT INTO scrap_sale_items(sale_id, product_id, name, gross_weight, tare_weight, net_weight, unit_price, total) VALUES(?,?,?,?,?,?,?,?)",
                             (sale_id, i['product_id'], i['name'], i['gross'], i['tare'], i['net'], i['price'], i['total']))
            conn.execute("INSERT INTO financial_documents(finance_no, operation_type, direction, counterparty_person_id, finance_date, total_amount, settled_amount, status, description, created_at, created_by) VALUES(?,?,?,?,?,?,'0','OPEN',?,?,?)",
                         (sale_no, 'OUTBOUND_ISSUE', 'RECEIVABLE', buyer_id, sale_date, total, f'فروش ضایعات {sale_no}', now_iso(), user_id))
            fd_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("UPDATE scrap_sales SET financial_document_id=? WHERE id=?", (fd_id, sale_id))
            conn.commit()
            return sale_no, sale_id

    def add_photo(self, sale_id, path):
        with self.db.connect() as conn:
            conn.execute("INSERT INTO scrap_sale_photos(sale_id, path) VALUES(?,?)", (sale_id, path)); conn.commit()

    def get_sale(self, sale_id):
        with self.db.connect() as conn:
            s = conn.execute("SELECT s.*, p.first_name||' '||p.last_name AS buyer FROM scrap_sales s LEFT JOIN persons p ON p.id=s.buyer_id WHERE s.id=?", (sale_id,)).fetchone()
            items = [dict(r) for r in conn.execute("SELECT * FROM scrap_sale_items WHERE sale_id=? ORDER BY id", (sale_id,))]
            photos = [r['path'] for r in conn.execute("SELECT path FROM scrap_sale_photos WHERE sale_id=? ORDER BY id", (sale_id,))]
        return (dict(s) if s else None), items, photos

    def list_sales(self):
        with self.db.connect() as conn:
            return [dict(r) for r in conn.execute("SELECT s.id, s.sale_no, s.sale_date, s.total_amount, s.status, p.first_name||' '||p.last_name AS buyer FROM scrap_sales s LEFT JOIN persons p ON p.id=s.buyer_id ORDER BY s.id DESC")]
