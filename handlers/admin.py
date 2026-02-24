# handlers/admin.py
import html
from telegram import Update
from telegram.ext import (ContextTypes, ConversationHandler,
                          CallbackQueryHandler, MessageHandler, filters)
from telegram.constants import ParseMode

from database import (check_session, create_user, get_all_users,
                      get_user_by_username, update_balance, add_key_to_stock,
                      get_stock_count, get_statistics, toggle_user_status,
                      reset_user_device, update_setting)
from keyboards import (get_admin_keyboard, get_keys_management_keyboard,
                       get_duration_selection_keyboard)

CREATE_USER_USERNAME, CREATE_USER_PASSWORD = range(2)
ADD_BALANCE_USERNAME, ADD_BALANCE_AMOUNT = range(2, 4)
SET_IPA_LINK = range(4, 5)
SELECT_KEY_DURATION, RECEIVE_KEYS_LIST = range(5, 7)


def is_admin(session):
    return session and session.get('is_admin')


async def admin_panel_callback(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(check_session(update.effective_user.id)):
        await query.edit_message_text("❌ Access denied. Admin only.")
        return

    await query.edit_message_text("⚙️ <b>Admin Panel</b>\n\nSelect an option:",
                                  reply_markup=get_admin_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def admin_users_callback(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(check_session(update.effective_user.id)):
        await query.edit_message_text("❌ Access denied.")
        return

    users = get_all_users()
    if not users:
        text = "👥 <b>User Management</b>\n\nNo users found."
    else:
        text = "👥 <b>User Management</b>\n\n"
        for user in users[:20]:
            status = "✅" if user['is_active'] else "❌"
            text += f"{status} <b>{html.escape(user['username'])}</b> - ${user['balance']:.2f}\n"

    text += """

To manage a user, use commands:
<code>/toggleuser username</code> - Enable/Disable
<code>/resetdevice username</code> - Reset device binding"""

    await query.edit_message_text(text,
                                  reply_markup=get_admin_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def admin_keys_callback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(check_session(update.effective_user.id)):
        await query.edit_message_text("❌ Access denied.")
        return

    await query.edit_message_text("🔑 <b>Keys Stock Management</b>\n\nSelect an option:",
                                  reply_markup=get_keys_management_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def view_stock_callback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(check_session(update.effective_user.id)):
        await query.edit_message_text("❌ Access denied.")
        return

    stock = get_stock_count()
    text = f"""
📦 <b>Current Stock</b>

• 1 Day Keys: <b>{stock.get(1, 0)}</b>
• 7 Days Keys: <b>{stock.get(7, 0)}</b>
• 1 Month Keys: <b>{stock.get(30, 0)}</b>

<b>Total: {sum(stock.values())} keys</b>
    """

    await query.edit_message_text(text,
                                  reply_markup=get_keys_management_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def admin_stats_callback(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(check_session(update.effective_user.id)):
        await query.edit_message_text("❌ Access denied.")
        return

    stats = get_statistics()
    text = f"""
📊 <b>Bot Statistics</b>

👥 Total Users: <b>{stats['total_users']}</b>
🔑 Keys in Stock: <b>{stats['keys_in_stock']}</b>
🛒 Total Sales: <b>{stats['total_sales']}</b>
💰 Total Revenue: <b>${stats['total_revenue']:.2f}</b>
    """

    await query.edit_message_text(text,
                                  reply_markup=get_admin_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def add_custom_keys_start(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(check_session(update.effective_user.id)):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END

    await query.edit_message_text("""
<b>Step 1: Select Key Duration</b>

Please choose the duration for the keys you are about to add:
                                  """,
                                  reply_markup=get_duration_selection_keyboard(),
                                  parse_mode=ParseMode.HTML)
    return SELECT_KEY_DURATION


async def select_key_duration(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    duration = int(query.data.replace("duration_select_", ""))
    context.user_data['bulk_add_duration'] = duration
    await query.edit_message_text(f"""
<b>Step 2: Paste Your Keys</b>

You have selected <b>{duration} days</b> duration.

Please send a message containing the list of keys. Each key must be on a <b>new line</b>.
                                  """,
                                  parse_mode=ParseMode.HTML)
    return RECEIVE_KEYS_LIST


async def receive_keys_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    duration = context.user_data.get('bulk_add_duration')
    if not duration:
        await update.message.reply_text("Error: Duration not set. Please start over.")
        return ConversationHandler.END

    keys_list = [key.strip() for key in update.message.text.splitlines() if key.strip()]
    if not keys_list:
        await update.message.reply_text("No valid keys found in your message. Please try again.")
        return RECEIVE_KEYS_LIST

    await update.message.reply_text(f"⏳ Processing {len(keys_list)} keys...")
    success_count, fail_count = 0, 0
    failed_keys = []
    for key in keys_list:
        success, result = add_key_to_stock(duration, key_value=key)
        if success:
            success_count += 1
        else:
            fail_count += 1
            failed_keys.append(f"<code>{html.escape(key)}</code> ({html.escape(str(result))})")

    report = f"""
✅ <b>Bulk Add Report</b>

Total keys processed: <b>{len(keys_list)}</b>
Successfully added: <b>{success_count}</b>
Failed (duplicates): <b>{fail_count}</b>
    """
    if failed_keys:
        report += "\n<b>Failed Keys:</b>\n" + "\n".join(failed_keys)

    await update.message.reply_text(report, parse_mode=ParseMode.HTML)
    context.user_data.pop('bulk_add_duration', None)
    return ConversationHandler.END


async def cancel_bulk_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.pop('bulk_add_duration', None)
    await query.edit_message_text("❌ Bulk key addition cancelled.", reply_markup=get_keys_management_keyboard())
    return ConversationHandler.END


async def admin_create_user_callback(update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(check_session(update.effective_user.id)):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END
    await query.edit_message_text("➕ <b>Create New User</b>\n\nEnter the username for the new user:", parse_mode=ParseMode.HTML)
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
    try: await update.message.delete()
    except: pass
    success, result = create_user(username, password)
    if success:
        await update.message.reply_text(f"""
✅ <b>User Created Successfully!</b>

👤 Username: <code>{html.escape(username)}</code>
🔑 Password: <code>{html.escape(password)}</code>

Share these credentials with the user.
        """, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ Failed to create user: {html.escape(str(result))}")
    return ConversationHandler.END


async def admin_add_balance_callback(update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(check_session(update.effective_user.id)):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END
    await query.edit_message_text("💵 <b>Add Balance</b>\n\nEnter the username:", parse_mode=ParseMode.HTML)
    return ADD_BALANCE_USERNAME


async def add_balance_username(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    user = get_user_by_username(username)
    if not user:
        await update.message.reply_text("❌ User not found. Please start over.")
        return ConversationHandler.END
    context.user_data['balance_user_id'] = user['id']
    context.user_data['balance_username'] = username
    await update.message.reply_text(f"""
👤 User: <b>{html.escape(username)}</b>
💰 Current Balance: <b>${user['balance']:.2f}</b>

Enter the amount to add (in USD):
    """, parse_mode=ParseMode.HTML)
    return ADD_BALANCE_AMOUNT


async def add_balance_amount(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a number.")
        return ADD_BALANCE_AMOUNT
    user_id = context.user_data.get('balance_user_id')
    username = context.user_data.get('balance_username')
    update_balance(user_id, amount, 'admin_add', 'Added by admin')
    await update.message.reply_text(f"""
✅ <b>Balance Added Successfully!</b>

👤 User: <b>{html.escape(username)}</b>
💵 Amount Added: <b>${amount:.2f}</b>
    """, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


async def cancel_admin_action(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action cancelled.")
    await update.message.reply_text("⚙️ <b>Admin Panel</b>\n\nSelect an option:", reply_markup=get_admin_keyboard(), parse_mode=ParseMode.HTML)
    return ConversationHandler.END


async def toggle_user_command(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(check_session(update.effective_user.id)):
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
    toggle_user_status(user['id'])
    await update.message.reply_text(f"✅ User <b>{html.escape(username)}</b> status toggled.", parse_mode=ParseMode.HTML)


async def reset_device_command(update: Update,
                               context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(check_session(update.effective_user.id)):
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
    reset_user_device(user['id'])
    await update.message.reply_text(f"✅ Device binding reset for <b>{html.escape(username)}</b>.", parse_mode=ParseMode.HTML)


async def admin_set_link_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(check_session(update.effective_user.id)):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END
    await query.edit_message_text("""
🔗 <b>Update IPA Link</b>

Please send me the new IPA link now. Send /cancel to abort.
    """, parse_mode=ParseMode.HTML)
    return SET_IPA_LINK


async def admin_receive_new_link(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    new_link = update.message.text
    update_setting('ipa_link', new_link)
    await update.message.reply_text("✅ <b>Link Updated Successfully!</b>\n\nNew link is now set.", parse_mode=ParseMode.HTML)
    await update.message.reply_text("⚙️ <b>Admin Panel</b>\n\nSelect an option:", reply_markup=get_admin_keyboard(), parse_mode=ParseMode.HTML)
    return ConversationHandler.END
