# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# --- Required Variables ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
# Your unique numeric Telegram user ID
# Can be a comma-separated list for multiple admins, e.g., "123,456"
ADMIN_IDS_str = os.getenv('ADMIN_IDS', "")
try:
    ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_str.split(',') if i]
except ValueError:
    print("Warning: ADMIN_IDS contains non-numeric values. Please check your environment variables.")
    ADMIN_IDS = []

# --- Admin Account Auto-Creation (NEW) ---
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# --- Optional / Customizable Variables ---
# Address for users to send USDT (TRC20) to
USDT_ADDRESS = os.getenv('USDT_ADDRESS', 'YOUR_USDT_TRC20_ADDRESS_HERE')

# Set to True to enable stock checking, False to allow unlimited purchases
STOCK_MODE = os.getenv('STOCK_MODE', 'True').lower() in ('true', '1', 't')

# --- Pricing Configuration ---
# You can add or remove plans here
# The key (e.g., 'plan1') is used internally.
# 'label' is what the user sees on the button.
# 'days' is the duration of the key.
# 'price' is the cost.
PRICING = {
    'plan1': {'label': '7 Days', 'days': 7, 'price': 5.00},
    'plan2': {'label': '30 Days', 'days': 30, 'price': 15.00},
    'plan3': {'label': '90 Days', 'days': 90, 'price': 30.00},
}
