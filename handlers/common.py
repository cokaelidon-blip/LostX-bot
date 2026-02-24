# handlers/common.py
import html
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# Corrected imports to match the new database structure
from database import (get_user, create_user, get_user_by_telegram_id, check_session,
                      link_telegram_id, create_session, invalidate_session,
                      promote_user_to_admin, get_user_by_username)
from keyboards import get_start_keyboard, get_dashboard_keyboard
from config import ADMIN_IDS, ADMIN_USERNAME, ADMIN_PASSWORD, PRICING

USERNAME, PASSWORD = range(1, 3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id

    # --- Auto-create and/or promote admin ---
    if telegram_id in ADMIN_IDS:
        admin_user = get_user_by_telegram_id(telegram_id)
        if not admin_user:
            if ADMIN_USERNAME and ADMIN_PASSWORD:
                existing_user = get_user_by_username(ADMIN_USERNAME)
                if not existing_user:
                    create_user(ADMIN_USERNAME, ADMIN_PASSWORD, is_admin=True)
                    logging.info(f"Admin account '{ADMIN_USERNAME}' created from config.")

                user_to_link = get_user_by_username(ADMIN_USERNAME)
                if user_to_link:
                    link_telegram_id(user_to_link['id'], telegram_id)
                    promote_user_to_admin(telegram_id)
                    await update.message.reply_text(f"✅ Admin account '{ADMIN_USERNAME}' has been linked to you.")
                else:
                    await update.message.reply_text("Critical error during admin setup.")
        elif not admin_user['is_admin']:
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
        link_telegram_id(user['id'], telegram_id)
        create_session(user['id'])

        if telegram_id in ADMIN_IDS and not user['is_admin']:
            promote_user_to_admin(telegram_id)

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
        # THIS IS THE FIXED LINE
        await update.message.reply_text(
            "❌ <b>Login Failed</b>\n\nInvalid username or password.",
            reply_markup=get_start_keyboard(),
            parse_mode=ParseMode.HTML
        )
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Action cancelled.', reply_markup=get_start_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    invalidate_session(update.effective_user.id)
    await query.edit_message_text("✅ You have been logged out.", reply_markup=get_start_keyboard())


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤔 Sorry, I didn't understand that command. Try using /start to see the main menu.")
