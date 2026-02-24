def get_key_stock():
    """Retrieves the count of unused keys grouped by duration."""
    conn = get_db_connection()
    try:
        stock = conn.execute("""
            SELECT duration_days, COUNT(id) as count
            FROM license_keys
            WHERE user_id IS NULL
            GROUP BY duration_days
            ORDER BY duration_days
        """).fetchall()
        return [dict(row) for row in stock]
    finally:
        conn.close()

def get_bot_stats():
    """Retrieves various statistics for the admin panel."""
    conn = get_db_connection()
    try:
        total_users = conn.execute('SELECT COUNT(id) FROM users').fetchone()[0]
        active_users = conn.execute('SELECT COUNT(id) FROM users WHERE is_active = 1').fetchone()[0]
        total_keys_sold = conn.execute('SELECT COUNT(id) FROM license_keys WHERE user_id IS NOT NULL').fetchone()[0]
        keys_in_stock = conn.execute('SELECT COUNT(id) FROM license_keys WHERE user_id IS NULL').fetchone()[0]
        
        # Note: This is a simplified earnings calculation.
        # A more accurate way would be to sum up transaction logs.
        total_earnings = conn.execute("""
            SELECT SUM(p.price) 
            FROM license_keys lk
            JOIN pricing p ON lk.duration_days = p.days
            WHERE lk.user_id IS NOT NULL
        """).fetchone()[0] or 0.0

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_keys_sold": total_keys_sold,
            "total_earnings": total_earnings,
            "keys_in_stock": keys_in_stock,
        }
    finally:
        conn.close()

def bulk_add_keys(duration_days, keys):
    """Adds a list of keys for a specific duration to the database."""
    conn = get_db_connection()
    try:
        with conn:
            c = conn.cursor()
            keys_to_add = [(key, duration_days) for key in keys]
            c.executemany('INSERT INTO license_keys (key, duration_days) VALUES (?, ?)', keys_to_add)
        return len(keys_to_add)
    finally:
        conn.close()
