# handlers/admin.py
from telegram import Update
from telegram.ext import (ContextTypes, ConversationHandler,
                          CallbackQueryHandler, MessageHandler, filters)

# --- MODIFIED IMPORTS ---
from database import (check_session, create_user, get_all_users,
                      get_user_by_username, update_balance, add_key_to_stock,
                      get_stock_count, get_statistics, toggle_user_status,
                      reset_user_device, update_setting)
from keyboards import (get_admin_keyboard, get_keys_management_keyboard,
                       get_back_keyboard, get_cancel_keyboard,
                       get_duration_selection_keyboard)  # <-- MODIFIED
# --- END MODIFIED IMPORTS ---

# --- MODIFIED CONVERSATION STATES ---
CREATE_USER_USERNAME, CREATE_USER_PASSWORD = range(2)
ADD_BALANCE_USERNAME, ADD_BALANCE_AMOUNT = range(2, 4)
SET_IPA_LINK = range(4, 5)

# NEW States for adding bulk custom keys
SELECT_KEY_DURATION, RECEIVE_KEYS_LIST = range(5, 7)
# --- END MODIFIED CONVERSATION STATES ---


def is_admin(session):
    return session and session.get('is_admin')


async def admin_panel_callback(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await query.edit_message_text("❌ Access denied. Admin only.")
        return

    await query.edit_message_text("⚙️ *Admin Panel*\n\nSelect an option:",
                                  reply_markup=get_admin_keyboard(),
                                  parse_mode='Markdown')


async def admin_users_callback(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return

    users = get_all_users()

    if not users:
        text = "👥 *User Management*\n\nNo users found."
    else:
        text = "👥 *User Management*\n\n"
        for user in users[:20]:  # Limit to 20 users
            user_id, username, balance, is_active, created, last_login = user
            status = "✅" if is_active else "❌"
            text += f"{status} *{username}* - ${balance:.2f}\n"

    text += "\n\nTo manage a user, use commands:\n"
    text += "`/toggleuser username` - Enable/Disable\n"
    text += "`/resetdevice username` - Reset device binding"

    await query.edit_message_text(text,
                                  reply_markup=get_admin_keyboard(),
                                  parse_mode='Markdown')


async def admin_keys_callback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return

    await query.edit_message_text("🔑 *Keys Stock Management*\n\nSelect an option:",
                                  reply_markup=get_keys_management_keyboard(),
                                  parse_mode='Markdown')


async def view_stock_callback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return

    stock = get_stock_count()

    text = "📦 *Current Stock*\n\n"
    text += f"• 1 Day Keys: *{stock.get(1, 0)}*\n"
    text += f"• 7 Days Keys: *{stock.get(7, 0)}*\n"
    text += f"• 1 Month Keys: *{stock.get(30, 0)}*\n"
    text += f"\n*Total: {sum(stock.values())} keys*"

    await query.edit_message_text(text,
                                  reply_markup=get_keys_management_keyboard(),
                                  parse_mode='Markdown')


async def admin_stats_callback(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return

    stats = get_statistics()

    text = f"""
📊 *Bot Statistics*

👥 Total Users: *{stats['total_users']}*
🔑 Keys in Stock: *{stats['keys_in_stock']}*
🛒 Total Sales: *{stats['total_sales']}*
💰 Total Revenue: *${stats['total_revenue']:.2f}*
    """

    await query.edit_message_text(text,
                                  reply_markup=get_admin_keyboard(),
                                  parse_mode='Markdown')


# --- NEW: Bulk Key Addition Conversation ---

async def add_custom_keys_start(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    """Starts the conversation to add custom keys."""
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END

    await query.edit_message_text(
        "*Step 1: Select Key Duration*\n\n"
        "Please choose the duration for the keys you are about to add:",
        reply_markup=get_duration_selection_keyboard(),
        parse_mode='Markdown')

    return SELECT_KEY_DURATION


async def select_key_duration(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    """Saves the selected duration and asks for the keys."""
    query = update.callback_query
    await query.answer()

    duration = int(query.data.replace("duration_select_", ""))
    context.user_data['bulk_add_duration'] = duration

    await query.edit_message_text(
        f"*Step 2: Paste Your Keys*\n\n"
        f"You have selected *{duration} days* duration.\n\n"
        f"Please send a message containing the list of keys. "
        f"Each key must be on a *new line*.",
        parse_mode='Markdown')

    return RECEIVE_KEYS_LIST


async def receive_keys_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives the list of keys, processes them, and saves to the database."""
    duration = context.user_data.get('bulk_add_duration')
    if not duration:
        await update.message.reply_text(
            "Error: Duration not set. Please start over.")
        return ConversationHandler.END

    keys_text = update.message.text
    # Split by new line and filter out any empty lines
    keys_list = [key.strip() for key in keys_text.splitlines() if key.strip()]

    if not keys_list:
        await update.message.reply_text(
            "No valid keys found in your message. Please try again.")
        return RECEIVE_KEYS_LIST

    # Inform the user that processing has started
    await update.message.reply_text(
        f"⏳ Processing {len(keys_list)} keys...")

    success_count = 0
    fail_count = 0
    failed_keys = []

    for key in keys_list:
        success, result = add_key_to_stock(duration, key_value=key)
        if success:
            success_count += 1
        else:
            fail_count += 1
            failed_keys.append(f"`{key}` ({result})")

    # Build the final report message
    report = f"✅ *Bulk Add Report*\n\n"
    report += f"Total keys processed: *{len(keys_list)}*\n"
    report += f"Successfully added: *{success_count}*\n"
    report += f"Failed (duplicates): *{fail_count}*\n"

    if failed_keys:
        report += "\n*Failed Keys:*\n" + "\n".join(failed_keys)

    await update.message.reply_text(report, parse_mode='Markdown')

    # Clean up and end conversation
    context.user_data.pop('bulk_add_duration', None)
    return ConversationHandler.END


async def cancel_bulk_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the bulk key addition process."""
    query = update.callback_query
    await query.answer()
    context.user_data.pop('bulk_add_duration', None)
    await query.edit_message_text("❌ Bulk key addition cancelled.",
                                  reply_markup=get_keys_management_keyboard())
    return ConversationHandler.END


# --- END: Bulk Key Addition Conversation ---


# Create User Conversation
async def admin_create_user_callback(update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END

    await query.edit_message_text(
        "➕ *Create New User*\n\nEnter the username for the new user:",
        parse_mode='Markdown')

    return CREATE_USER_USERNAME


async def create_user_username(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_username'] = update.message.text

    await update.message.reply_text("🔑 Now enter the password for this user:")

    return CREATE_USER_PASSWORD


async def create_user_password(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get('new_username')
    password = update.message.text

    try:
        await update.message.delete()
    except:
        pass

    success, result = create_user(username, password)

    if success:
        await update.message.reply_text(
            f"✅ *User Created Successfully!*\n\n"
            f"👤 Username: `{username}`\n"
            f"🔑 Password: `{password}`\n\n"
            f"Share these credentials with the user.",
            parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ Failed to create user: {result}")

    return ConversationHandler.END


# Add Balance Conversation
async def admin_add_balance_callback(update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END

    await query.edit_message_text("💵 *Add Balance*\n\nEnter the username:",
                                  parse_mode='Markdown')

    return ADD_BALANCE_USERNAME


async def add_balance_username(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    user = get_user_by_username(username)

    if not user:
        await update.message.reply_text(
            "❌ User not found. Please try again with /start")
        return ConversationHandler.END

    context.user_data['balance_user_id'] = user[0]
    context.user_data['balance_username'] = username

    await update.message.reply_text(
        f"👤 User: *{username}*\n"
        f"💰 Current Balance: *${user[2]:.2f}*\n\n"
        f"Enter the amount to add (in USD):",
        parse_mode='Markdown')

    return ADD_BALANCE_AMOUNT


async def add_balance_amount(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a number.")
        return ADD_BALANCE_AMOUNT

    user_id = context.user_data.get('balance_user_id')
    username = context.user_data.get('balance_username')

    update_balance(user_id, amount, 'admin_add', f'Added by admin')

    await update.message.reply_text(
        f"✅ *Balance Added Successfully!*\n\n"
        f"👤 User: *{username}*\n"
        f"💵 Amount Added: *${amount:.2f}*",
        parse_mode='Markdown')

    return ConversationHandler.END


async def cancel_admin_action(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action cancelled.")
    await update.message.reply_text("⚙️ *Admin Panel*\n\nSelect an option:",
                                    reply_markup=get_admin_keyboard(),
                                    parse_mode='Markdown')
    return ConversationHandler.END


# Command handlers for user management
async def toggle_user_command(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await update.message.reply_text("❌ Access denied.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /toggleuser username")
        return

    username = context.args[0]
    user = get_user_by_username(username)

    if not user:
        await update.message.reply_text("❌ User not found.")
        return

    toggle_user_status(user[0])

    await update.message.reply_text(f"✅ User *{username}* status toggled.",
                                    parse_mode='Markdown')


async def reset_device_command(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await update.message.reply_text("❌ Access denied.")
        return

    if not context.args:
        await update.message.reply_text("Usage: /resetdevice username")
        return

    username = context.args[0]
    user = get_user_by_username(username)

    if not user:
        await update.message.reply_text("❌ User not found.")
        return

    reset_user_device(user[0])

    await update.message.reply_text(
        f"✅ Device binding reset for *{username}*.", parse_mode='Markdown')


# Conversation for setting IPA Link
async def admin_set_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END

    await query.edit_message_text(
        "🔗 *Update IPA Link*\n\nPlease send me the new IPA link now. "
        "Send /cancel to abort.",
        parse_mode='Markdown')

    return SET_IPA_LINK


async def admin_receive_new_link(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    new_link = update.message.text

    update_setting('ipa_link', new_link)

    await update.message.reply_text(
        f"✅ *Link Updated Successfully!*\n\nNew link is now set.",
        parse_mode='Markdown')

    await update.message.reply_text("⚙️ *Admin Panel*\n\nSelect an option:",
                                    reply_markup=get_admin_keyboard(),
                                    parse_mode='Markdown')

    return ConversationHandler.END
