# handlers/admin.py
import html
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (get_all_users_paged, get_key_stock, get_bot_stats,
                      create_user, get_user_by_username, update_balance,
                      set_setting, bulk_add_keys,
                      toggle_user_active_status, reset_user_device_id)
from keyboards import (get_admin_panel_keyboard, get_admin_users_keyboard,
                       get_admin_keys_keyboard, get_cancel_admin_action_keyboard,
                       get_bulk_add_duration_keyboard)
from config import ADMIN_IDS

# Conversation states
(CREATE_USER_USERNAME, CREATE_USER_PASSWORD, ADD_BALANCE_USERNAME, ADD_BALANCE_AMOUNT,
 SET_IPA_LINK, SELECT_KEY_DURATION, RECEIVE_KEYS_LIST) = range(10, 17)

# --- Main Admin Panel ---
async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "👑 *Admin Panel*\n\nSelect a management category."
    await query.edit_message_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode=ParseMode.MARKDOWN)

# --- User Management ---
async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    users = get_all_users_paged()
    user_list_text = "\n".join([
        f"`{u['id']}`: {html.escape(u['username'])} {'👑' if u['is_admin'] else ''} - ${u['balance']:.2f}"
        for u in users
    ]) if users else "No users found."
    text = f"👥 *User Management*\n\n{user_list_text}"
    await query.edit_message_text(text, reply_markup=get_admin_users_keyboard(), parse_mode=ParseMode.MARKDOWN)

# --- Key Management ---
async def admin_keys_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔑 *Key Management*", reply_markup=get_admin_keys_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def view_stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stock = get_key_stock()
    stock_text = "\n".join([f"• {item['duration_days']}-Day Keys: {item['count']}" for item in stock]) if stock else "No keys in stock."
    text = f"📦 *Key Stock*\n\n{stock_text}"
    await query.edit_message_text(text, reply_markup=get_admin_keys_keyboard(), parse_mode=ParseMode.MARKDOWN)

# --- Bot Statistics ---
async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = get_bot_stats()
    text = f"""📊 *Bot Statistics*
- Total Users: `{stats['total_users']}`
- Total Keys Sold: `{stats['total_keys_sold']}`
- Total Earnings: `${stats['total_earnings']:.2f}`
- Keys in Stock: `{stats['keys_in_stock']}`"""
    await query.edit_message_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode=ParseMode.MARKDOWN)

# --- Generic Cancel ---
async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("👑 *Admin Panel*\n\nAction cancelled.", reply_markup=get_admin_panel_keyboard(), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

# --- Conversation: Create User ---
async def admin_create_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Enter username for new user:", reply_markup=get_cancel_admin_action_keyboard())
    return CREATE_USER_USERNAME

async def create_user_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_username'] = update.message.text
    await update.message.reply_text("Enter password for new user:")
    return CREATE_USER_PASSWORD

async def create_user_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data['new_username']
    password = update.message.text
    success, message = create_user(username, password)
    await update.message.reply_text(f"{'✅' if success else '❌'} {message}")
    context.user_data.clear()
    await update.message.reply_text("Returning to admin panel...", reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END

# --- Conversation: Add Balance ---
async def admin_add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Enter username to add balance to:", reply_markup=get_cancel_admin_action_keyboard())
    return ADD_BALANCE_USERNAME

async def add_balance_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user_by_username(update.message.text)
    if not user:
        await update.message.reply_text("User not found. Try again:", reply_markup=get_cancel_admin_action_keyboard())
        return ADD_BALANCE_USERNAME
    context.user_data['user_to_credit'] = user
    await update.message.reply_text(f"Enter amount to add to {user['username']}:")
    return ADD_BALANCE_AMOUNT

async def add_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = context.user_data['user_to_credit']
    try:
        amount = float(update.message.text)
        update_balance(user['id'], amount, 'credit')
        await update.message.reply_text(f"✅ Added ${amount:.2f} to {user['username']}'s balance.")
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
        return ADD_BALANCE_AMOUNT
    context.user_data.clear()
    await update.message.reply_text("Returning to admin panel...", reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END

# --- Conversation: Set IPA Link ---
async def admin_set_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Send the new IPA download link:", reply_markup=get_cancel_admin_action_keyboard())
    return SET_IPA_LINK

async def admin_receive_new_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    set_setting('ipa_download_link', update.message.text)
    await update.message.reply_text("✅ IPA link updated.", reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END

# --- Conversation: Bulk Add Keys ---
async def admin_add_keys_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Select duration for keys:", reply_markup=get_bulk_add_duration_keyboard())
    return SELECT_KEY_DURATION

async def select_key_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    duration = int(update.data.split('_')[-1])
    context.user_data['bulk_add_duration'] = duration
    await update.callback_query.edit_message_text(f"Send a list of {duration}-day keys, one per line.")
    return RECEIVE_KEYS_LIST

async def receive_keys_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    duration = context.user_data['bulk_add_duration']
    keys = [k.strip() for k in update.message.text.split('\n') if k.strip()]
    count = bulk_add_keys(duration, keys)
    await update.message.reply_text(f"✅ Added {count} new {duration}-day keys.", reply_markup=get_admin_keys_keyboard())
    context.user_data.clear()
    return ConversationHandler.END
