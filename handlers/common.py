# handlers/common.py
import html
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (check_session, create_session, clear_session,
                      get_user_by_username, hash_password, get_db_connection)
# --- THIS IS THE FIX ---
# Correctly imports 'get_start_keyboard' instead of the non-existent ones.
from keyboards import (get_start_keyboard, get_dashboard_keyboard, 
                       get_admin_panel_keyboard)

# Conversation states
USERNAME, PASSWORD = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    session = check_session(user.id)

    if session:
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

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives the password, verifies credentials, and ends the conversation."""
    username = context.user_data.get('username')
    password = update.message.text
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()

    if user and user['password_hash'] == hash_password(password):
        create_session(update.effective_user.id, user)
        await update.message.reply_text("✅ Login successful!")
        await start(update, context) # Show the correct dashboard
    else:
        await update.message.reply_text("❌ Invalid username or password. Please try again or type /cancel.")
        await update.message.reply_text("Please enter your username:")
        return USERNAME

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the login conversation."""
    context.user_data.clear()
    await update.message.reply_text("Login cancelled.")
    await start(update, context)
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
