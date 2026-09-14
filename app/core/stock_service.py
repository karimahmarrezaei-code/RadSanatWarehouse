# -*- coding: utf-8 -*-
"""منبع واحد موجودی آزاد پالت - ONE-STOCK"""


def free_stock_map(db):
    try:
        with db.connect() as cn:
            cn.row_factory = None
            phys = {r[0]: int(r[1] or 0) for r in cn.execute(
                "SELECT pallet_id, COALESCE(SUM(quantity),0) FROM inventory_levels GROUP BY pallet_id").fetchall()}
            iss = {r[0]: int(r[1] or 0) for r in cn.execute(
                "SELECT wii.pallet_id, SUM(wii.qty) FROM warehouse_issue_items wii "
                "JOIN warehouse_issues wi ON wi.id=wii.issue_id "
                "WHERE wi.issue_status!='CANCELLED' GROUP BY wii.pallet_id").fetchall()}
            rsv = {r[0]: int(r[1] or 0) for r in cn.execute(
                "SELECT oli.pallet_id, SUM(oli.qty - COALESCE((SELECT SUM(wii.qty) FROM warehouse_issue_items wii "
                "JOIN warehouse_issues wi ON wi.id=wii.issue_id WHERE wi.outbound_load_id=ol.id "
                "AND wi.issue_status!='CANCELLED' AND wii.pallet_id=oli.pallet_id),0)) "
                "FROM outbound_load_items oli JOIN outbound_loads ol ON ol.id=oli.outbound_load_id "
                "WHERE ol.load_status='OPEN' AND ol.is_active=1 GROUP BY oli.pallet_id").fetchall()}
        return {pid: max(phys.get(pid, 0) - iss.get(pid, 0) - rsv.get(pid, 0), 0) for pid in phys}
    except Exception:
        return {}


def free_stock(db, pallet_id):
    return int(free_stock_map(db).get(pallet_id, 0) or 0)
