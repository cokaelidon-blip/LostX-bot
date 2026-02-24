# handlers/admin.py
import html
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (check_session, get_all_users, get_user_by_username,
                      create_user, update_balance, toggle_user_status,
                      reset_user_device, get_stock_count, get_statistics,
                      update_setting, add_key_to_stock)
from keyboards import (get_admin_panel_keyboard, get_admin_users_keyboard,
                       get_admin_keys_keyboard, get_key_duration_keyboard,
                       get_back_to_dashboard_keyboard)

# Conversation states for admin actions
CREATE_USER_USERNAME, CREATE_USER_PASSWORD = range(10, 12)
ADD_BALANCE_USERNAME, ADD_BALANCE_AMOUNT = range(12, 14)
SET_IPA_LINK = range(14, 15)
SELECT_KEY_DURATION, RECEIVE_KEYS_LIST = range(15, 17)


async def check_admin_session(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    """Checks if the user is an admin and has an active session."""
    query = update.callback_query
    # For commands, the user is in update.message, not update.callback_query
    user = update.effective_user

    session = check_session(user.id)
    if not session or not session.get('is_admin'):
        if query:
            await query.answer("You are not authorized to do this.", show_alert=True)
        else: # For commands
            await update.message.reply_text("You are not authorized to do this.")
        return None
    if query:
        await query.answer()
    return session


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return
    query = update.callback_query
    text = "👑 <b>Admin Panel</b>\n\nWelcome to the admin control center."
    await query.edit_message_text(text,
                                  reply_markup=get_admin_panel_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return
    query = update.callback_query
    users = get_all_users()
    user_list = "\n".join(
        [f"👤 `{u['username']}` | 💳 ${u['balance']:.2f} | {'✅ Active' if u['is_active'] else '❌ Inactive'}" for u in users]
    ) if users else "No users found."
    text = f"👥 <b>User Management</b>\n\n{user_list}"
    await query.edit_message_text(text,
                                  reply_markup=get_admin_users_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def admin_keys_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return
    query = update.callback_query
    text = "🔑 <b>Key Management</b>\n\nManage license keys and IPA link."
    await query.edit_message_text(text, reply_markup=get_admin_keys_keyboard())


async def view_stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return
    query = update.callback_query
    stock = get_stock_count()
    stock_text = "\n".join([f"• {days}-day keys: {count}" for days, count in stock.items()]) if stock else "No keys in stock."
    text = f"📈 <b>Current Stock</b>\n\n{stock_text}"
    await query.edit_message_text(text,
                                  reply_markup=get_admin_panel_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return
    query = update.callback_query
    stats = get_statistics()
    text = f"""
📊 <b>Bot Statistics</b>

• Total Users: <b>{stats.get('total_users', 0)}</b>
• Keys in Stock: <b>{stats.get('keys_in_stock', 0)}</b>
• Total Sales: <b>{stats.get('total_sales', 0)}</b>
• Total Revenue: <b>${stats.get('total_revenue', 0):.2f}</b>
    """
    await query.edit_message_text(text,
                                  reply_markup=get_admin_panel_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels any admin conversation."""
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("Admin action cancelled.", reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END


# --- Create User Conversation ---
async def admin_create_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.edit_message_text("Enter the username for the new user:")
    return CREATE_USER_USERNAME

async def create_user_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_username'] = update.message.text
    await update.message.reply_text("Enter a password for the new user:")
    return CREATE_USER_PASSWORD

async def create_user_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data['new_username']
    password = update.message.text
    success, message = create_user(username, password)
    await update.message.reply_text(f"✅ {message}" if success else f"❌ {message}")
    context.user_data.clear()
    # This part can be improved to show the admin menu again
    return ConversationHandler.END


# --- Add Balance Conversation ---
async def admin_add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.edit_message_text("Enter the username to add balance to:")
    return ADD_BALANCE_USERNAME

async def add_balance_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    user = get_user_by_username(username)
    if not user:
        await update.message.reply_text("User not found. Action cancelled.")
        return ConversationHandler.END
    context.user_data['balance_user_id'] = user['id']
    await update.message.reply_text(f"Current balance for {username} is ${user['balance']:.2f}. Enter the amount to add:")
    return ADD_BALANCE_AMOUNT

async def add_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        user_id = context.user_data['balance_user_id']
        update_balance(user_id, amount, 'deposit', 'Admin deposit')
        await update.message.reply_text(f"✅ Successfully added ${amount:.2f} to the user's balance.")
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
    context.user_data.clear()
    return ConversationHandler.END


# --- Commands for user management ---
async def toggle_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return
    try:
        username = context.args[0]
        user = get_user_by_username(username)
        if not user:
            await update.message.reply_text("User not found.")
            return
        toggle_user_status(user['id'])
        await update.message.reply_text(f"Toggled status for user {username}.")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /toggleuser <username>")


async def reset_device_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return
    try:
        username = context.args[0]
        user = get_user_by_username(username)
        if not user:
            await update.message.reply_text("User not found.")
            return
        reset_user_device(user['id'])
        await update.message.reply_text(f"Reset device binding for user {username}.")
    except (IndexError, ValueError):
        await update.message.reply_.text("Usage: /resetdevice <username>")

# --- Set IPA Link Conversation ---
async def admin_set_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.edit_message_text("Please send the new IPA download link.")
    return SET_IPA_LINK

async def admin_receive_new_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_link = update.message.text
    update_setting('ipa_download_link', new_link)
    await update.message.reply_text("✅ IPA download link has been updated.")
    return ConversationHandler.END

# --- Bulk Add Keys Conversation ---
async def add_custom_keys_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin_session(update, context): return ConversationHandler.END
    query = update.callback_query
    await query.edit_message_text("Select the duration for the keys you want to add:", reply_markup=get_key_duration_keyboard())
    return SELECT_KEY_DURATION

async def select_key_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    duration = int(query.data.split('_')[-1])
    context.user_data['key_duration'] = duration
    await query.edit_message_text(f"Adding {duration}-day keys. Now, send a list of keys, one per line.")
    return RECEIVE_KEYS_LIST

async def receive_keys_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = update.message.text.splitlines()
    duration = context.user_data['key_duration']
    added_count = 0
    failed_keys = []
    for key in keys:
        if key.strip():
            success, _ = add_key_to_stock(duration, key.strip())
            if success:
                added_count += 1
            else:
                failed_keys.append(key)
    
    response = f"✅ Added {added_count} new keys to stock.\n"
    if failed_keys:
        response += f"❌ Failed to add {len(failed_keys)} keys (duplicates): {', '.join(failed_keys)}"

    await update.message.reply_text(response)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_bulk_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("Action cancelled.", reply_markup=get_admin_keys_keyboard())
    return ConversationHandler.END
