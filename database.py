# database.py
import sqlite3
from datetime import datetime, timedelta
import secrets
import hashlib
from config import DATABASE_NAME


def get_connection():
    return sqlite3.connect(DATABASE_NAME, check_same_thread=False)


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table (login credentials)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            device_id TEXT,
            balance REAL DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    # Sessions table (active logins)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            telegram_id INTEGER,
            session_token TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Keys stock table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keys_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_value TEXT UNIQUE NOT NULL,
            duration_days INTEGER NOT NULL,
            is_sold BOOLEAN DEFAULT 0,
            sold_to INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sold_at TIMESTAMP,
            FOREIGN KEY (sold_to) REFERENCES users(id)
        )
    ''')

    # Purchases history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            key_id INTEGER,
            amount REAL,
            duration_days INTEGER,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (key_id) REFERENCES keys_stock(id)
        )
    ''')

    # Balance transactions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            transaction_type TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Settings table for IPA link and other settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def update_setting(key, value):
    """Update or insert a setting into the settings table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value))
    conn.commit()
    conn.close()


def get_setting(key):
    """Retrieve a setting from the settings table."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key, ))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def generate_session_token():
    return secrets.token_hex(32)


def generate_key():
    return f"MODDER-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"


# User Management
def create_user(username, password, is_admin=False):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            '''
            INSERT INTO users (username, password_hash, is_admin)
            VALUES (?, ?, ?)
        ''', (username, hash_password(password), is_admin))
        conn.commit()
        return True, cursor.lastrowid
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    finally:
        conn.close()


def authenticate_user(username, password, telegram_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT id, password_hash, device_id, is_active FROM users WHERE username = ?
    ''', (username, ))

    result = cursor.fetchone()

    if not result:
        conn.close()
        return False, "Invalid username or password"

    user_id, stored_hash, device_id, is_active = result

    if not is_active:
        conn.close()
        return False, "Account is deactivated"

    if stored_hash != hash_password(password):
        conn.close()
        return False, "Invalid username or password"

    # Check device binding
    if device_id and device_id != str(telegram_id):
        conn.close()
        return False, "This account is bound to another device"

    # Bind device if first login
    if not device_id:
        cursor.execute(
            '''
            UPDATE users SET device_id = ?, telegram_id = ? WHERE id = ?
        ''', (str(telegram_id), telegram_id, user_id))

    # Update last login
    cursor.execute(
        '''
        UPDATE users SET last_login = ?, telegram_id = ? WHERE id = ?
    ''', (datetime.now(), telegram_id, user_id))

    # Create session
    session_token = generate_session_token()
    expires_at = datetime.now() + timedelta(days=7)

    cursor.execute(
        '''
        INSERT INTO sessions (user_id, telegram_id, session_token, expires_at)
        VALUES (?, ?, ?, ?)
    ''', (user_id, telegram_id, session_token, expires_at))

    conn.commit()
    conn.close()

    return True, {"user_id": user_id, "session_token": session_token}


def check_session(telegram_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT s.user_id, u.username, u.balance, u.is_admin
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.telegram_id = ? AND s.expires_at > ?
        ORDER BY s.created_at DESC LIMIT 1
    ''', (telegram_id, datetime.now()))

    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "user_id": result[0],
            "username": result[1],
            "balance": result[2],
            "is_admin": result[3]
        }
    return None


def logout_user(telegram_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM sessions WHERE telegram_id = ?',
                   (telegram_id, ))
    conn.commit()
    conn.close()


def get_user_balance(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id, ))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


def update_balance(user_id, amount, transaction_type, description):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE users SET balance = balance + ? WHERE id = ?
    ''', (amount, user_id))

    cursor.execute(
        '''
        INSERT INTO transactions (user_id, amount, transaction_type, description)
        VALUES (?, ?, ?, ?)
    ''', (user_id, amount, transaction_type, description))

    conn.commit()
    conn.close()


# Keys Management
def add_key_to_stock(duration_days, key_value=None):
    conn = get_connection()
    cursor = conn.cursor()

    if not key_value:
        key_value = generate_key()

    try:
        cursor.execute(
            '''
            INSERT INTO keys_stock (key_value, duration_days)
            VALUES (?, ?)
        ''', (key_value, duration_days))
        conn.commit()
        key_id = cursor.lastrowid
        conn.close()
        return True, key_value
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Key already exists"


def get_available_key(duration_days):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT id, key_value FROM keys_stock
        WHERE duration_days = ? AND is_sold = 0
        LIMIT 1
    ''', (duration_days, ))

    result = cursor.fetchone()
    conn.close()

    return result if result else None


def sell_key(key_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE keys_stock SET is_sold = 1, sold_to = ?, sold_at = ?
        WHERE id = ?
    ''', (user_id, datetime.now(), key_id))

    cursor.execute(
        '''
        SELECT key_value, duration_days FROM keys_stock WHERE id = ?
    ''', (key_id, ))

    result = cursor.fetchone()
    conn.commit()
    conn.close()

    return result


def get_stock_count():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT duration_days, COUNT(*) FROM keys_stock
        WHERE is_sold = 0
        GROUP BY duration_days
    ''')

    results = cursor.fetchall()
    conn.close()

    return {row[0]: row[1] for row in results}


def record_purchase(user_id, key_id, amount, duration_days):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        INSERT INTO purchases (user_id, key_id, amount, duration_days)
        VALUES (?, ?, ?, ?)
    ''', (user_id, key_id, amount, duration_days))

    conn.commit()
    conn.close()


# Admin Functions
def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, username, balance, is_active, created_at, last_login
        FROM users WHERE is_admin = 0
    ''')

    results = cursor.fetchall()
    conn.close()

    return results


def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT id, username, balance, is_active FROM users WHERE username = ?
    ''', (username, ))

    result = cursor.fetchone()
    conn.close()

    return result


def toggle_user_status(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE users SET is_active = NOT is_active WHERE id = ?
    ''', (user_id, ))

    conn.commit()
    conn.close()


def reset_user_device(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE users SET device_id = NULL, telegram_id = NULL WHERE id = ?
    ''', (user_id, ))

    cursor.execute('DELETE FROM sessions WHERE user_id = ?', (user_id, ))

    conn.commit()
    conn.close()


def get_statistics():
    conn = get_connection()
    cursor = conn.cursor()

    stats = {}

    cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 0')
    stats['total_users'] = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM keys_stock WHERE is_sold = 0')
    stats['keys_in_stock'] = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM purchases')
    stats['total_sales'] = cursor.fetchone()[0]

    cursor.execute('SELECT SUM(amount) FROM purchases')
    result = cursor.fetchone()[0]
    stats['total_revenue'] = result if result else 0

    conn.close()

    return stats
