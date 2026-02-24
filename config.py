# config.py
import os

# --- Optional: Load .env file for local development ---
# This will try to load the .env file but will not cause an error if it's missing
# or if the python-dotenv library is not installed.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass # Silently continue if python-dotenv is not installed

# --- Required Variables ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
# Your unique numeric Telegram user ID
# Can be a comma-separated list for multiple admins, e.g., "123,456"
ADMIN_IDS_str = os.getenv('ADMIN_IDS', "")
try:
    ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_str.split(',') if i]
except (ValueError, TypeError):
    print("Warning: ADMIN_IDS contains non-numeric values or is not set. Please check your environment variables.")
    ADMIN_IDS = []

# --- Admin Account Auto-Creation ---
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# --- Bot Settings ---
# The username of the admin to contact for balance additions.
ADMIN_CONTACT_USERNAME = "@lostSick"

# Set to True to enable stock checking, False to allow unlimited purchases
STOCK_MODE = os.getenv('STOCK_MODE', 'True').lower() in ('true', '1', 't')

# --- Pricing Configuration (NEW PRICES) ---
# You can add or remove plans here.
# The key (e.g., 'plan1') is used internally.
# 'label' is what the user sees on the button.
# 'days' is the duration of the key.
# 'price' is the cost.
PRICING = {
    'plan1': {'label': '1 Day', 'days': 1, 'price': 2.00},
    'plan2': {'label': '7 Days', 'days': 7, 'price': 5.00},
    'plan3': {'label': '1 Month', 'days': 30, 'price': 8.00},
}
