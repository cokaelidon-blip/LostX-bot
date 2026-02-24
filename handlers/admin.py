# handlers/admin.py
import html
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (get_all_users_paged, get_key_stock, get_bot_stats, # Corrected to match function
                      create_user, update_balance, get_user_by_username,
                      set_setting, bulk_add_keys,
                      toggle_user_active_status, reset_user_device_id)
from keyboards import (get_admin_panel_keyboard, get_admin_users_keyboard,
                       get_admin_keys_keyboard, get_cancel_admin_action_keyboard,
                       get_back_to_dashboard_keyboard, get_bulk_add_duration_keyboard,
                       get_cancel_bulk_add_keyboard)

# Conversation states
(CREATE_USER_USERNAME, CREATE_USER_PASSWORD, ADD_BALANCE_USERNAME,
 ADD_BALANCE_AMOUNT, SET_IPA_LINK, SELECT_KEY_DURATION, RECEIVE_KEYS_LIST) = range(10, 17)


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "👑 *Admin Panel*\n\nWelcome to the admin control center."
    await query.edit_message_text(text,
                                  reply_markup=get_admin_panel_keyboard(),
                                  parse_mode=ParseMode.MARKDOWN)


async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Now correctly calls the function that exists
    users = get_all_users_paged()
    if not users:
        user_list_text = "No users found."
    else:
        user_list = []
        for user in users:
            status_icon = "✅" if user['is_active'] else "❌"
            admin_icon = " 👑" if user['is_admin'] else ""
            user_list.append(
                f"`{user['id']}`: {html.escape(user['username'])} ({status_icon}){admin_icon} - Bal: ${user['balance']:.2f}"
            )
        user_list_text = "\n".join(user_list)

    text = f"👥 *User Management*\n\n{user_list_text}"
    await query.edit_message_text(text,
                                  reply_markup=get_admin_users_keyboard(),
                                  parse_mode=ParseMode.MARKDOWN)

async def admin_keys_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "🔑 *Key Management*\n\nManage license key stock."
    await query.edit_message_text(text, reply_markup=get_admin_keys_keyboard(), parse_mode=ParseMode.MARKDOWN)


async def view_stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stock = get_key_stock()
    if not stock:
        stock_text = "No keys of any duration are in stock."
    else:
        stock_text = "\n".join([f"• {item['duration_days']}-Day Keys: {item['count']}" for item in stock])

    text = f"📦 *Key Stock*\n\nAvailable keys:\n{stock_text}"
    await query.edit_message_text(text, reply_markup=get_admin_keys_keyboard(), parse_mode=ParseMode.MARKDOWN)


async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    stats = get_bot_stats()
    text = f"""
📊 *Bot Statistics*

- Total Users: `{stats['total_users']}`
- Active Users: `{stats['active_users']}`
- Total Keys Sold: `{stats['total_keys_sold']}`
- Total Earnings: `${stats['total_earnings']:.2f}`
- Keys in Stock: `{stats['keys_in_stock']}`
    """
    await query.edit_message_text(text, reply_markup=get_admin_panel_keyboard(), parse_mode=ParseMode.MARKDOWN)


async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    text = "👑 *Admin Panel*\n\nAction cancelled. Returning to the admin panel."
    await query.edit_message_text(text,
                                  reply_markup=get_admin_panel_keyboard(),
                                  parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


# --- Create User Conversation ---
async def admin_create_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Enter the username for the new user:",
                                  reply_markup=get_cancel_admin_action_keyboard())
    return CREATE_USER_USERNAME

async def create_user_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_username'] = update.message.text
    await update.message.reply_text("Enter the password for the new user:")
    return CREATE_USER_PASSWORD

async def create_user_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data['new_username']
    password = update.message.text
    success, message = create_user(username, password)
    await update.message.reply_text(message)
    context.user_data.clear()
    await update.message.reply_text("Returning to admin panel.", reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END


# --- Add Balance Conversation ---
async def admin_add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Enter the username to add balance to:",
                                  reply_markup=get_cancel_admin_action_keyboard())
    return ADD_BALANCE_USERNAME

async def add_balance_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    user = get_user_by_username(username)
    if not user:
        await update.message.reply_text("User not found. Please try again or cancel.",
                                        reply_markup=get_cancel_admin_action_keyboard())
        return ADD_BALANCE_USERNAME
    context.user_data['user_to_credit'] = user
    await update.message.reply_text(f"Enter the amount to add to {username}'s balance (e.g., 10.50):")
    return ADD_BALANCE_AMOUNT

async def add_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount_text = update.message.text
    user = context.user_data['user_to_credit']
    try:
        amount = float(amount_text)
        if amount <= 0:
            raise ValueError("Amount must be positive.")
        update_balance(user['id'], amount, 'credit', f"Admin credit by {update.effective_user.id}")
        await update.message.reply_text(f"✅ Successfully added ${amount:.2f} to {user['username']}'s balance.")
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a positive number (e.g., 10.50).")
        return ADD_BALANCE_AMOUNT

    context.user_data.clear()
    await update.message.reply_text("Returning to admin panel.", reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END


# --- User Commands (handled via /command <username>) ---
async def toggle_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in context.bot_data.get('admin_ids', []):
        return
    try:
        username = context.args[0]
        success, message = toggle_user_active_status(username)
        await update.message.reply_text(message)
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /toggleuser <username>")

async def reset_device_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in context.bot_data.get('admin_ids', []):
        return
    try:
        username = context.args[0]
        success, message = reset_user_device_id(username)
        await update.message.reply_text(message.
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /resetdevice <username>")


# --- Set IPA Link ---
async def admin_set_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please send me the new IPA download link:",
                                  reply_markup=get_cancel_admin_action_keyboard())
    return SET_IPA_LINK

async def admin_receive_new_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_link = update.message.text
    set_setting('ipa_download_link', new_link)
    await update.message.reply_text(f"✅ IPA link has been updated successfully.",
                                    reply_markup=get_admin_panel_keyboard())
    return ConversationHandler.END


# --- Bulk Add Keys ---
async def add_custom_keys_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "Please select the duration for the keys you want to add:"
    await query.edit_message_text(text=text, reply_markup=get_bulk_add_duration_keyboard())
    return SELECT_KEY_DURATION

async def select_key_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    duration = int(query.data.split('_')[-1])
    context.user_data['bulk_add_duration'] = duration
    text = (f"OK, adding {duration}-day keys.\n\n"
            "Please send me a list of keys, with each key on a new line.")
    await query.edit_message_text(text=text, reply_markup=get_cancel_bulk_add_keyboard())
    return RECEIVE_KEYS_LIST

async def receive_keys_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    duration = context.user_data.get('bulk_add_duration')
    if not duration:
        await update.message.reply_text("Error: Duration not set. Please start over.",
                                        reply_markup=get_admin_keys_keyboard())
        return ConversationHandler.END

    keys = [key.strip() for key in update.message.text.split('\n') if key.strip()]
    if not keys:
        await update.message.reply_text("No valid keys received. Please send a non-empty list.",
                                        reply_markup=get_cancel_bulk_add_keyboard())
        return RECEIVE_KEYS_LIST

    count = bulk_add_keys(duration, keys)
    await update.message.reply_text(f"✅ Success! Added {count} new {duration}-day keys to the stock.",
                                    reply_markup=get_admin_keys_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_bulk_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text("🔑 *Key Management*\n\nAction cancelled.",
                                  reply_markup=get_admin_keys_keyboard(),
                                  parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END
