# config.py
import os

# Bot Configuration
BOT_TOKEN = "8273127925:AAGPDqYbvIyvF2vXcHMM8dnk7luAqZwzowM"  # Get from @BotFather

# Admin Configuration
ADMIN_USERNAME = "El1don_07"
ADMIN_IDS = [6180001609]  # Add admin Telegram IDs here

# Database
DATABASE_NAME = "modder_ipa.db"

# Pricing (in USD)
PRICING = {
    "1_day": {"days": 1, "price": 2, "label": "1 Day - $2"},
    "7_days": {"days": 7, "price": 5, "label": "7 Days - $5"},
    "1_month": {"days": 30, "price": 8, "label": "1 Month - $8"}
}

# Payment Configuration
USDT_ADDRESS = "YOUR_USDT_TRC20_ADDRESS_HERE"  # TRC20 USDT Address

# Stock Mode: True = manual stock, False = auto-generate
STOCK_MODE = True