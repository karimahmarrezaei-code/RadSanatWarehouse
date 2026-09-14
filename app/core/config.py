from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data'
DB_PATH = DATA_DIR / 'app.db'
SCHEMA_PATH = DATA_DIR / 'schema.sql'
SEED_PATH = DATA_DIR / 'seed.sql'
PROVINCES_PATH = DATA_DIR / 'iran_provinces.json'
CITIES_PATH = DATA_DIR / 'iran_cities.json'
APP_NAME = 'Warehouse Pallet Manager'
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'
