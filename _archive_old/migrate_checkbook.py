# -*- coding: utf-8 -*-
import sqlite3, os
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'warehouse.db')
conn = sqlite3.connect(DB)
conn.executescript("""
CREATE TABLE IF NOT EXISTS checkbook_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  check_no TEXT, sayyad_no TEXT, bank_name TEXT, branch TEXT,
  amount INTEGER NOT NULL DEFAULT 0,
  issue_date TEXT, due_date TEXT,
  issuer_person_id INTEGER,
  direction TEXT NOT NULL DEFAULT 'RECEIVED',
  status TEXT NOT NULL DEFAULT 'IN_HAND',
  source_type TEXT, source_id INTEGER,
  created_at TEXT, created_by INTEGER
);
CREATE TABLE IF NOT EXISTS checkbook_movements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  check_id INTEGER NOT NULL,
  move_type TEXT NOT NULL,
  move_date TEXT,
  from_person_id INTEGER, to_person_id INTEGER,
  ref_type TEXT, ref_id INTEGER,
  amount INTEGER, note TEXT,
  created_at TEXT, created_by INTEGER
);
""")
conn.commit(); conn.close()
print('جداول دفترچه چک ساخته شد.')