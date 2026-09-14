from app.core.config import DB_PATH, DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME
from app.core.database import DatabaseManager


def main() -> None:
    db = DatabaseManager(DB_PATH)
    db.initialize()
    print('Database created successfully:', DB_PATH)
    print('Default admin username:', DEFAULT_ADMIN_USERNAME)
    print('Default admin password:', DEFAULT_ADMIN_PASSWORD)
    print('Important: change the default password after first login.')


if __name__ == '__main__':
    main()
