# handlers/user.py
import html
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import check_session, get_setting
from keyboards import get_dashboard_keyboard, get_back_to_dashboard_keyboard
from config import ADMIN_CONTACT_USERNAME


async def dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Back to Dashboard' button."""
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.", parse_mode=ParseMode.HTML)
        return

    safe_username = html.escape(session['username'])
    dashboard_text = f"""
🎮 <b>Welcome back, {safe_username}!</b>

You are already logged in.

💰 Balance: <b>${session['balance']:.2f}</b>
    """
    await query.edit_message_text(
        dashboard_text,
        reply_markup=get_dashboard_keyboard(session['is_admin']),
        parse_mode=ParseMode.HTML)


async def add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows instructions for adding balance by contacting the admin."""
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.")
        return
    
    text = f"""
💰 <b>Add Balance</b>

To add balance to your account, please contact the admin directly on Telegram for assistance.

Admin: <b>{ADMIN_CONTACT_USERNAME}</b>

They will help you with the payment process.
    """
    await query.edit_message_text(text,
                                  reply_markup=get_back_to_dashboard_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def download_ipa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides the IPA download link."""
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.")
        return

    ipa_link = get_setting('ipa_download_link')
    if not ipa_link:
        text = "The download link is not set yet. Please check back later."
    else:
        text = f"⬇️ Here is your download link:\n\n{ipa_link}"

    await query.edit_message_text(text,
                                  reply_markup=get_back_to_dashboard_keyboard(),
                                  disable_web_page_preview=True)
