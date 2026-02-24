# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Bot Configuration ---
# Get your bot token from your environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")

# --- Pricing Configuration ---
# Define the pricing plans for license keys.
# 'plan_id': { 'days': duration_in_days, 'price': cost_in_dollars, 'label': text_on_button }
PRICING = {
    'plan_1': {'days': 1,  'price': 2.00, 'label': '1-Day Access'},
    'plan_2': {'days': 7,  'price': 5.00, 'label': '7-Day Access'},
    'plan_3': {'days': 30, 'price': 8.00, 'label': '30-Day Access'},
}

# --- Admin Credentials (Loaded from environment variables) ---
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
