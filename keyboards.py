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
        [
            InlineKeyboardButton("📊 Statistics", callback_data='admin_stats'),
            InlineKeyboardButton("🔗 Set IPA Link", callback_data='admin_set_ipa_link')
        ],
        [InlineKeyboardButton("« Back to Dashboard", callback_data='back_to_dashboard')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_users_keyboard():
    """Returns the keyboard for the user management section."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Create User", callback_data='admin_create_user'),
            InlineKeyboardButton("💰 Add Balance", callback_data='admin_add_balance')
        ],
        [InlineKeyboardButton("« Back to Admin Panel", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keys_keyboard():
    """Returns the keyboard for the key management section."""
    keyboard = [
        [
            InlineKeyboardButton("📦 View Stock", callback_data='view_stock'),
            InlineKeyboardButton("➕ Add Custom Keys", callback_data='admin_add_custom_keys')
        ],
        [InlineKeyboardButton("« Back to Admin Panel", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_bulk_add_duration_keyboard():
    """Returns a keyboard for selecting key duration during bulk add."""
    keyboard = []
    for key, plan in PRICING.items():
        text = f"{plan['label']}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f'add_keys_duration_{plan["days"]}')])
    keyboard.append([InlineKeyboardButton("« Cancel", callback_data='admin_keys')])
    return InlineKeyboardMarkup(keyboard)

def get_cancel_admin_action_keyboard():
    """Returns a simple cancel button for admin conversations."""
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel_admin_action')]]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_bulk_add_keyboard():
    """Returns a 'Back' button for the bulk add conversation."""
    # This is the line that had the syntax error. It's now fixed.
    keyboard = [[InlineKeyboardButton("« Back to Key Menu", callback_data='admin_keys')]]
    return InlineKeyboardMarkup(keyboard)
