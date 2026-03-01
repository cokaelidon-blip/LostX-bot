# handlers/common.py
import html
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# --- FIX 1: Import the new database function ---
from database import (check_session, create_session, clear_session,
                      get_user_by_username, hash_password, get_db_connection, link_telegram_id_to_user)
                      
from keyboards import (get_start_keyboard, get_dashboard_keyboard, 
                       get_admin_panel_keyboard)

# Conversation states
USERNAME, PASSWORD = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    # Ensure user has a session and is linked in DB upon /start
    session = check_session(user.id)
    if session:
        user_db = get_user_by_telegram_id(user.id)
        if not user_db:
            link_telegram_id_to_user(session['id'], user.id)

        # User is logged in, show the appropriate dashboard
        if session.get('is_admin'):
            text = f"Welcome back, Admin {html.escape(session['username'])}!"
            keyboard = get_admin_panel_keyboard()
        else:
            text = f"Welcome back, {html.escape(session['username'])}!"
            keyboard = get_dashboard_keyboard(session.get('is_admin', False))
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        # User is not logged in, show the login prompt
        text = "Welcome to the Modder IPA Bot! Please log in to continue."
        await update.message.reply_text(text, reply_markup=get_start_keyboard())

# --- Login Conversation ---
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the login process after the 'Login' button is clicked."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="Please enter your username:")
    return USERNAME

async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the username and asks for the password."""
    context.user_data['username'] = update.message.text
    await update.message.reply_text("Please enter your password:")
    return PASSWORD

# --- FIX 2: This function is heavily modified ---
async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives password, verifies credentials, links Telegram ID, and ends conversation."""
    username = context.user_data.get('username')
    password = update.message.text
    
    user = get_user_by_username(username)

    if user and user['password_hash'] == hash_password(password):
        telegram_id = update.effective_user.id
        
        # This is the core fix: Link the user's account to their Telegram ID in the database.
        if not user['telegram_id'] or user['telegram_id'] != telegram_id:
             link_telegram_id_to_user(user['id'], telegram_id)
        
        create_session(telegram_id, user)
        await update.message.reply_text("✅ Login successful!")
        
        # Call start to display the correct dashboard
        # We need a dummy message object for start() to reply to
        dummy_update = Update(update.update_id, message=update.message)
        await start(dummy_update, context)
    else:
        await update.message.reply_text("❌ Invalid username or password. Please try again or type /cancel.")
        # Ask for username again to restart the login flow cleanly
        await update.message.reply_text("Please enter your username:")
        return USERNAME

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the login conversation."""
    context.user_data.clear()
    await update.message.reply_text("Login cancelled.")
    # We need a dummy message object for start() to reply to
    dummy_update = Update(update.update_id, message=update.message)
    await start(dummy_update, context)
    return ConversationHandler.END

# --- Logout ---
async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logs the user out and shows the initial login screen."""
    query = update.callback_query
    await query.answer("Logging you out...")
    clear_session(update.effective_user.id)
    text = "You have been successfully logged out."
    await query.edit_message_text(text=text, reply_markup=get_start_keyboard())

# --- Unknown Command ---
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles any command that the bot doesn't recognize."""
    await update.message.reply_text("Sorry, I didn't understand that command.")
