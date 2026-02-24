# database.py
import sqlite3
import uuid
import logging
from datetime import datetime, timedelta
import bcrypt

DATABASE_FILE = 'bot_database.db'
SESSION_LIFETIME_HOURS = 24

def get_db_connection():
    """Creates and returns a database connection."""
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initializes the database and creates tables if they don't exist."""
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys = ON;")

        # Add telegram_id column if it doesn't exist
        try:
            c.execute("ALTER TABLE users ADD COLUMN telegram_id INTEGER UNIQUE")
            logging.info("Column 'telegram_id' added to 'users' table.")
        except sqlite3.OperationalError:
            pass  # Column already exists

        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                device_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_admin BOOLEAN DEFAULT 0
            )
        ''')
        # The ALTER TABLE command for telegram_id is above

        c.execute('''
            CREATE TABLE IF NOT EXISTS license_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                duration_days INTEGER NOT NULL,
                user_id INTEGER,
                activation_date DATE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL UNIQUE,
                expiry_date DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS pricing (days INTEGER PRIMARY KEY, price REAL NOT NULL, label TEXT NOT NULL)
        ''')

        conn.commit()
        logging.info("Database tables checked/created successfully.")
    finally:
        conn.close()


def get_user(username, password):
    """Retrieves a user and verifies their password."""
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return dict(user)
        return None
    finally:
        conn.close()

def get_user_by_telegram_id(telegram_id):
    """Retrieves a user by their Telegram ID."""
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def link_telegram_id(user_id, telegram_id):
    """Links a telegram_id to an existing user account."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('UPDATE users SET telegram_id = ? WHERE id = ?', (telegram_id, user_id))
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"Attempted to link a telegram_id ({telegram_id}) that is already in use.")
        return False
    finally:
        conn.close()

def check_session(telegram_id):
    """Checks for a valid session using a Telegram ID."""
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return None

    user_id = user['id']
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM sessions WHERE user_id = ? AND expiry_date < ?', (user_id, datetime.now()))
        conn.commit()
        session = conn.execute('SELECT * FROM sessions WHERE user_id = ?', (user_id,)).fetchone()

        if session:
            # Session exists, return user info
            return user
        return None
    finally:
        conn.close()

def create_session(user_id):
    """Creates a new session for a user."""
    conn = get_db_connection()
    try:
        token = str(uuid.uuid4())
        expiry = datetime.now() + timedelta(hours=SESSION_LIFETIME_HOURS)
        # Use INSERT OR REPLACE to handle logins on new devices, invalidating the old session.
        conn.execute('INSERT OR REPLACE INTO sessions (session_token, user_id, expiry_date) VALUES (?, ?, ?)',
                     (token, user_id, expiry))
        conn.commit()
        return token
    finally:
        conn.close()

def invalidate_session(telegram_id):
    """Invalidates a session using a Telegram ID."""
    user = get_user_by_telegram_id(telegram_id)
    if not user:
        return False

    conn = get_db_connection()
    try:
        with conn:
            conn.execute('DELETE FROM sessions WHERE user_id = ?', (user['id'],))
        logging.info(f"Session invalidated for telegram_id: {telegram_id}")
        return True
    finally:
        conn.close()

def promote_user_to_admin(telegram_id):
    """Promotes an existing user to admin status via their Telegram ID."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE users SET is_admin = 1 WHERE telegram_id = ?", (telegram_id,))
        logging.info(f"User with telegram_id {telegram_id} promoted to admin.")
        return True
    except Exception as e:
        logging.error(f"Failed to promote user {telegram_id} to admin: {e}")
        return False

# --- All other functions from the previous version remain the same ---
# (create_user, get_user_by_username, get_all_users_paged, update_balance, etc.)

def create_user(username, password, is_admin=False):
    """Creates a new user with a hashed password."""
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                'INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                (username, password_hash.decode('utf-8'), 1 if is_admin else 0)
            )
        return True, f"User '{username}' created successfully."
    except sqlite3.IntegrityError:
        return False, f"Error: User '{username}' already exists."
    finally:
        conn.close()

def get_user_by_username(username):
    """Retrieves a user by their username without password check."""
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def get_all_users_paged(page=1, per_page=20):
    conn = get_db_connection()
    try:
        users = conn.execute(
            'SELECT id, username, balance, is_active, is_admin FROM users ORDER BY id LIMIT ? OFFSET ?',
            (per_page, (page - 1) * per_page)
        ).fetchall()
        return [dict(user) for user in users]
    finally:
        conn.close()

def update_balance(user_id, amount, transaction_type, reason):
    conn = get_db_connection()
    try:
        with conn:
            if transaction_type == 'credit':
                conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))
            elif transaction_type == 'debit':
                conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, user_id))
        logging.info(f"Balance updated for user {user_id}: {transaction_type} ${amount}. Reason: {reason}")
        return True
    finally:
        conn.close()

def toggle_user_active_status(username):
    conn = get_db_connection()
    try:
        user = get_user_by_username(username)
        if not user: return False, f"User '{username}' not found."
        new_status = not user['is_active']
        with conn:
            conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (1 if new_status else 0, user['id']))
        status_text = "activated" if new_status else "deactivated"
        return True, f"User '{username}' has been {status_text}."
    finally:
        conn.close()

def reset_user_device_id(username):
    conn = get_db_connection()
    try:
        user = get_user_by_username(username)
        if not user: return False, f"User '{username}' not found."
        with conn:
            conn.execute('UPDATE users SET device_id = NULL WHERE id = ?', (user['id'],))
        return True, f"Device ID for user '{username}' has been reset."
    finally:
        conn.close()

def get_setting(key):
    conn = get_db_connection()
    try:
        result = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        return result['value'] if result else None
    finally:
        conn.close()

def set_setting(key, value):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        return True
    finally:
        conn.close()

def get_key_stock():
    conn = get_db_connection()
    try:
        stock = conn.execute("""
            SELECT duration_days, COUNT(id) as count FROM license_keys WHERE user_id IS NULL GROUP BY duration_days ORDER BY duration_days
        """).fetchall()
        return [dict(row) for row in stock]
    finally:
        conn.close()

def get_bot_stats():
    conn = get_db_connection()
    try:
        total_users = conn.execute('SELECT COUNT(id) FROM users').fetchone()[0] or 0
        active_users = conn.execute('SELECT COUNT(id) FROM users WHERE is_active = 1').fetchone()[0] or 0
        total_keys_sold = conn.execute('SELECT COUNT(id) FROM license_keys WHERE user_id IS NOT NULL').fetchone()[0] or 0
        keys_in_stock = conn.execute('SELECT COUNT(id) FROM license_keys WHERE user_id IS NULL').fetchone()[0] or 0
        total_earnings_query = conn.execute("SELECT SUM(p.price) FROM pricing WHERE days IN (SELECT duration_days FROM license_keys WHERE user_id IS NOT NULL)").fetchone()
        total_earnings = total_earnings_query[0] if total_earnings_query and total_earnings_query[0] is not None else 0.0
        return {"total_users": total_users, "active_users": active_users, "total_keys_sold": total_keys_sold, "total_earnings": total_earnings, "keys_in_stock": keys_in_stock}
    finally:
        conn.close()

def bulk_add_keys(duration_days, keys):
    conn = get_db_connection()
    try:
        with conn:
            keys_to_add = [(key, duration_days) for key in keys]
            conn.executemany('INSERT INTO license_keys (key, duration_days) VALUES (?, ?)', keys_to_add)
        return len(keys_to_add)
    except Exception as e:
        logging.error(f"Error in bulk_add_keys: {e}")
        return 0
    finally:
        conn.close()
