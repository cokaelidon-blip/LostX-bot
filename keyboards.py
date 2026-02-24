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
            InlineKeyboardButton("📜 History", callback_data='history'),
            InlineKeyboardButton("🔒 Logout", callback_data='logout')
        ]
    ]
    if is_admin:
        # Add the Admin Panel button for admins
        keyboard.insert(1, [InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel')])
    return InlineKeyboardMarkup(keyboard)

def get_modder_ipa_keyboard():
    """Returns the keyboard for the 'Modder IPA' menu, including buy options."""
    keyboard = []
    # Create a button for each plan in the PRICING config
    for plan_key, plan_details in PRICING.items():
        text = f"Buy {plan_details['label']} - ${plan_details['price']:.2f}"
        # The callback_data will be e.g., 'buy_plan_plan1'
        keyboard.append([InlineKeyboardButton(text, callback_data=f'buy_plan_{plan_key}')])
    
    keyboard.append([InlineKeyboardButton("⬇️ Download IPA", callback_data='download_ipa')])
    keyboard.append([InlineKeyboardButton("« Back to Dashboard", callback_data='back_to_dashboard')])
    return InlineKeyboardMarkup(keyboard)

def get_back_to_dashboard_keyboard():
    """Returns a simple 'Back to Dashboard' keyboard."""
    keyboard = [[InlineKeyboardButton("« Back to Dashboard", callback_data='back_to_dashboard')]]
    return InlineKeyboardMarkup(keyboard)

# --- Admin Keyboards (Unchanged for now, but keeping for future steps) ---
def get_admin_panel_keyboard():
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
