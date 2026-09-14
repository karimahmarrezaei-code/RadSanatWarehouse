from typing import Dict, Any
from app.core.database import DatabaseManager

class CompanyRepository:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """بررسی و ساخت خودکار جدول در صورتی که در دیتابیس فعلی وجود نداشته باشد"""
        create_table_query = """
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
        """
        with self.db.connect() as connection:
            connection.execute(create_table_query)
            # ساخت یک ردیف پیش‌فرض برای اینکه آپدیت‌ها روی آن انجام شود
            connection.execute("INSERT OR IGNORE INTO company_profile (id) VALUES (1)")
            connection.commit()

    def get_company_profile(self) -> Dict[str, Any]:
        """دریافت اطلاعات شرکت برای نمایش در فرم یا چاپ در سربرگ"""
        query = "SELECT * FROM company_profile WHERE id = 1 LIMIT 1"
        
        with self.db.connect() as connection:
            row = connection.execute(query).fetchone()
            if row:
                return dict(row)
            return {}

    def save_company_profile(self, payload: Dict[str, Any]) -> None:
        """بروزرسانی اطلاعات شرکت"""
        query = """
            UPDATE company_profile 
            SET 
                company_name = ?, show_company_name = ?,
                ceo_name = ?, show_ceo_name = ?,
                national_id = ?, show_national_id = ?,
                economic_code = ?, show_economic_code = ?,
                registration_number = ?, show_registration_number = ?,
                phone = ?, show_phone = ?,
                mobile = ?, show_mobile = ?,
                email = ?, show_email = ?,
                website = ?, show_website = ?,
                address = ?, show_address = ?
            WHERE id = 1
        """
        
        # استخراج مقادیر به صورت یک تاپل برای دیتابیس
        params = (
            payload.get('company_name'), 1 if payload.get('show_company_name') else 0,
            payload.get('ceo_name'), 1 if payload.get('show_ceo_name') else 0,
            payload.get('national_id'), 1 if payload.get('show_national_id') else 0,
            payload.get('economic_code'), 1 if payload.get('show_economic_code') else 0,
            payload.get('registration_number'), 1 if payload.get('show_registration_number') else 0,
            payload.get('phone'), 1 if payload.get('show_phone') else 0,
            payload.get('mobile'), 1 if payload.get('show_mobile') else 0,
            payload.get('email'), 1 if payload.get('show_email') else 0,
            payload.get('website'), 1 if payload.get('show_website') else 0,
            payload.get('address'), 1 if payload.get('show_address') else 0,
        )
        
        with self.db.connect() as connection:
            connection.execute(query, params)
            connection.commit()