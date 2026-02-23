# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PRICING

# Main Menu Keyboards


def get_start_keyboard():
    keyboard = [[
        InlineKeyboardButton("➡️ Login", callback_data="login"),
        InlineKeyboardButton("📋 Register", callback_data="register")
    ]]
    return InlineKeyboardMarkup(keyboard)


def get_dashboard_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("🔑 Modder IPA", callback_data="modder_ipa")],
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("📜 History", callback_data="history")
        ], [InlineKeyboardButton("🚪 Logout", callback_data="logout")]
    ]
    if is_admin:
        keyboard.append([
            InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")
        ])
    return InlineKeyboardMarkup(keyboard)


def get_back_keyboard():
    keyboard = [[
        InlineKeyboardButton("⬅️ Back to Dashboard",
                             callback_data="dashboard")
    ]]
    return InlineKeyboardMarkup(keyboard)


def get_cancel_keyboard():
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)


# User Flow Keyboards


def get_modder_ipa_keyboard():
    keyboard = [
        [InlineKeyboardButton("🛒 Buy Key", callback_data="buy_menu")],
        [InlineKeyboardButton("🔗 Get IPA Link", callback_data="ipa_link")],
        [
            InlineKeyboardButton("⬅️ Back to Dashboard",
                                 callback_data="dashboard")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_pricing_keyboard():
    keyboard = [
        [
            InlineKeyboardButton(PRICING["1_day"]["label"],
                                 callback_data="buy_1_day")
        ],
        [
            InlineKeyboardButton(PRICING["7_days"]["label"],
                                 callback_data="buy_7_days")
        ],
        [
            InlineKeyboardButton(PRICING["1_month"]["label"],
                                 callback_data="buy_1_month")
        ],
        [
            InlineKeyboardButton("⬅️ Back to Dashboard",
                                 callback_data="dashboard")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_purchase_keyboard(plan_key):
    keyboard = [[
        InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{plan_key}"),
        InlineKeyboardButton("❌ Cancel", callback_data="modder_ipa")
    ]]
    return InlineKeyboardMarkup(keyboard)


# Admin Keyboards


def get_admin_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            InlineKeyboardButton("🔑 Keys Stock", callback_data="admin_keys")
        ],
        [
            InlineKeyboardButton("➕ Create User",
                                 callback_data="admin_create_user"),
            InlineKeyboardButton("💵 Add Balance",
                                 callback_data="admin_add_balance")
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("🔗 Set IPA Link",
                                 callback_data="admin_set_link")
        ], [InlineKeyboardButton("⬅️ Back", callback_data="dashboard")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_keys_management_keyboard():
    """
    MODIFIED: Replaced individual key add buttons with a single "Add Custom Keys" button.
    """
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Custom Keys",
                                 callback_data="add_custom_keys_start")
        ],
        [InlineKeyboardButton("📦 View Stock", callback_data="view_stock")],
        [InlineKeyboardButton("⬅️ Back to Admin", callback_data="admin_panel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_duration_selection_keyboard():
    """
    NEW: Keyboard to ask admin which duration the bulk keys are for.
    """
    keyboard = [
        [
            InlineKeyboardButton("1 Day", callback_data="duration_select_1"),
            InlineKeyboardButton("7 Days", callback_data="duration_select_7"),
            InlineKeyboardButton("30 Days", callback_data="duration_select_30")
        ], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_bulk_add")]
    ]
    return InlineKeyboardMarkup(keyboard)
