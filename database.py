import sqlite3
from datetime import datetime, timedelta
import random
import string

DB_PATH = "shop.db"

def generate_unique_code():
    """Генерирует уникальный 6-символьный код из букв и цифр"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT 1 FROM users WHERE referral_code = ?", (code,))
        exists = c.fetchone()
        conn.close()
        if not exists:
            return code

def migrate_users_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    if 'balance' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
    if 'referrer_id' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN referrer_id INTEGER")
    if 'referrer_code' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN referrer_code TEXT")
    if 'referral_code' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
    if 'created_at' not in columns:
        c.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
    # Генерируем коды для старых пользователей, у которых их нет
    c.execute("SELECT user_id FROM users WHERE referral_code IS NULL")
    rows = c.fetchall()
    for (user_id,) in rows:
        code = generate_unique_code()
        c.execute("UPDATE users SET referral_code = ? WHERE user_id = ?", (code, user_id))
    conn.commit()
    conn.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        steam_id TEXT,
        balance REAL DEFAULT 0,
        referrer_id INTEGER,
        referrer_code TEXT,
        referral_code TEXT UNIQUE,
        created_at TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        privilege TEXT,
        steam_id TEXT,
        amount REAL,
        status TEXT,
        created_at TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS deposit_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        screenshot_file_id TEXT,
        status TEXT DEFAULT 'waiting',
        created_at TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        type TEXT,
        description TEXT,
        created_at TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS admins (
        admin_id INTEGER PRIMARY KEY
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS pending_orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        steam_id TEXT,
        product_detail TEXT,
        amount REAL,
        command TEXT,
        status TEXT DEFAULT 'waiting',
        created_at TIMESTAMP
    )""")
    conn.commit()
    conn.close()
    migrate_users_table()

def get_or_create_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, balance, referrer_code, referral_code FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        conn.close()
        return {"user_id": row[0], "balance": row[1], "referrer_code": row[2], "referral_code": row[3]}
    else:
        code = generate_unique_code()
        c.execute("INSERT INTO users (user_id, balance, referrer_code, referral_code, created_at) VALUES (?, ?, ?, ?, ?)",
                  (user_id, 0, None, code, datetime.now()))
        conn.commit()
        conn.close()
        return {"user_id": user_id, "balance": 0, "referrer_code": None, "referral_code": code}

def set_referrer(user_id: int, friend_code: str) -> bool:
    """Привязывает пользователя к рефереру по коду"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Найти пользователя с таким кодом
    c.execute("SELECT user_id FROM users WHERE referral_code = ?", (friend_code,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False
    referrer_id = row[0]
    if referrer_id == user_id:
        conn.close()
        return False  # нельзя пригласить самого себя
    # Проверить, не привязан ли уже
    c.execute("SELECT referrer_code FROM users WHERE user_id = ?", (user_id,))
    current = c.fetchone()
    if current[0] is not None:
        conn.close()
        return False  # уже есть реферер
    c.execute("UPDATE users SET referrer_code = ? WHERE user_id = ?", (friend_code, user_id))
    conn.commit()
    conn.close()
    return True

def get_referrals_list(user_id: int):
    """Возвращает список пользователей, которые указали код данного пользователя"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, created_at FROM users WHERE referrer_code = (SELECT referral_code FROM users WHERE user_id = ?)", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"user_id": r[0], "date": r[1]} for r in rows]

def get_referral_bonus_total(user_id: int) -> float:
    """Сумма бонусов, полученных от рефералов"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = 'referral'", (user_id,))
    total = c.fetchone()[0]
    conn.close()
    return total or 0.0

def update_balance(user_id: int, amount_change: float, transaction_type: str, description: str = ""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount_change, user_id))
    c.execute("INSERT INTO transactions (user_id, amount, type, description, created_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, amount_change, transaction_type, description, datetime.now()))
    conn.commit()
    conn.close()

def get_balance(user_id: int) -> float:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0.0

def add_deposit_request(user_id: int, amount: float, file_id: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO deposit_requests (user_id, amount, screenshot_file_id, created_at, status) VALUES (?, ?, ?, ?, 'waiting')",
              (user_id, amount, file_id, datetime.now()))
    request_id = c.lastrowid
    conn.commit()
    conn.close()
    return request_id

def get_pending_deposit_requests():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT request_id, user_id, amount, screenshot_file_id, created_at FROM deposit_requests WHERE status = 'waiting' ORDER BY created_at")
    rows = c.fetchall()
    conn.close()
    return [{"request_id": r[0], "user_id": r[1], "amount": r[2], "screenshot_file_id": r[3], "created_at": r[4]} for r in rows]

def approve_deposit(request_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, amount FROM deposit_requests WHERE request_id = ? AND status = 'waiting'", (request_id,))
    row = c.fetchone()
    if row:
        user_id, amount = row
        # Начисляем основной баланс
        update_balance(user_id, amount, "deposit", f"Пополнение баланса на {amount} ₽")
        # Начисляем бонус рефереру (10% от суммы пополнения)
        c.execute("SELECT referrer_code FROM users WHERE user_id = ?", (user_id,))
        referrer_code = c.fetchone()[0]
        if referrer_code:
            c.execute("SELECT user_id FROM users WHERE referral_code = ?", (referrer_code,))
            referrer_row = c.fetchone()
            if referrer_row:
                referrer_id = referrer_row[0]
                bonus = amount * 0.1
                update_balance(referrer_id, bonus, "referral", f"10% от пополнения реферала {user_id} ({amount} ₽)")
        c.execute("UPDATE deposit_requests SET status = 'approved' WHERE request_id = ?", (request_id,))
        conn.commit()
        conn.close()
        return user_id, amount
    conn.close()
    return None, None

def reject_deposit(request_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE deposit_requests SET status = 'rejected' WHERE request_id = ?", (request_id,))
    conn.commit()
    conn.close()

def add_purchase_record(user_id: int, privilege: str, steam_id: str, amount: float):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO purchases (user_id, privilege, steam_id, amount, status, created_at) VALUES (?, ?, ?, ?, 'completed', ?)",
              (user_id, privilege, steam_id, amount, datetime.now()))
    conn.commit()
    conn.close()

def get_purchases_last_week():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    week_ago = datetime.now() - timedelta(days=7)
    c.execute("SELECT privilege, amount, steam_id, created_at FROM purchases WHERE created_at > ? ORDER BY created_at DESC", (week_ago,))
    rows = c.fetchall()
    conn.close()
    return [{"privilege": r[0], "amount": r[1], "steam_id": r[2], "created_at": r[3]} for r in rows]

def get_all_steam_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT steam_id FROM users WHERE steam_id IS NOT NULL")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(amount) FROM purchases")
    count, total = c.fetchone()
    conn.close()
    return count or 0, total or 0

def add_admin(admin_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO admins (admin_id) VALUES (?)", (admin_id,))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def remove_admin(admin_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE admin_id = ?", (admin_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_admins() -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT admin_id FROM admins")
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def save_steam_id(user_id: int, steam_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET steam_id = ? WHERE user_id = ?", (steam_id, user_id))
    conn.commit()
    conn.close()

def get_steam_id(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT steam_id FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_referral_code(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT referral_code FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_referrer_code(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT referrer_code FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None