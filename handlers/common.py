# handlers/common.py
import html
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (get_user, create_user, get_user_by_telegram_id, check_session,
                      link_telegram_id, create_session, invalidate_session,
                      promote_user_to_admin)
from keyboards import get_start_keyboard, get_dashboard_keyboard
from config import ADMIN_IDS, ADMIN_USERNAME, ADMIN_PASSWORD, PRICING

USERNAME, PASSWORD = range(1, 3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    
    # --- Auto-create and/or promote admin ---
    if telegram_id in ADMIN_IDS:
        admin_user = get_user_by_telegram_id(telegram_id)
        if not admin_user:
            # If the admin user account itself doesn't exist, create it from config
            if ADMIN_USERNAME and ADMIN_PASSWORD:
                # Check if username already exists to avoid errors
                existing_user = get_user_by_username(ADMIN_USERNAME)
                if not existing_user:
                    create_user(ADMIN_USERNAME, ADMIN_PASSWORD, is_admin=True)
                    logging.info(f"Admin account '{ADMIN_USERNAME}' created from config.")
                
                # Now, find the user we just created (or that already existed) and link it
                user_to_link = get_user_by_username(ADMIN_USERNAME)
                if user_to_link:
                    link_telegram_id(user_to_link['id'], telegram_id)
                    promote_user_to_admin(telegram_id) # Ensure admin status is set
                    await update.message.reply_text(f"✅ Admin account '{ADMIN_USERNAME}' has been linked to you.")
                else: # This should theoretically never happen
                    await update.message.reply_text("Critical error during admin setup.")

        elif not admin_user['is_admin']:
            # User exists and is an admin by ID, but not in DB. Promote them.
            promote_user_to_admin(telegram_id)
            await update.message.reply_text("✅ Your account has been granted admin privileges.")

    # --- Session check for all users ---
    session_user = check_session(telegram_id)
    if session_user:
        safe_username = html.escape(session_user['username'])
        dashboard_text = f"""
🎮 <b>Welcome back, {safe_username}!</b>

You are already logged in.

💰 Balance: <b>${session_user['balance']:.2f}</b>
        """
        await update.message.reply_text(
            dashboard_text,
            reply_markup=get_dashboard_keyboard(session_user['is_admin']),
            parse_mode=ParseMode.HTML)
    else:
        price_list = "\n".join([f"• {plan['label']}: <b>${plan['price']:.2f}</b>" for plan in PRICING.values()])
        welcome_text = f"""
👋 <b>Welcome to the Modder IPA Bot!</b>

Here are our available plans:
{price_list}

Please log in to purchase access.
        """
        await update.message.reply_text(welcome_text,
                                        reply_markup=get_start_keyboard(),
                                        parse_mode=ParseMode.HTML)


async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="👤 Please enter your username:")
    return USERNAME


async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['login_username'] = update.message.text
    await update.message.reply_text("🔑 Please enter your password:")
    return PASSWORD


async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data.get('login_username')
    password = update.message.text
    telegram_id = update.effective_user.id
    try: await update.message.delete()
    except Exception: pass

    user = get_user(username, password)

    if user:
        # Link this telegram account to the user id
        link_telegram_id(user['id'], telegram_id)

        # Create a persistent session
        create_session(user['id'])

        # Promote to admin if they are in the ADMIN_IDS list
        if telegram_id in ADMIN_IDS and not user['is_admin']:
            promote_user_to_admin(telegram_id)
        
        # Now fetch the final, updated user state
        final_user_state = get_user_by_telegram_id(telegram_id)

        safe_username = html.escape(final_user_state['username'])
        dashboard_text = f"""
✅ <b>Login Successful!</b>

Welcome, <b>{safe_username}</b>.

💰 Balance: <b>${final_user_state['balance']:.2f}</b>
        """
        await update.message.reply_text(
            dashboard_text,
            reply_markup=get_dashboard_keyboard(final_user_state['is_admin']),
            parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("❌ <b>Login Failed</b>
Invalid username or password.",
                                        reply_markup=get_start_keyboard(),
                                        parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Action cancelled.', reply_markup=get_start_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Use the new invalidate_session function
    invalidate_session(update.effective_user.id)
    
    await query.edit_message_text("✅ You have been logged out.", reply_markup=get_start_keyboard())


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤔 Sorry, I didn't understand that command. Try using /start to see the main menu.")

# Helper to get user by username, since it's used in start logic now
def get_user_by_username(username):
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def get_db_connection():
    """Duplicate for local use to avoid circular import"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn
