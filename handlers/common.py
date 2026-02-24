# handlers/common.py
import html
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

from database import (check_session, authenticate_user, create_user, logout_user,
                      promote_user_to_admin, get_user_by_telegram_id)
from keyboards import get_start_keyboard, get_dashboard_keyboard
from config import ADMIN_IDS, ADMIN_USERNAME, ADMIN_PASSWORD, PRICING

# States for login and register conversations
USERNAME, PASSWORD = range(1, 3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user = get_user_by_telegram_id(telegram_id)

    # --- Auto-create admin account if it doesn't exist ---
    if not user and telegram_id in ADMIN_IDS:
        if ADMIN_USERNAME and ADMIN_PASSWORD:
            # Create the admin user
            create_user(ADMIN_USERNAME, ADMIN_PASSWORD, is_admin=True)
            # Now, authenticate to link the telegram_id and create a session
            authenticate_user(ADMIN_USERNAME, ADMIN_PASSWORD, telegram_id)
            await update.message.reply_text(
                f"✅ Admin account '{ADMIN_USERNAME}' created and linked to you. Welcome!"
            )
        else:
            await update.message.reply_text(
                "⚠️ Admin user setup required. Please set ADMIN_USERNAME and ADMIN_PASSWORD in your environment variables."
            )

    # --- Check for admin promotion for existing users ---
    session = check_session(telegram_id)
    if session and telegram_id in ADMIN_IDS and not session['is_admin']:
        promote_user_to_admin(telegram_id)
        # Re-check session to get updated admin status
        session = check_session(telegram_id)
        await update.message.reply_text("✅ Admin privileges have been granted to this account.")

    if session:
        safe_username = html.escape(session['username'])
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
        # --- NEW: Show prices to non-logged-in users ---
        price_list = "\n".join(
            [f"• {plan['label']}: <b>${plan['price']:.2f}</b>" for plan in PRICING.values()]
        )
        welcome_text = f"""
👋 <b>Welcome to the Modder IPA Bot!</b>

Here are our available plans:
{price_list}

Please log in to purchase access.
        """
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
        if telegram_id in ADMIN_IDS:
             promote_user_to_admin(telegram_id)

        session = check_session(telegram_id)
        safe_username = html.escape(session['username'])
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
        await update.message.reply_text(f"❌ {html.escape(str(result))}",
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


async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    logout_user(update.effective_user.id)
    await query.edit_message_text("✅ You have been logged out.", reply_markup=get_start_keyboard())


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤔 Sorry, I didn't understand that command. Try using /start to see the main menu.")
