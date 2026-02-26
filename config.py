# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Bot Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Pricing Configuration ---
PRICING = {
    'plan_1': {'days': 1,  'price': 2.00, 'label': '1-Day Access'},
    'plan_2': {'days': 7,  'price': 5.00, 'label': '7-Day Access'},
    'plan_3': {'days': 30, 'price': 8.00, 'label': '30-Day Access'},
}

# --- Admin Credentials (Loaded from environment variables) ---
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# --- THIS IS THE FIX ---
# This code reads the ADMIN_IDS variable, splits it by commas,
# and creates a set of integer IDs for fast lookups.
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = {int(uid.strip()) for uid in admin_ids_str.split(',') if uid.strip().isdigit()}
