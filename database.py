# database.py
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse
import secrets
import hashlib
from datetime import datetime, timedelta
from config import DATABASE_URL


def get_connection():
    """Establishes a connection to the PostgreSQL database."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    result = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        dbname=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    return conn


def init_database():
    """Initializes the database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            device_id TEXT,
            balance NUMERIC(10, 2) DEFAULT 0.00,
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
            last_login TIMESTAMP WITH TIME ZONE
        );
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            telegram_id BIGINT,
            session_token TEXT UNIQUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
            expires_at TIMESTAMP WITH TIME ZONE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS keys_stock (
            id SERIAL PRIMARY KEY,
            key_value TEXT UNIQUE NOT NULL,
            duration_days INTEGER NOT NULL,
            is_sold BOOLEAN DEFAULT FALSE,
            sold_to INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
            sold_at TIMESTAMP WITH TIME ZONE,
            FOREIGN KEY (sold_to) REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS purchases (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            key_id INTEGER,
            amount NUMERIC(10, 2),
            duration_days INTEGER,
            purchased_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY (key_id) REFERENCES keys_stock(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            amount NUMERIC(10, 2),
            transaction_type TEXT,
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
    """)

    conn.commit()
    cursor.close()
    conn.close()


def _execute(query, params=None, fetch=None):
    """Helper function to execute queries."""
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cursor.execute(query, params)
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()
        else:
            result = None # For INSERT, UPDATE, DELETE
        conn.commit()
        return result
    finally:
        cursor.close()
        conn.close()

# --- NEW FUNCTION ---
def promote_user_to_admin(telegram_id):
    """Sets the is_admin flag to TRUE for a user based on their Telegram ID."""
    _execute("UPDATE users SET is_admin = TRUE WHERE telegram_id = %s;", (telegram_id,))

def update_setting(key, value):
    _execute("INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;", (key, value))

def get_setting(key):
    result = _execute("SELECT value FROM settings WHERE key = %s;", (key,), fetch="one")
    return result['value'] if result else None

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_session_token():
    return secrets.token_hex(32)

def generate_key():
    return f"MODDER-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"

def create_user(username, password, is_admin=False):
    try:
        _execute("INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s);", (username, hash_password(password), is_admin))
        return True, "User created"
    except psycopg2.IntegrityError:
        return False, "Username already exists"

def authenticate_user(username, password, telegram_id):
    user = _execute("SELECT id, password_hash, device_id, is_active FROM users WHERE username = %s;", (username,), fetch="one")
    if not user: return False, "Invalid username or password"
    if not user['is_active']: return False, "Account is deactivated"
    if user['password_hash'] != hash_password(password): return False, "Invalid username or password"
    if user['device_id'] and user['device_id'] != str(telegram_id): return False, "This account is bound to another device"
    
    if not user['device_id']:
        _execute("UPDATE users SET device_id = %s, telegram_id = %s WHERE id = %s;", (str(telegram_id), telegram_id, user['id']))

    _execute("UPDATE users SET last_login = (NOW() AT TIME ZONE 'utc'), telegram_id = %s WHERE id = %s;", (telegram_id, user['id']))

    session_token = generate_session_token()
    expires_at = datetime.utcnow() + timedelta(days=7)
    _execute("INSERT INTO sessions (user_id, telegram_id, session_token, expires_at) VALUES (%s, %s, %s, %s);", (user['id'], telegram_id, session_token, expires_at))

    return True, {"user_id": user['id'], "session_token": session_token}

def check_session(telegram_id):
    query = """
        SELECT s.user_id, u.username, u.balance, u.is_admin
        FROM sessions s JOIN users u ON s.user_id = u.id
        WHERE s.telegram_id = %s AND s.expires_at > (NOW() AT TIME ZONE 'utc')
        ORDER BY s.created_at DESC LIMIT 1;
    """
    return _execute(query, (telegram_id,), fetch="one")

def logout_user(telegram_id):
    _execute('DELETE FROM sessions WHERE telegram_id = %s;', (telegram_id,))

def get_user_balance(user_id):
    result = _execute('SELECT balance FROM users WHERE id = %s;', (user_id,), fetch="one")
    return result['balance'] if result else 0

def update_balance(user_id, amount, transaction_type, description):
    _execute("UPDATE users SET balance = balance + %s WHERE id = %s;", (amount, user_id))
    _execute("INSERT INTO transactions (user_id, amount, transaction_type, description) VALUES (%s, %s, %s, %s);", (user_id, amount, transaction_type, description))

def add_key_to_stock(duration_days, key_value=None):
    if not key_value: key_value = generate_key()
    try:
        _execute("INSERT INTO keys_stock (key_value, duration_days) VALUES (%s, %s);", (key_value, duration_days))
        return True, key_value
    except psycopg2.IntegrityError:
        return False, "Key already exists"

def get_available_key(duration_days):
    return _execute("SELECT id, key_value FROM keys_stock WHERE duration_days = %s AND is_sold = FALSE LIMIT 1;", (duration_days,), fetch="one")

def sell_key(key_id, user_id):
    _execute("UPDATE keys_stock SET is_sold = TRUE, sold_to = %s, sold_at = (NOW() AT TIME ZONE 'utc') WHERE id = %s;", (user_id, key_id))
    return _execute("SELECT key_value, duration_days FROM keys_stock WHERE id = %s;", (key_id,), fetch="one")

def get_stock_count():
    results = _execute("SELECT duration_days, COUNT(*) as count FROM keys_stock WHERE is_sold = FALSE GROUP BY duration_days;", fetch="all")
    return {row['duration_days']: row['count'] for row in results} if results else {}

def record_purchase(user_id, key_id, amount, duration_days):
    _execute("INSERT INTO purchases (user_id, key_id, amount, duration_days) VALUES (%s, %s, %s, %s);", (user_id, key_id, amount, duration_days))

def get_all_users():
    return _execute("SELECT id, username, balance, is_active, created_at, last_login FROM users WHERE is_admin = FALSE;", fetch="all")

def get_user_by_username(username):
    return _execute("SELECT id, username, balance, is_active FROM users WHERE username = %s;", (username,), fetch="one")

def toggle_user_status(user_id):
    _execute("UPDATE users SET is_active = NOT is_active WHERE id = %s;", (user_id,))

def reset_user_device(user_id):
    _execute("UPDATE users SET device_id = NULL, telegram_id = NULL WHERE id = %s;", (user_id,))
    _execute('DELETE FROM sessions WHERE user_id = %s;', (user_id,))

def get_statistics():
    stats = {}
    stats['total_users'] = _execute('SELECT COUNT(*) as count FROM users WHERE is_admin = FALSE;', fetch="one")['count']
    stats['keys_in_stock'] = _execute('SELECT COUNT(*) as count FROM keys_stock WHERE is_sold = FALSE;', fetch="one")['count']
    stats['total_sales'] = _execute('SELECT COUNT(*) as count FROM purchases;', fetch="one")['count']
    total_revenue = _execute('SELECT SUM(amount) as sum FROM purchases;', fetch="one")['sum']
    stats['total_revenue'] = total_revenue if total_revenue else 0
    return stats
