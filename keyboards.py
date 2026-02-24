# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PRICING

def get_start_keyboard():
    """Returns the keyboard for the initial start message (not logged in)."""
    keyboard = [[InlineKeyboardButton("👤 Login", callback_data='login')]]
    return InlineKeyboardMarkup(keyboard)

def get_main_dashboard_keyboard(is_admin=False):
    """Returns the main dashboard keyboard for a logged-in user."""
    keyboard = [
        [InlineKeyboardButton("📱 Modder IPA", callback_data='modder_ipa_menu')],
        [
            InlineKeyboardButton("💰 Check Balance", callback_data='check_balance'),
            InlineKeyboardButton("📜 History", callback_data='history')
        ],
        [InlineKeyboardButton("🔒 Logout", callback_data='logout')]
    ]
    if is_admin:
        keyboard.insert(1, [InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel')])
    return InlineKeyboardMarkup(keyboard)

def get_modder_ipa_keyboard():
    """Returns the keyboard for the 'Modder IPA' menu."""
    keyboard = []
    for plan_key, plan_details in PRICING.items():
        text = f"Buy {plan_details['label']} - ${plan_details['price']:.2f}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f'buy_plan_{plan_key}')])
    
    keyboard.append([InlineKeyboardButton("⬇️ Download IPA", callback_data='download_ipa')])
    keyboard.append([InlineKeyboardButton("« Back to Dashboard", callback_data='back_to_dashboard')])
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
        # --- NEW BUTTON ADDED HERE ---
        [InlineKeyboardButton("➖ Remove User", callback_data='admin_remove_user')],
        [InlineKeyboardButton("« Back to Admin Panel", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keys_keyboard():
    """Returns the keyboard for the key management section."""
    keyboard = [
        [
            InlineKeyboardButton("📦 View Stock", callback_data='view_stock'),
            InlineKeyboardButton("➕ Add Keys", callback_data='admin_add_keys')
        ],
        [InlineKeyboardButton("« Back to Admin Panel", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_bulk_add_duration_keyboard():
    """Returns a keyboard for selecting key duration during bulk add."""
    keyboard = []
    for key, plan in PRICING.items():
        text = f"Add for: {plan['label']}"
        # Corrected callback data format
        keyboard.append([InlineKeyboardButton(text, callback_data=f'add_keys_for_{plan["days"]}')])
    keyboard.append([InlineKeyboardButton("« Cancel", callback_data='cancel_admin_action')])
    return InlineKeyboardMarkup(keyboard)

def get_cancel_admin_action_keyboard():
    """Returns a simple cancel button for admin conversations."""
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel_admin_action')]]
    return InlineKeyboardMarkup(keyboard)
