# database.py
import sqlite3
import hashlib
import os
import config # <-- IMPORT CONFIG TO ACCESS ADMIN CREDENTIALS

# This is the correct, permanent path. Do not change.
DATABASE_URL = '/data/bot_database.db'

# --- Database Connection ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initializes the database, creates tables, and creates the initial admin user if needed."""
    print("Checking/creating database tables...")
    conn = get_db_connection()
    # Create tables if they don't exist
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

    # ---------------------------------------------------------------- #
    # --- THIS IS THE CRITICAL LOGIC THAT WAS MISSING --- #
    # ---------------------------------------------------------------- #
    try:
        cursor = conn.cursor()
        # Check if any users exist in the database
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        # If the database is new (0 users) AND the admin credentials are set in the environment
        if user_count == 0 and config.ADMIN_USERNAME and config.ADMIN_PASSWORD:
            print(f"--- NO USERS FOUND ---")
            print(f"Creating initial admin user '{config.ADMIN_USERNAME}' from environment variables...")
            
            password_hash = hash_password(config.ADMIN_PASSWORD)
            conn.execute(
                'INSERT INTO users (username, password_hash, is_admin, is_active) VALUES (?, ?, ?, ?)',
                (config.ADMIN_USERNAME, password_hash, True, True)
            )
            conn.commit()
            print("✅ Initial admin user created successfully.")
        
    except sqlite3.Error as e:
        print(f"❌ Error during initial admin user creation: {e}")
    finally:
        # We always close the connection after we're done.
        conn.close()
    
    print("Database initialization process complete.")
    # ---------------------------------------------------------------- #

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
    session_data = conn.execute('SELECT s.user_id as id, s.username, u.is_admin, u.telegram_id FROM sessions s JOIN users u ON s.user_id = u.id WHERE s.telegram_id = ?', (telegram_id,)).fetchone()
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
        SELECT SUM(
            CASE duration_days 
            WHEN 1 THEN 2.00 
            WHEN 7 THEN 7.00 
            WHEN 30 THEN 15.00 
            ELSE 0 END
        ) 
        FROM license_keys WHERE is_used = TRUE
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

def toggle_user_active_status(user_id): pass 
def reset_user_device_id(user_id): pass
