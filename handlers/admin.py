# handlers/admin.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import (
    check_session, create_user, get_all_users, get_user_by_username,
    update_balance, add_key_to_stock, get_stock_count, get_statistics,
    toggle_user_status, reset_user_device
)
from keyboards import (
    get_admin_keyboard, get_keys_management_keyboard,
    get_back_keyboard, get_cancel_keyboard
)

# Conversation states
CREATE_USER_USERNAME, CREATE_USER_PASSWORD = range(2)
ADD_BALANCE_USERNAME, ADD_BALANCE_AMOUNT = range(2, 4)

def is_admin(session):
    return session and session.get('is_admin')

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not is_admin(session):
        await query.edit_message_text("❌ Access denied. Admin only.")
        return
    
    await query.edit_message_text(
        "⚙️ *Admin Panel*\n\nSelect an option:",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def admin_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await query.edit_message_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def admin_keys_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return
    
    await query.edit_message_text(
        "🔑 *Keys Stock Management*\n\nSelect an option:",
        reply_markup=get_keys_management_keyboard(),
        parse_mode='Markdown'
    )

async def add_key_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return
    
    days = int(query.data.split("_")[-1])
    success, key = add_key_to_stock(days)
    
    if success:
        await query.edit_message_text(
            f"✅ *Key Added Successfully!*\n\n"
            f"🔑 Key: `{key}`\n"
            f"📅 Duration: {days} days",
            reply_markup=get_keys_management_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            f"❌ Failed to add key: {key}",
            reply_markup=get_keys_management_keyboard()
        )

async def view_stock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await query.edit_message_text(
        text,
        reply_markup=get_keys_management_keyboard(),
        parse_mode='Markdown'
    )

async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await query.edit_message_text(
        text,
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

# Create User Conversation
async def admin_create_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "➕ *Create New User*\n\nEnter the username for the new user:",
        parse_mode='Markdown'
    )
    
    return CREATE_USER_USERNAME

async def create_user_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_username'] = update.message.text
    
    await update.message.reply_text(
        "🔑 Now enter the password for this user:"
    )
    
    return CREATE_USER_PASSWORD

async def create_user_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get('new_username')
    password = update.message.text
    
    # Delete password message
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
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ Failed to create user: {result}"
        )
    
    return ConversationHandler.END

# Add Balance Conversation
async def admin_add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not is_admin(session):
        await query.edit_message_text("❌ Access denied.")
        return ConversationHandler.END
    
    await query.edit_message_text(
        "💵 *Add Balance*\n\nEnter the username:",
        parse_mode='Markdown'
    )
    
    return ADD_BALANCE_USERNAME

async def add_balance_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    user = get_user_by_username(username)
    
    if not user:
        await update.message.reply_text(
            "❌ User not found. Please try again with /start"
        )
        return ConversationHandler.END
    
    context.user_data['balance_user_id'] = user[0]
    context.user_data['balance_username'] = username
    
    await update.message.reply_text(
        f"👤 User: *{username}*\n"
        f"💰 Current Balance: *${user[2]:.2f}*\n\n"
        f"Enter the amount to add (in USD):",
        parse_mode='Markdown'
    )
    
    return ADD_BALANCE_AMOUNT

async def add_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a number.")
        return ADD_BALANCE_AMOUNT
    
    user_id = context.user_data.get('balance_user_id')
    username = context.user_data.get('balance_username')
    
    update_balance(user_id, amount, 'admin_add', f'Added by admin')
    
    await update.message.reply_text(
        f"✅ *Balance Added Successfully!*\n\n"
        f"👤 User: *{username}*\n"
        f"💵 Amount Added: *${amount:.2f}*",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def cancel_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Action cancelled.")
    return ConversationHandler.END

# Command handlers for user management
async def toggle_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await update.message.reply_text(f"✅ User *{username}* status toggled.", parse_mode='Markdown')

async def reset_device_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await update.message.reply_text(f"✅ Device binding reset for *{username}*.", parse_mode='Markdown')