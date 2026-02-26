# database.py
import sqlite3
import hashlib
import logging
import datetime
from config import ADMIN_USERNAME, ADMIN_PASSWORD, ADMIN_IDS # --- FIX 1: Import ADMIN_IDS

# --- Database Setup ---
DB_NAME = 'bot_database.db'
SESSIONS = {} # In-memory session storage

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    """Hashes a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_database():
    """Initializes the database tables and creates the primary admin user if they don't exist."""
    logging.info("Checking/creating database tables...")
    conn = get_db_connection()
    c = conn.cursor()
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    balance REAL DEFAULT 0.0,
                    is_admin INTEGER DEFAULT 0
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS keys (
                    id INTEGER PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    duration_days INTEGER NOT NULL,
                    is_used INTEGER DEFAULT 0,
                    user_id INTEGER,
                    activation_date TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )''')
    
    # Create the primary admin user from environment variables if they don't exist
    if ADMIN_USERNAME and ADMIN_PASSWORD:
        c.execute("SELECT id FROM users WHERE username = ?", (ADMIN_USERNAME,))
        if c.fetchone() is None:
            c.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                      (ADMIN_USERNAME, hash_password(ADMIN_PASSWORD), 1))
            logging.info(f"Primary admin user '{ADMIN_USERNAME}' created.")
            
    conn.commit()
    conn.close()
    logging.info("Database tables checked/created successfully.")
    logging.info("Database initialization process complete.")

# --- Session Management ---

def create_session(telegram_id: int, user_data: sqlite3.Row):
    """Creates a session for a logged-in user."""
    # --- FIX 2: This is the core logic fix ---
    # Check if the user's telegram_id is in the ADMIN_IDS set from config.py
    is_admin_from_env = telegram_id in ADMIN_IDS

    SESSIONS[telegram_id] = {
        'id': user_data['id'],
        'username': user_data['username'],
        # The user is an admin if their DB flag is set OR their ID is in ADMIN_IDS
        'is_admin': user_data['is_admin'] or is_admin_from_env
    }
    logging.info(f"Session created for user '{user_data['username']}' (ID: {telegram_id}). Admin status: {SESSIONS[telegram_id]['is_admin']}")

def check_session(telegram_id: int):
    """Checks if a user has an active session."""
    return SESSIONS.get(telegram_id)

def clear_session(telegram_id: int):
    """Clears a user's session (logout)."""
    if telegram_id in SESSIONS:
        del SESSIONS[telegram_id]

# --- User Functions ---

def create_user(username, password, is_admin=False):
    """Creates a new user in the database."""
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                     (username, hash_password(password), 1 if is_admin else 0))
        conn.commit()
        return True, f"✅ User '{username}' created successfully."
    except sqlite3.IntegrityError:
        return False, f"❌ User '{username}' already exists."
    finally:
        conn.close()

def get_user_by_username(username: str):
    """Fetches a user by their username."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def get_user_by_telegram_id(telegram_id: int):
    """Fetches a user by their Telegram ID."""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()
    conn.close()
    return user

def update_balance(user_id: int, amount: float, transaction_type: str = 'credit'):
    """Updates a user's balance. 'credit' adds, 'debit' subtracts."""
    conn = get_db_connection()
    if transaction_type == 'credit':
        conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user_id))
    elif transaction_type == 'debit':
        conn.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def delete_user_by_username(username: str):
    """Deletes a user from the database by username."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if user:
        cursor.execute("DELETE FROM users WHERE id = ?", (user['id'],))
        conn.commit()
        conn.close()
        return True, f"✅ User '{username}' has been deleted."
    else:
        conn.close()
        return False, f"❌ User '{username}' not found."

# --- Key Functions ---

def bulk_add_keys(duration: int, keys: list):
    """Adds a list of keys for a specific duration to the database."""
    conn = get_db_connection()
    keys_to_insert = [(key, duration) for key in keys]
    added_count = 0
    try:
        cursor = conn.cursor()
        cursor.executemany("INSERT OR IGNORE INTO keys (key, duration_days) VALUES (?, ?)", keys_to_insert)
        added_count = cursor.rowcount
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error during bulk key add: {e}")
    finally:
        conn.close()
    return added_count

def find_available_key(duration: int):
    """Finds an unused key for a specific duration."""
    conn = get_db_connection()
    key = conn.execute("SELECT * FROM keys WHERE duration_days = ? AND is_used = 0 LIMIT 1", (duration,)).fetchone()
    conn.close()
    return key

def assign_key_to_user(key_id: int, user_id: int):
    """Assigns a key to a user, marking it as used."""
    conn = get_db_connection()
    today = datetime.date.today().isoformat()
    conn.execute("UPDATE keys SET is_used = 1, user_id = ?, activation_date = ? WHERE id = ?", (user_id, today, key_id))
    # Also associate the telegram_id with the user account if it's not already there
    user = conn.execute("SELECT telegram_id FROM users WHERE id = ?", (user_id,)).fetchone()
    if user and user['telegram_id'] is None:
        session_telegram_id = next((tid for tid, s in SESSIONS.items() if s['id'] == user_id), None)
        if session_telegram_id:
            conn.execute("UPDATE users SET telegram_id = ? WHERE id = ?", (session_telegram_id, user_id))
    conn.commit()
    conn.close()

def get_user_purchase_history(user_id: int):
    """Retrieves all keys purchased by a user."""
    conn = get_db_connection()
    history = conn.execute("SELECT key, duration_days, activation_date FROM keys WHERE user_id = ? ORDER BY activation_date DESC", (user_id,)).fetchall()
    conn.close()
    return history

# --- Settings & Stats ---

def get_setting(key: str, default=None):
    """Gets a value from the settings table."""
    conn = get_db_connection()
    setting = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return setting['value'] if setting else default

def set_setting(key: str, value: str):
    """Sets a value in the settings table."""
    conn = get_db_connection()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_key_stock():
    """Gets the count of unused keys, grouped by duration."""
    conn = get_db_connection()
    stock = conn.execute("""
        SELECT duration_days, COUNT(*) as count 
        FROM keys 
        WHERE is_used = 0 
        GROUP BY duration_days
    """).fetchall()
    conn.close()
    return stock

def get_bot_stats():
    """Retrieves general statistics for the admin panel."""
    conn = get_db_connection()
    total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_keys_sold = conn.execute("SELECT COUNT(*) FROM keys WHERE is_used = 1").fetchone()[0]
    keys_in_stock = conn.execute("SELECT COUNT(*) FROM keys WHERE is_used = 0").fetchone()[0]
    
    # Calculate earnings by joining keys and pricing
    # This is a simplified approach; a real app might store the price at time of sale.
    earnings_query = """
        SELECT SUM(p.price) 
        FROM keys k
        JOIN (
            SELECT 1 as days, 2.00 as price
            UNION ALL SELECT 7, 5.00
            UNION ALL SELECT 30, 8.00
        ) p ON k.duration_days = p.days
        WHERE k.is_used = 1
    """
    total_earnings_row = conn.execute(earnings_query).fetchone()
    total_earnings = total_earnings_row[0] if total_earnings_row and total_earnings_row[0] is not None else 0.0

    conn.close()
    return {
        'total_users': total_users,
        'total_keys_sold': total_keys_sold,
        'total_earnings': total_earnings,
        'keys_in_stock': keys_in_stock
    }
