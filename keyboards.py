# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PRICING

def get_start_keyboard():
    """Returns the keyboard for the start message when the user is not logged in."""
    keyboard = [[InlineKeyboardButton("🔐 Login", callback_data='login')]]
    return InlineKeyboardMarkup(keyboard)

def get_dashboard_keyboard(is_admin=False):
    """Returns the main dashboard keyboard."""
    keyboard = [
        [InlineKeyboardButton("📱 Modder IPA", callback_data='modder_ipa')],
        [
            InlineKeyboardButton("💰 Balance", callback_data='balance'),
            InlineKeyboardButton("🛒 Buy Access", callback_data='buy_menu')
        ],
        [InlineKeyboardButton("📜 History", callback_data='history')],
        [InlineKeyboardButton("🔗 Get IPA Link", callback_data='ipa_link')],
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel')])
    keyboard.append([InlineKeyboardButton("🚪 Logout", callback_data='logout')])
    return InlineKeyboardMarkup(keyboard)

def get_buy_menu_keyboard():
    """Returns the keyboard for the buy menu."""
    keyboard = [[
        InlineKeyboardButton(data["label"], callback_data=f"buy_{key}")
    ] for key, data in PRICING.items()]
    keyboard.append([InlineKeyboardButton("⬅️ Back to Dashboard", callback_data='dashboard')])
    return InlineKeyboardMarkup(keyboard)

def get_confirmation_keyboard(plan_key):
    """Returns a confirmation keyboard for a purchase."""
    keyboard = [
        [InlineKeyboardButton("✅ Yes, I'm sure", callback_data=f"confirm_{plan_key}")],
        [InlineKeyboardButton("❌ Cancel", callback_data='buy_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_dashboard_keyboard():
    """Returns a simple 'Back to Dashboard' keyboard."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Dashboard", callback_data='dashboard')]])

def get_admin_panel_keyboard():
    """Returns the main admin panel keyboard."""
    keyboard = [
        [InlineKeyboardButton("👥 Users", callback_data='admin_users'), InlineKeyboardButton("🔑 Keys", callback_data='admin_keys')],
        [InlineKeyboardButton("📊 Statistics", callback_data='admin_stats'), InlineKeyboardButton("📈 View Stock", callback_data='view_stock')],
        [InlineKeyboardButton("⬅️ Back to Dashboard", callback_data='dashboard')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_users_keyboard():
    """Returns the keyboard for the admin users section."""
    keyboard = [
        [InlineKeyboardButton("➕ Create User", callback_data='admin_create_user')],
        [InlineKeyboardButton("💰 Add Balance", callback_data='admin_add_balance')],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keys_keyboard():
    """Returns the keyboard for the admin keys section."""
    keyboard = [
        [InlineKeyboardButton("➕ Add Custom Keys", callback_data='add_custom_keys_start')],
        [InlineKeyboardButton("🔗 Set IPA Link", callback_data='admin_set_link')],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)
    
def get_key_duration_keyboard():
    """Returns keyboard for selecting key duration."""
    keyboard = [[
        InlineKeyboardButton(data["label"], callback_data=f"duration_select_{data['days']}")
    ] for _, data in PRICING.items()]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel_bulk_add')])
    return InlineKeyboardMarkup(keyboard)
