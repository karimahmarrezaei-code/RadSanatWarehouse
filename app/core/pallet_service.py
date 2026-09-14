# -*- coding: utf-8 -*-
"""pallet_service.py - کلاس مرکزی مدیریت قیمت‌ها و موجودی پالت‌ها (نسخه مقاوم)"""

from typing import Any, Dict, List, Optional


class PalletService:
    def __init__(self, db) -> None:
        self.db = db
        self._avg_prices: Dict[int, float] = {}
        self._stock: Dict[int, int] = {}
        self._loaded = False

    # ------------------------------------------------------------------
    def load_prices(self) -> None:
        if self._loaded:
            return

        self._avg_prices = {}
        self._stock = {}

        # ---------- 1) قیمت میانگین: موجودی اول دوره + تراکنش‌های IN ----------
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute("""
                    SELECT pallet_id,
                           SUM(total_value) * 1.0 / NULLIF(SUM(qty), 0) AS avg_price
                    FROM (
                        SELECT pallet_id, qty AS qty, total_price AS total_value
                        FROM opening_inventory_items WHERE qty > 0

                        UNION ALL

                        SELECT pallet_id, qty_in AS qty, total_price AS total_value
                        FROM inventory_transactions
                        WHERE transaction_type = 'IN' AND qty_in > 0
                              AND COALESCE(is_void, 0) = 0
                    )
                    WHERE qty > 0
                    GROUP BY pallet_id
                """).fetchall()
            for r in rows:
                if r[1]:
                    self._avg_prices[int(r[0])] = float(r[1])
        except Exception as e:
            print('PalletService avg(transactions) error:', str(e))

        # ---------- 2) fallback: میانگین وزنی از اسناد ثبت‌شده ----------
        if not self._avg_prices:
            try:
                with self.db.connect() as conn:
                    conn.row_factory = None
                    rows = conn.execute("""
                        SELECT pallet_id,
                               SUM(unit_price * qty) * 1.0 / NULLIF(SUM(qty), 0) AS avg_price
                        FROM (
                            SELECT wri.pallet_id AS pallet_id, wri.qty AS qty, wri.unit_price AS unit_price
                            FROM warehouse_receipt_items wri
                            JOIN warehouse_receipts wr ON wr.id = wri.receipt_id
                            WHERE COALESCE(wr.receipt_status, 'CONFIRMED') <> 'CANCELLED'
                                  AND wri.qty > 0 AND wri.unit_price > 0

                            UNION ALL

                            SELECT wii.pallet_id, wii.qty, wii.unit_price
                            FROM warehouse_issue_items wii
                            JOIN warehouse_issues wi ON wi.id = wii.issue_id
                            WHERE COALESCE(wi.issue_status, 'CONFIRMED') <> 'CANCELLED'
                                  AND wii.qty > 0 AND wii.unit_price > 0
                        )
                        GROUP BY pallet_id
                    """).fetchall()
                for r in rows:
                    if r[1]:
                        self._avg_prices[int(r[0])] = float(r[1])
            except Exception as e:
                print('PalletService avg(documents) error:', str(e))

        # ---------- 3) موجودی کل = افتتاحیه + تراکنش‌های غیرباطل ----------
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows2 = conn.execute("""
                    SELECT pallet_id, COALESCE(SUM(q), 0) AS stock
                    FROM (
                        SELECT pallet_id, qty AS q
                        FROM opening_inventory_items

                        UNION ALL

                        SELECT pallet_id,
                               CASE WHEN transaction_type = 'IN' THEN qty_in ELSE -qty_out END
                        FROM inventory_transactions
                        WHERE COALESCE(is_void, 0) = 0
                    )
                    GROUP BY pallet_id
                """).fetchall()
            for r in rows2:
                self._stock[int(r[0])] = max(int(r[1] or 0), 0)
        except Exception as e:
            print('PalletService stock error:', str(e))

        self._loaded = True
        print(f'PalletService loaded: {len(self._avg_prices)} prices / {len(self._stock)} stocks')

    # ------------------------------------------------------------------
    def reload(self) -> None:
        self._loaded = False
        self.load_prices()

    def all_pallets(self) -> List[Dict[str, Any]]:
        try:
            with self.db.connect() as conn:
                conn.row_factory = None
                rows = conn.execute(
                    "SELECT id, code, name FROM pallets WHERE is_active=1 ORDER BY code"
                ).fetchall()
                return [{'id': r[0], 'code': r[1] or '', 'name': r[2] or ''} for r in rows]
        except Exception:
            return []

    def avg_price(self, pallet_id: Optional[int]) -> float:
        if not pallet_id:
            return 0.0
        self.load_prices()
        return self._avg_prices.get(int(pallet_id), 0.0)

    def stock(self, pallet_id: Optional[int]) -> int:
        if not pallet_id:
            return 0
        self.load_prices()
        return self._stock.get(int(pallet_id), 0)

    def prices_map(self) -> Dict[int, float]:
        self.load_prices()
        return dict(self._avg_prices)

    def stock_map(self) -> Dict[int, int]:
        self.load_prices()
        return dict(self._stock)