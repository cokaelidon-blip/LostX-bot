# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from config import PRICING, ADMIN_USERNAME

def get_start_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔐 Login", callback_data="login")],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_dashboard_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("🔑 Modder IPA", callback_data="modder_ipa")],
        [InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("📜 Purchase History", callback_data="history")],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton("🚪 Logout", callback_data="logout")]
    ]
    
    if is_admin:
        keyboard.insert(0, [InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def get_pricing_keyboard():
    keyboard = []
    for key, value in PRICING.items():
        keyboard.append([
            InlineKeyboardButton(
                f"📅 {value['label']}", 
                callback_data=f"buy_{key}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)

def get_confirm_purchase_keyboard(plan_key):
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Purchase", callback_data=f"confirm_{plan_key}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="modder_ipa")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dashboard")]]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")],
        [InlineKeyboardButton("🔑 Manage Keys Stock", callback_data="admin_keys")],
        [InlineKeyboardButton("💵 Add Balance to User", callback_data="admin_add_balance")],
        [InlineKeyboardButton("➕ Create New User", callback_data="admin_create_user")],
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="dashboard")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_keys_management_keyboard():
    keyboard = [
        [InlineKeyboardButton("➕ Add 1 Day Key", callback_data="add_key_1")],
        [InlineKeyboardButton("➕ Add 7 Days Key", callback_data="add_key_7")],
        [InlineKeyboardButton("➕ Add 1 Month Key", callback_data="add_key_30")],
        [InlineKeyboardButton("📦 View Stock", callback_data="view_stock")],
        [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_keyboard():
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]
    return InlineKeyboardMarkup(keyboard)