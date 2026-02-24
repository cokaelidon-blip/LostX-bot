# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PRICING

def get_start_keyboard():
    """Returns the keyboard for the start message (not logged in)."""
    keyboard = [
        [InlineKeyboardButton("👤 Login", callback_data='login')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_dashboard_keyboard(is_admin=False):
    """
    Returns the main dashboard keyboard for logged-in users.
    'Buy Access' button has been removed as requested.
    """
    keyboard = [
        [
            InlineKeyboardButton("💰 Add Balance", callback_data='add_balance'),
            InlineKeyboardButton("⬇️ Download IPA", callback_data='download_ipa')
        ],
        [InlineKeyboardButton("🔒 Logout", callback_data='logout')]
    ]
    if is_admin:
        # Insert the Admin Panel button as the second button in the first row
        keyboard[0].insert(1, InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel'))
        
    return InlineKeyboardMarkup(keyboard)

def get_buy_menu_keyboard():
    """Returns the keyboard for the buy menu, constructed from PRICING config."""
    keyboard = []
    for key, plan in PRICING.items():
        # e.g., "7 Days - $5.00"
        text = f"{plan['label']} - ${plan['price']:.2f}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f'buy_plan_{key}')])

    keyboard.append([InlineKeyboardButton("« Back to Dashboard", callback_data='back_to_dashboard')])
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard():
    """Returns a simple Yes/No confirmation keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Confirm", callback_data='confirm_purchase'),
            InlineKeyboardButton("❌ No, Cancel", callback_data='back_to_dashboard')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_dashboard_keyboard():
    """Returns a simple 'Back to Dashboard' keyboard."""
    keyboard = [[InlineKeyboardButton("« Back to Dashboard", callback_data='back_to_dashboard')]]
    return InlineKeyboardMarkup(keyboard)

# --- Admin Keyboards ---

def get_admin_panel_keyboard():
    """Returns the main admin panel keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("👥 Users", callback_data='admin_users'),
            InlineKeyboardButton("🔑 Keys", callback_data='admin_keys')
        ],
