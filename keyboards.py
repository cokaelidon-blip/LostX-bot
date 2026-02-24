# keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import PRICING

def get_start_keyboard():
    """Keyboard for users who are not logged in. This provides the 'Login' button."""
    keyboard = [[InlineKeyboardButton("➡️ Login", callback_data='login')]]
    return InlineKeyboardMarkup(keyboard)

def get_dashboard_keyboard(is_admin=False):
    """Main keyboard for logged-in users."""
    keyboard = [
        [InlineKeyboardButton("📱 Modder IPA Menu", callback_data='modder_ipa_menu')],
        [InlineKeyboardButton("💰 Check Balance", callback_data='check_balance'), InlineKeyboardButton("📜 Purchase History", callback_data='history')],
        [InlineKeyboardButton("🚪 Logout", callback_data='logout')]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel')])
    return InlineKeyboardMarkup(keyboard)

def get_ipa_menu_keyboard():
    """Keyboard for the IPA menu, shown after clicking 'Modder IPA Menu'."""
    keyboard = [
        # --- THIS IS THE CHANGE ---
        [InlineKeyboardButton("🛒 Buy key", callback_data='buy_key_menu')],
        [InlineKeyboardButton("⬇️ Download IPA", callback_data='download_ipa')],
        [InlineKeyboardButton("⬅️ Back to Dashboard", callback_data='back_to_dashboard')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_buy_key_keyboard():
    """Generates a keyboard with all available pricing plans."""
    keyboard = []
    # Buttons are now generated based on the PRICING dictionary in config.py
    for plan_id, details in PRICING.items():
        button_text = f"{details['label']} - ${details['price']:.2f}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'buy_{plan_id}')])
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data='modder_ipa_menu')])
    return InlineKeyboardMarkup(keyboard)

# --- Admin Keyboards ---

def get_admin_panel_keyboard():
    """Keyboard for the main admin panel."""
    keyboard = [
        [InlineKeyboardButton("👥 Users", callback_data='admin_users'), InlineKeyboardButton("🔑 Keys", callback_data='admin_keys')],
        [InlineKeyboardButton("📊 Stats", callback_data='admin_stats'), InlineKeyboardButton("🔗 Set IPA Link", callback_data='admin_set_ipa_link')],
        [InlineKeyboardButton("⬅️ Back to User Dashboard", callback_data='back_to_dashboard')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_users_keyboard():
    """Keyboard for user management in the admin panel."""
    keyboard = [
        [InlineKeyboardButton("➕ Create User", callback_data='admin_create_user'), InlineKeyboardButton("💸 Add Balance", callback_data='admin_add_balance')],
        [InlineKeyboardButton("❌ Remove User", callback_data='admin_remove_user')],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keys_keyboard():
    """Keyboard for key management in the admin panel."""
    keyboard = [
        [InlineKeyboardButton("➕ Add Keys", callback_data='admin_add_keys'), InlineKeyboardButton("📦 View Stock", callback_data='view_stock')],
        [InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data='admin_panel')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_cancel_admin_action_keyboard():
    """A generic keyboard with a single 'Cancel' button for admin conversations."""
    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data='cancel_admin_action')]]
    return InlineKeyboardMarkup(keyboard)

def get_bulk_add_duration_keyboard():
    """Keyboard to select key duration for bulk adding."""
    keyboard = []
    for plan_id, details in PRICING.items():
        button_text = f"{details['days']}-Day Keys"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'add_keys_for_{details["days"]}')])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel_admin_action')])
    return InlineKeyboardMarkup(keyboard)
