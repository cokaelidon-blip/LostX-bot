# handlers/user.py
import html
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (check_session, get_user_balance, get_available_key,
                      sell_key, update_balance, record_purchase, get_setting)
from keyboards import (get_dashboard_keyboard, get_buy_menu_keyboard,
                       get_back_to_dashboard_keyboard, get_confirmation_keyboard)
from config import PRICING, STOCK_MODE, ADMIN_CONTACT_USERNAME


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


async def buy_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the menu for buying keys."""
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.")
        return

    text = f"🔑 <b>Buy Access</b>\n\nYour current balance: <b>${session['balance']:.2f}</b>\n\nPlease select a plan:"
    await query.edit_message_text(text,
                                  reply_markup=get_buy_menu_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def buy_key_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the user selecting a specific key plan to buy."""
    query = update.callback_query
    await query.answer()
    plan_key = query.data.split('_')[-1]
    plan = PRICING.get(plan_key)

    session = check_session(update.effective_user.id)
    if not session or not plan:
        await query.edit_message_text("An error occurred. Please try again.",
                                      reply_markup=get_back_to_dashboard_keyboard())
        return

    user_balance = session['balance']
    plan_price = plan['price']

    if user_balance < plan_price:
        await query.edit_message_text(
            f"❌ <b>Insufficient Funds</b>\n\nYour balance is ${user_balance:.2f}, but you need ${plan_price:.2f} for this plan.",
            reply_markup=get_back_to_dashboard_keyboard(),
            parse_mode=ParseMode.HTML)
        return

    if STOCK_MODE:
        key = get_available_key(plan['days'])
        if not key:
            await query.edit_message_text(
                "❌ <b>Out of Stock</b>\n\nWe are currently out of stock for this plan. Please check back later.",
                reply_markup=get_back_to_dashboard_keyboard(),
                parse_mode=ParseMode.HTML)
            return

    # Store data for confirmation step
    context.user_data['purchase_plan'] = plan

    text = f"❓ <b>Confirm Purchase</b>\n\nYou are about to buy <b>{plan['label']}</b> for <b>${plan_price:.2f}</b>.\n\nYour remaining balance will be <b>${user_balance - plan_price:.2f}</b>."
    await query.edit_message_text(text,
                                  reply_markup=get_confirmation_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def confirm_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirms and finalizes the key purchase."""
    query = update.callback_query
    await query.answer()
    plan = context.user_data.get('purchase_plan')
    session = check_session(update.effective_user.id)

    if not session or not plan:
        await query.edit_message_text("An error occurred or your session expired. Please try again.",
                                      reply_markup=get_back_to_dashboard_keyboard())
        return

    key = get_available_key(plan['days']) if STOCK_MODE else {'id': None, 'key_value': 'Unlimited'}

    if STOCK_MODE and not key:
        await query.edit_message_text(
            "❌ <b>Out of Stock</b>\n\nSomeone else purchased the last key just before you. Please try again.",
            reply_markup=get_back_to_dashboard_keyboard(), parse_mode=ParseMode.HTML)
        return

    # Finalize purchase
    key_info = sell_key(key['id'], session['user_id'])
    update_balance(session['user_id'], -plan['price'], 'purchase', f"Purchase of {plan['label']} key")
    record_purchase(session['user_id'], key['id'], plan['price'], plan['days'])
    new_balance = get_user_balance(session['user_id'])

    # --- NEW: Simplified confirmation message ---
    final_message = f"""
✅ <b>Purchase Successful!</b>

Your access key has been generated and applied to your account.

Key: <code>{html.escape(key_info['key_value'])}</code>
Duration: {key_info['duration_days']} days

Your new balance is <b>${new_balance:.2f}</b>.
"""
    await query.edit_message_text(
        text=final_message,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_to_dashboard_keyboard() # Re-use the back button
    )
    context.user_data.clear()


async def add_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows instructions for adding balance by contacting the admin."""
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.")
        return
    
    # --- NEW: "Contact Admin" message ---
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
