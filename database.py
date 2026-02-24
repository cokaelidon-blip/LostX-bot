# database.py
import sqlite3
import hashlib
import os
# --- FIX #1: Corrected DATABASE_FILE to DATABASE_URL ---
from config import DATABASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_IDS

# --- Database Connection ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    # --- FIX #2: Corrected DATABASE_FILE to DATABASE_URL ---
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initializes the database and creates tables if they don't exist."""
    print("Checking/creating database tables...")
    conn = get_db_connection()
    # Check for settings table
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings';")
    if cursor.fetchone() is None:
        print("Creating tables...")
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                is_admin BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                device_id TEXT,
                telegram_id INTEGER UNIQUE
            );
            CREATE TABLE IF NOT EXISTS license_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                duration_days INTEGER NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                user_id INTEGER,
                activation_date TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                telegram_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                login_time TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        ''')
    print("Database tables checked/created successfully.")
    
    # --- Auto-Create/Link Admin Accounts ---
    if ADMIN_IDS and ADMIN_USERNAME:
        admin_ids_list = [int(i.strip()) for i in ADMIN_IDS.split(',')]
        for admin_tg_id in admin_ids_list:
            # Check if a user with this Telegram ID already exists
            user = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (admin_tg_id,)).fetchone()
            if user:
                # If user exists but is not admin, promote them
                if not user['is_admin']:
                    conn.execute('UPDATE users SET is_admin = TRUE WHERE telegram_id = ?', (admin_tg_id,))
                    print(f"Promoted existing user with Telegram ID {admin_tg_id} to admin.")
            else:
                # If no user with this Telegram ID, check for the admin username
                admin_user = conn.execute('SELECT * FROM users WHERE username = ?', (ADMIN_USERNAME,)).fetchone()
                if admin_user:
                    # If admin username exists but is not linked, link it
                    if admin_user['telegram_id'] is None:
                        conn.execute('UPDATE users SET telegram_id = ?, is_admin = TRUE WHERE username = ?', (admin_tg_id, ADMIN_USERNAME))
                        print(f"Linked existing admin account '{ADMIN_USERNAME}' to Telegram ID {admin_tg_id}.")
                else:
                    # If neither exists, create a new admin account
                    if ADMIN_PASSWORD:
                        password_hash = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()
                        conn.execute(
                            'INSERT INTO users (username, password_hash, is_admin, telegram_id) VALUES (?, ?, TRUE, ?)',
                            (ADMIN_USERNAME, password_hash, admin_tg_id)
                        )
                        print(f"Created new admin account '{ADMIN_USERNAME}' for Telegram ID {admin_tg_id}.")
        conn.commit()
    
    conn.close()

# --- Utility Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Session Management ---
def create_session(telegram_id, user):
    conn = get_db_connection()
    conn.execute('DELETE FROM sessions WHERE telegram_id = ?', (telegram_id,))
    conn.execute('INSERT INTO sessions (telegram_id, user_id, username) VALUES (?, ?, ?)',
                 (telegram_id, user['id'], user['username']))
    conn.commit()
    conn.close()

def check_session(telegram_id):
    conn = get_db_connection()
    session_data = conn.execute('SELECT s.user_id, s.username, u.is_admin, u.telegram_id FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.telegram_id = ?', (telegram_id,)).fetchone()
    conn.close()
    return dict(session_data) if session_data else None

def clear_session(telegram_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM sessions WHERE telegram_id = ?', (telegram_id,))
    conn.commit()
    conn.close()

# --- User Management ---
def create_user(username, password, is_admin=False, telegram_id=None):
    conn = get_db_connection()
    try:
        password_hash = hash_password(password)
        conn.execute(
            'INSERT INTO users (username, password_hash, is_admin, telegram_id) VALUES (?, ?, ?, ?)',
            (username, password_hash, is_admin, telegram_id)
        )
        conn.commit()
        return True, f"User '{username}' created successfully."
    except sqlite3.IntegrityError:
        return False, "Username or Telegram ID already exists."
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_telegram_id(telegram_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

def update_balance(user_id, amount, transaction_type='credit'):
    conn = get_db_connection()
    if transaction_type == 'credit':
        conn.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))
    elif transaction_type == 'debit':
        conn.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_all_users_paged(page=1, per_page=10):
    offset = (page - 1) * per_page
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, balance, is_admin, is_active FROM users ORDER BY id LIMIT ? OFFSET ?', (per_page, offset)).fetchall()
    conn.close()
    return [dict(row) for row in users]

# --- Key Management ---
def bulk_add_keys(duration, keys):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data_to_insert = [(key, duration) for key in keys]
        cursor.executemany('INSERT OR IGNORE INTO license_keys (key, duration_days) VALUES (?, ?)', data_to_insert)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()

def get_key_stock():
    conn = get_db_connection()
    stock = conn.execute(
        'SELECT duration_days, COUNT(*) as count FROM license_keys WHERE is_used = FALSE GROUP BY duration_days'
    ).fetchall()
    conn.close()
    return [dict(row) for row in stock]

def find_available_key(duration):
    conn = get_db_connection()
    key = conn.execute(
        'SELECT id, key FROM license_keys WHERE duration_days = ? AND is_used = FALSE LIMIT 1',
        (duration,)
    ).fetchone()
    conn.close()
    return dict(key) if key else None

def assign_key_to_user(key_id, user_id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE license_keys SET is_used = TRUE, user_id = ?, activation_date = DATE('now') WHERE id = ?",
        (user_id, key_id)
    )
    conn.commit()
    conn.close()

# --- Settings Management ---
def set_setting(key, value):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = get_db_connection()
    setting = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    conn.close()
    return setting['value'] if setting else default

# --- Stats & History ---
def get_bot_stats():
    conn = get_db_connection()
    stats = {}
    stats['total_users'] = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    stats['total_keys_sold'] = conn.execute('SELECT COUNT(*) FROM license_keys WHERE is_used = TRUE').fetchone()[0]
    total_earnings_query = conn.execute(
        """
        SELECT SUM(p.price) 
        FROM license_keys lk
        JOIN (
            SELECT 1 as duration, 2.00 as price
            UNION ALL SELECT 7, 7.00
            UNION ALL SELECT 30, 15.00
        ) p ON lk.duration_days = p.duration
        WHERE lk.is_used = TRUE
        """
    ).fetchone()[0]
    stats['total_earnings'] = total_earnings_query if total_earnings_query is not None else 0.0
    stats['keys_in_stock'] = conn.execute('SELECT COUNT(*) FROM license_keys WHERE is_used = FALSE').fetchone()[0]
    conn.close()
    return stats

def get_user_purchase_history(user_id):
    conn = get_db_connection()
    try:
        history = conn.execute(
            'SELECT key, duration_days, activation_date FROM license_keys WHERE user_id = ? ORDER BY activation_date DESC',
            (user_id,)
        ).fetchall()
        return [dict(row) for row in history]
    finally:
        conn.close()

def delete_user_by_username(username):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT id, is_admin FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            return False, "User not found."
            
        conn.execute('UPDATE license_keys SET user_id = NULL, activation_date = NULL WHERE user_id = ?', (user['id'],))
        conn.execute('DELETE FROM sessions WHERE user_id = ?', (user['id'],))
        conn.execute('DELETE FROM users WHERE id = ?', (user['id'],))
        conn.commit()
        return True, f"User '{username}' and all their data has been deleted."
    finally:
        conn.close()

# --- Admin Functions ---
def toggle_user_active_status(user_id):
    pass 
def reset_user_device_id(user_id):
    pass
