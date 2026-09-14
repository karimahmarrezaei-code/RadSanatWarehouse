# -*- coding: utf-8 -*-
"""اعمال ویوهای جدید روی لپ‌تاپ - فقط روی لپ‌تاپ اجرا شود"""
import os, sqlite3
p = None
for c in (r"D:\warehouse_app\_internal\data\app.db", r"D:\warehouse_app\data\app.db"):
    if os.path.exists(c):
        p = c
        break
print('دیتابیس:', p)
conn = sqlite3.connect(p)
conn.execute("DROP VIEW IF EXISTS v_issue_payments")
conn.execute("""CREATE VIEW v_issue_payments AS
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
    LEFT JOIN payment_methods pm ON pm.id = pe.payment_method_id""")
conn.execute("DROP VIEW IF EXISTS v_combined_issues")
conn.execute("""CREATE VIEW v_combined_issues AS
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
    LEFT JOIN persons pd ON pd.id=ol.driver_id""")
conn.commit()
print('✔ ویوها اعمال شد: 2 ویو')
conn.close()
input('Enter...')