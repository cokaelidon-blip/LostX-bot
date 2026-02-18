# config.py
import os

# Bot Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8273127925:AAGPDqYbvIyvF2vXcHMM8dnk7luAqZwzowM')

# Admin Configuration
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'El1don_07')

# Multiple Admin IDs - Add IDs separated by commas in Railway
# Example: ADMIN_IDS = "6180001609,123456789"
ADMIN_IDS_ENV = os.environ.get('ADMIN_IDS', '6180001609')
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_ENV.split(',') if id.strip()]

# Database
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///modder_ipa.db')
DATABASE_NAME = "modder_ipa.db"

# Pricing (in USD)
PRICING = {
    "1_day": {"days": 1, "price": 2, "label": "1 Day - $2"},
    "7_days": {"days": 7, "price": 5, "label": "7 Days - $5"},
    "1_month": {"days": 30, "price": 8, "label": "1 Month - $8"}
}

# Payment Configuration
USDT_ADDRESS = os.environ.get('USDT_ADDRESS', 'YOUR_USDT_TRC20_ADDRESS_HERE')

# Stock Mode: True = manual stock, False = auto-generate
STOCK_MODE = True
