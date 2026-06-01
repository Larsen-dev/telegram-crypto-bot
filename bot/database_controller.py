import yaml
import sqlite3
from pathlib import Path

# .yaml settings variables
with open(r"bot/settings.yaml", "r") as file:
    yaml_settings = yaml.safe_load(file)

DB_SETTINGS = yaml_settings["database_settings"]
BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "bot_subscriptions.db"

def init_db():
    with sqlite3.connect(DB_NAME) as connect:
        cursor = connect.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                coin TEXT NOT NULL,
                target_price REAL NOT NULL,
                alert_type TEXT CHECK(alert_type IN ('above', 'below')),
                is_active INTEGER DEFAULT 1,

                UNIQUE(user_id, coin, target_price, alert_type)
            )
        """)
        
        connect.commit()

def add_subscription(user_id: int, coin: str, target_price: int, alert_type: str):
    with sqlite3.connect(DB_NAME) as connect:
        cursor = connect.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO subscriptions(
                user_id,
                coin,
                target_price,
                alert_type
            ) VALUES(?, ?, ?, ?)
        """, (user_id, coin, target_price, alert_type))

        connect.commit()

def get_subscriptions():
    with sqlite3.connect(DB_NAME) as connect:
        connect.row_factory = sqlite3.Row
        
        cursor = connect.cursor()
        cursor.execute("""
            SELECT * FROM subscriptions WHERE is_active = 1
        """)

        return [dict(row) for row in cursor.fetchall()]

def get_subscriptions_by_user_id(user_id: int):
    with sqlite3.connect(DB_NAME) as connect:
        connect.row_factory = sqlite3.Row
        
        cursor = connect.cursor()
        cursor.execute("""
            SELECT * FROM subscriptions WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC
        """, (user_id,))

        return [dict(row) for row in cursor.fetchall()]

def set_inactive(subscription_id: int):
    with sqlite3.connect(DB_NAME) as connect:
        cursor = connect.cursor()
        cursor.execute("""
            UPDATE subscriptions SET is_active = 0 WHERE id = ?
        """, (subscription_id,))
        
        connect.commit()
