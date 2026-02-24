# config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

# --- Telegram Bot Token ---
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables. Please set it.")

# --- Admin Configuration ---
ADMIN_IDS = os.getenv('ADMIN_IDS')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# --- Database Configuration ---
# THE FINAL, PERMANENT FIX:
# We are now pointing to a file inside the persistent /data volume.
DATABASE_URL = '/data/bot_database.db'

# --- Pricing Configuration ---
PRICING = {
    'plan_1': {
        'label': '1-Day Access',
        'days': 1,
        'price': 2.00
    },
    'plan_2': {
        'label': '7-Day Access',
        'days': 7,
        'price': 7.00
    },
    'plan_3': {
        'label': '30-Day Access',
        'days': 30,
        'price': 15.00
    }
}
