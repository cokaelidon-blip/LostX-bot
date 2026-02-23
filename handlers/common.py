# handlers/common.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from database import check_session, authenticate_user, create_user
from keyboards import get_start_keyboard, get_dashboard_keyboard

# States for login and register conversations
USERNAME, PASSWORD = range(1, 3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the /start command.
    Checks if the user has an active session. If so, shows the dashboard.
    If not, shows the initial login/register menu.
    """
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if session:
        # User is already logged in, show the dashboard
        dashboard_text = f"""
🎮 *Welcome back, {session['username']}!*

You are already logged in.

💰 Balance: *${session['balance']:.2f}*
        """
        await update.message.reply_text(
            dashboard_text,
            reply_markup=get_dashboard_keyboard(session['is_admin']),
            parse_mode='Markdown')
    else:
        # User is not logged in, show the welcome message
        welcome_text = (
            "👋 *Welcome to the Modder IPA Bot!*\n\n"
            "Please log in to access your dashboard or register for a new account."
        )
        await update.message.reply_text(welcome_text,
                                        reply_markup=get_start_keyboard(),
                                        parse_mode='Markdown')


# --- Login Conversation Handlers ---


async def login_start(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the login conversation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="👤 Please enter your username:")
    return USERNAME


async def login_username(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the username and asks for the password."""
    context.user_data['login_username'] = update.message.text
    await update.message.reply_text("🔑 Please enter your password:")
    return PASSWORD


async def login_password(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the password, authenticates the user, and ends the conversation."""
    username = context.user_data.get('login_username')
    password = update.message.text
    telegram_id = update.effective_user.id

    # Try to delete the password message for security
    try:
        await update.message.delete()
    except Exception:
        pass  # Ignore if it fails (e.g., not enough rights)

    success, result = authenticate_user(username, password, telegram_id)

    if success:
        session = check_session(
            telegram_id)  # Re-fetch session to get all details
        dashboard_text = f"""
✅ *Login Successful!*

Welcome, *{session['username']}*.

💰 Balance: *${session['balance']:.2f}*
        """
        await update.message.reply_text(
            dashboard_text,
            reply_markup=get_dashboard_keyboard(session['is_admin']),
            parse_mode='Markdown')
    else:
        error_message = result  # The error message from authenticate_user
        await update.message.reply_text(f"❌ {error_message}",
                                        reply_markup=get_start_keyboard())

    # Clean up and end the conversation
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_login(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the login/register conversation."""
    await update.message.reply_text('Action cancelled.',
                                    reply_markup=get_start_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


# --- Register Conversation Handlers ---


async def register_start(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the registration conversation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="📋 Please choose a username:")
    return USERNAME


async def register_username(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the new username and asks for a password."""
    context.user_data['register_username'] = update.message.text
    await update.message.reply_text("🔑 Please choose a strong password:")
    return PASSWORD


async def register_password(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles the password, creates the new user, and ends the conversation."""
    username = context.user_data.get('register_username')
    password = update.message.text

    # Try to delete the password message for security
    try:
        await update.message.delete()
    except Exception:
        pass

    success, result = create_user(username, password)

    if success:
        await update.message.reply_text(
            "✅ *Registration Successful!*\n\n"
            "You can now log in using your new credentials.",
            reply_markup=get_start_keyboard(),
            parse_mode='Markdown')
    else:
        error_message = result
        await update.message.reply_text(f"❌ {error_message}",
                                        reply_markup=get_start_keyboard())

    context.user_data.clear()
    return ConversationHandler.END


# --- Logout Handler ---


async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logs the user out by clearing their session from the database."""
    query = update.callback_query
    await query.answer()

    # We can implement session clearing here if needed in database.py
    # For now, just send them to the start menu
    await query.edit_message_text(
        "✅ You have been logged out.", reply_markup=get_start_keyboard())


# --- Fallback for Unknown Commands ---


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles any command that the bot does not recognize."""
    await update.message.reply_text(
        "🤔 Sorry, I didn't understand that command. "
        "Try using /start to see the main menu.")
