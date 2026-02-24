# database.py
import sqlite3
import uuid
import logging
from datetime import datetime, timedelta, date
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
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                device_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_admin BOOLEAN DEFAULT 0,
                telegram_id INTEGER UNIQUE
            )
        ''')
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

# NEW FUNCTION: Finds an available key of a specific duration
def find_available_key(duration_days):
    """Finds an unused license key for a given duration."""
    conn = get_db_connection()
    try:
        key = conn.execute(
            'SELECT * FROM license_keys WHERE duration_days = ? AND user_id IS NULL LIMIT 1',
            (duration_days,)
        ).fetchone()
        return dict(key) if key else None
    finally:
        conn.close()

# NEW FUNCTION: Assigns a found key to a user
def assign_key_to_user(key_id, user_id):
    """Assigns a license key to a user and sets the activation date."""
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                'UPDATE license_keys SET user_id = ?, activation_date = ? WHERE id = ?',
                (user_id, date.today(), key_id)
            )
        return True
    except Exception as e:
        logging.error(f"Failed to assign key {key_id} to user {user_id}: {e}")
        return False

# --- All other database functions remain the same ---
def get_user(username, password):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            return dict(user)
        return None
    finally:
        conn.close()

def get_user_by_telegram_id(telegram_id):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def link_telegram_id(user_id, telegram_id):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('UPDATE users SET telegram_id = ? WHERE id = ?', (telegram_id, user_id))
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_session(telegram_id):
    user = get_user_by_telegram_id(telegram_id)
    if not user: return None
    user_id = user['id']
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM sessions WHERE user_id = ? AND expiry_date < ?', (user_id, datetime.now()))
        conn.commit()
        session = conn.execute('SELECT * FROM sessions WHERE user_id = ?', (user_id,)).fetchone()
        return user if session else None
    finally:
        conn.close()

def create_session(user_id):
    conn = get_db_connection()
    try:
        token = str(uuid.uuid4())
        expiry = datetime.now() + timedelta(hours=SESSION_LIFETIME_HOURS)
        conn.execute('INSERT OR REPLACE INTO sessions (session_token, user_id, expiry_date) VALUES (?, ?, ?)',
                     (token, user_id, expiry))
        conn.commit()
        return token
    finally:
        conn.close()

def invalidate_session(telegram_id):
    user = get_user_by_telegram_id(telegram_id)
    if not user: return False
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('DELETE FROM sessions WHERE user_id = ?', (user['id'],))
        return True
    finally:
        conn.close()

def promote_user_to_admin(telegram_id):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("UPDATE users SET is_admin = 1 WHERE telegram_id = ?", (telegram_id,))
        return True
    except Exception: return False

def create_user(username, password, is_admin=False):
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    conn = get_db_connection()
    try:
        with conn:
            conn.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)',
                         (username, password_hash.decode('utf-8'), 1 if is_admin else 0))
        return True, f"User '{username}' created."
    except sqlite3.IntegrityError: return False, f"User '{username}' already exists."
    finally: conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        return dict(user) if user else None
    finally: conn.close()

def update_balance(user_id, amount, transaction_type='debit'):
    conn = get_db_connection()
    try:
        current_balance = conn.execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()['balance']
        if transaction_type == 'debit' and current_balance < amount:
            return False, "Insufficient balance."
        
        with conn:
            if transaction_type == 'credit':
                conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))
            elif transaction_type == 'debit':
                conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, user_id))
        return True, "Balance updated."
    finally:
        conn.close()

# Other admin/utility functions remain unchanged
def get_all_users_paged(page=1, per_page=20):
    conn = get_db_connection()
    try:
        offset = (page - 1) * per_page
        users = conn.execute('SELECT * FROM users LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
        return [dict(u) for u in users]
    finally: conn.close()
def toggle_user_active_status(username): pass
def reset_user_device_id(username): pass
def get_setting(key):
    conn = get_db_connection()
    try:
        result = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
        return result['value'] if result else None
    finally: conn.close()
def set_setting(key, value): pass
def get_key_stock(): pass
def get_bot_stats(): pass
def bulk_add_keys(duration, keys): pass

# ADD THIS FUNCTION TO THE END OF database.py

def get_user_purchase_history(user_id):
    """Retrieves all keys purchased by a specific user."""
    conn = get_db_connection()
    try:
        history = conn.execute(
            'SELECT key, duration_days, activation_date FROM license_keys WHERE user_id = ? ORDER BY activation_date DESC',
            (user_id,)
        ).fetchall()
        return [dict(row) for row in history]
    finally:
        conn.close()
