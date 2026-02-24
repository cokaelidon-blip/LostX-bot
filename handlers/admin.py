# handlers/admin.py
import html
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (create_user, get_user_by_username, update_balance, set_setting, 
                      bulk_add_keys, get_key_stock, get_bot_stats, delete_user_by_username)
from keyboards import (get_admin_panel_keyboard, get_admin_users_keyboard, get_admin_keys_keyboard,
                       get_cancel_admin_action_keyboard, get_bulk_add_duration_keyboard)

# Conversation states for admin actions
(A_USERNAME, A_PASSWORD, A_GET_USERNAME_BALANCE, A_GET_AMOUNT, A_GET_LINK, 
 A_CHOOSE_DURATION, A_GET_KEYS, A_GET_USERNAME_REMOVE) = range(10, 18)

# --- Admin Panel Navigation ---

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "👑 *Admin Panel*\n\nWelcome, Admin. Select an option."
    await query.edit_message_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "👥 *User Management*\n\nCreate, remove, or modify users."
    await query.edit_message_text(text, reply_markup=get_admin_users_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def admin_keys_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "🔑 *Key Management*\n\nAdd new license keys or view current stock."
    await query.edit_message_text(text, reply_markup=get_admin_keys_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Action cancelled.", reply_markup=get_admin_panel_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# --- Create User Conversation ---

async def admin_create_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Enter the username for the new user:", reply_markup=get_cancel_admin_action_keyboard())
    return A_USERNAME

async def admin_receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_username'] = update.message.text
    await update.message.reply_text("Enter the password for the new user:")
    return A_PASSWORD

async def admin_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data['new_username']
    password = update.message.text
    success, message = create_user(username, password)
    await update.message.reply_text(message)
    await update.message.reply_text("Returning to the admin panel.", reply_markup=get_admin_panel_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# --- Add Balance Conversation ---

async def admin_add_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Enter the username to add balance to:", reply_markup=get_cancel_admin_action_keyboard())
    return A_GET_USERNAME_BALANCE

async def admin_receive_username_for_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text
    user = get_user_by_username(username)
    if not user:
        await update.message.reply_text("User not found. Action cancelled.", reply_markup=get_admin_panel_keyboard())
        return ConversationHandler.END
    context.user_data['user_to_credit'] = user
    await update.message.reply_text(f"User '{username}' found. Enter the amount to add (e.g., 10.50):")
    return A_GET_AMOUNT

async def admin_receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = context.user_data['user_to_credit']
    try:
        amount = float(update.message.text)
        if amount <= 0: raise ValueError
        update_balance(user['id'], amount)
        await update.message.reply_text(f"✅ Successfully added ${amount:.2f} to {user['username']}'s balance.")
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a positive number.")
    
    await update.message.reply_text("Returning to the admin panel.", reply_markup=get_admin_panel_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# --- Set IPA Link Conversation ---

async def admin_set_ipa_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please send the new IPA download link:", reply_markup=get_cancel_admin_action_keyboard())
    return A_GET_LINK

async def admin_receive_ipa_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    link = update.message.text
    set_setting('ipa_download_link', link)
    await update.message.reply_text("✅ IPA download link updated successfully.", reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END

# --- Add Keys Conversation ---

async def admin_add_keys_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Select the duration for the new keys:", reply_markup=get_bulk_add_duration_keyboard())
    return A_CHOOSE_DURATION

async def admin_choose_key_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    duration = int(query.data.split('_')[-1])
    context.user_data['key_duration'] = duration
    await query.edit_message_text(f"Enter the {duration}-day keys, one per line:")
    return A_GET_KEYS

async def admin_receive_keys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    duration = context.user_data['key_duration']
    keys = update.message.text.strip().split('\n')
    added_count = bulk_add_keys(duration, keys)
    await update.message.reply_text(f"✅ Process complete. Added {added_count} new unique keys.", reply_markup=get_admin_panel_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# --- View Stock & Stats ---

async def view_stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stock = get_key_stock()
    if not stock:
        stock_text = "No keys in stock."
    else:
        stock_list = [f"- {item['count']} x {item['duration_days']}-day keys" for item in stock]
        stock_text = "📦 *Current Key Stock*\n\n" + "\n".join(stock_list)
    await query.edit_message_text(stock_text, reply_markup=get_admin_keys_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = get_bot_stats()
    stats_text = (
        f"📊 *Bot Statistics*\n\n"
        f"Total Users: {stats['total_users']}\n"
        f"Keys Sold: {stats['total_keys_sold']}\n"
        f"Total Earnings: ${stats['total_earnings']:.2f}\n"
        f"Keys in Stock: {stats['keys_in_stock']}"
    )
    await query.edit_message_text(stats_text, reply_markup=get_admin_panel_keyboard(), parse_mode=ParseMode.MARKDOWN)

# --- Remove User Conversation ---

async def admin_remove_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Enter the username of the user to remove:", reply_markup=get_cancel_admin_action_keyboard())
    return A_GET_USERNAME_REMOVE

async def admin_confirm_remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip()
    success, message = delete_user_by_username(username)
    await update.message.reply_text(message)
    await update.message.reply_text("Returning to the admin panel.", reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END
