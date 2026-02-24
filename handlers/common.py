# handlers/common.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from telegram.helpers import escape_html

from database import check_session, authenticate_user, create_user, logout_user
from keyboards import get_start_keyboard, get_dashboard_keyboard

# States for login and register conversations
USERNAME, PASSWORD = range(1, 3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)

    if session:
        safe_username = escape_html(session['username'])
        dashboard_text = f"""
🎮 <b>Welcome back, {safe_username}!</b>

You are already logged in.

💰 Balance: <b>${session['balance']:.2f}</b>
        """
        await update.message.reply_text(
            dashboard_text,
            reply_markup=get_dashboard_keyboard(session['is_admin']),
            parse_mode=ParseMode.HTML)
    else:
        welcome_text = (
            "👋 <b>Welcome to the Modder IPA Bot!</b>
"
            "Please log in to access your dashboard or register for a new account."
        )
        await update.message.reply_text(welcome_text,
                                        reply_markup=get_start_keyboard(),
                                        parse_mode=ParseMode.HTML)


async def login_start(update: Update,
                      context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="👤 Please enter your username:")
    return USERNAME


async def login_username(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['login_username'] = update.message.text
    await update.message.reply_text("🔑 Please enter your password:")
    return PASSWORD


async def login_password(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data.get('login_username')
    password = update.message.text
    telegram_id = update.effective_user.id
    try: await update.message.delete()
    except Exception: pass

    success, result = authenticate_user(username, password, telegram_id)

    if success:
        session = check_session(telegram_id)
        safe_username = escape_html(session['username'])
        dashboard_text = f"""
✅ <b>Login Successful!</b>

Welcome, <b>{safe_username}</b>.

💰 Balance: <b>${session['balance']:.2f}</b>
        """
        await update.message.reply_text(
            dashboard_text,
            reply_markup=get_dashboard_keyboard(session['is_admin']),
            parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ {escape_html(result)}",
                                        reply_markup=get_start_keyboard(),
                                        parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_login(update: Update,
                       context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Action cancelled.',
                                    reply_markup=get_start_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


async def register_start(update: Update,
                         context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(text="📋 Please choose a username:")
    return USERNAME


async def register_username(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['register_username'] = update.message.text
    await update.message.reply_text("🔑 Please choose a strong password:")
    return PASSWORD


async def register_password(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data.get('register_username')
    password = update.message.text
    try: await update.message.delete()
    except Exception: pass
    success, result = create_user(username, password)
    if success:
        await update.message.reply_text(
            "✅ <b>Registration Successful!</b>
You can now log in using your new credentials.",
            reply_markup=get_start_keyboard(),
            parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"❌ {escape_html(result)}",
                                        reply_markup=get_start_keyboard(),
                                        parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END


async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logout_user(update.effective_user.id)
    await query.edit_message_text("✅ You have been logged out.", reply_markup=get_start_keyboard())


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤔 Sorry, I didn't understand that command. Try using /start to see the main menu.")
