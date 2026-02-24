# handlers/common.py
import html
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (create_user, get_user_by_username, get_user_by_telegram_id, 
                      hash_password, create_session, check_session, clear_session) # <-- REMOVED get_user
from keyboards import get_start_keyboard
from handlers.user import show_dashboard

# States for login conversation
USERNAME, PASSWORD = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user_id = update.effective_user.id
    session = check_session(user_id)

    if session:
        # User is already logged in, show them the dashboard
        await show_dashboard(update, context, session)
    else:
        # User is not logged in
        await update.message.reply_text(
            "Welcome to the Modder IPA Bot! Please log in to continue.",
            reply_markup=get_start_keyboard()
        )

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the login conversation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Please enter your username:")
    return USERNAME

async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the username and asks for the password."""
    context.user_data['username'] = update.message.text
    await update.message.reply_text("Please enter your password:")
    return PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Checks the password and completes login."""
    username = context.user_data.get('username')
    password = update.message.text
    
    # --- THIS IS THE CORRECTED LOGIN LOGIC ---
    user = get_user_by_username(username)
    
    if user and user['password_hash'] == hash_password(password):
        # Check if the user's telegram ID is set, if not, set it.
        if not user['telegram_id']:
            conn = get_db_connection()
            conn.execute('UPDATE users SET telegram_id = ? WHERE id = ?', (update.effective_user.id, user['id']))
            conn.commit()
            conn.close()
            logging.info(f"Associated Telegram ID {update.effective_user.id} with user '{username}'.")
            
        # Create a session for the user
        create_session(update.effective_user.id, user)
        session = check_session(update.effective_user.id)

        await update.message.reply_text("✅ Login successful!")
        await show_dashboard(update, context, session) # Show the main dashboard
        
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Invalid username or password. Please try again or type /cancel.")
        # We stay in the PASSWORD state to allow another password attempt
        return PASSWORD

async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the login conversation."""
    context.user_data.clear()
    await update.message.reply_text(
        "Login cancelled. Welcome to the Modder IPA Bot!",
        reply_markup=get_start_keyboard()
    )
    return ConversationHandler.END

async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logs the user out and clears their session."""
    query = update.callback_query
    await query.answer()
    clear_session(update.effective_user.id)
    await query.edit_message_text(
        "You have been logged out.",
        reply_markup=get_start_keyboard()
    )

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles any unknown commands."""
    await update.message.reply_text("Sorry, I didn't understand that command.")
