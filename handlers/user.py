# handlers/user.py
import html
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (check_session, get_user_balance, get_available_key,
                      update_balance, sell_key, record_purchase, get_setting)
from keyboards import (get_buy_menu_keyboard, get_confirmation_keyboard,
                       get_back_to_dashboard_keyboard, get_dashboard_keyboard)
from config import PRICING, USDT_ADDRESS, STOCK_MODE


async def dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.", parse_mode=ParseMode.HTML)
        return

    safe_username = html.escape(session['username'])
    dashboard_text = f"""
🎮 <b>Welcome back, {safe_username}!</b>

You are logged in.

💰 Balance: <b>${session['balance']:.2f}</b>
    """
    await query.edit_message_text(dashboard_text,
                                  reply_markup=get_dashboard_keyboard(session['is_admin']),
                                  parse_mode=ParseMode.HTML)


async def modder_ipa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.", parse_mode=ParseMode.HTML)
        return

    # In a real scenario, you'd check if the user has an active subscription
    # For now, we just show a generic message.
    text = """
<b>Modder IPA Information</b>

This section will contain details about the Modder IPA, version info, and perhaps a download link if the user has an active subscription.
    """
    await query.edit_message_text(text,
                                  reply_markup=get_back_to_dashboard_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def buy_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.", parse_mode=ParseMode.HTML)
        return

    text = "Please choose a subscription plan:"
    await query.edit_message_text(text, reply_markup=get_buy_menu_keyboard())


async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace('buy_', '')
    plan = PRICING.get(plan_key)

    if not plan:
        await query.edit_message_text("Invalid plan selected.", reply_markup=get_back_to_dashboard_keyboard())
        return

    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.", parse_mode=ParseMode.HTML)
        return

    user_balance = session['balance']
    plan_price = plan['price']

    text = f"""
<b>Confirm Purchase</b>

You are about to buy: <b>{plan['label']}</b>
Cost: <b>${plan_price:.2f}</b>

Your current balance is <b>${user_balance:.2f}</b>.
"""

    if user_balance >= plan_price:
        text += "\nDo you want to proceed with the purchase from your balance?"
        await query.edit_message_text(text,
                                      reply_markup=get_confirmation_keyboard(plan_key),
                                      parse_mode=ParseMode.HTML)
    else:
        text += f"""
\n⚠️ You have insufficient balance.
Please add funds to your account by sending USDT (TRC20) to the address below.

Your deposit address:
`{USDT_ADDRESS}`

After sending, please contact an admin to have your balance updated.
"""
        await query.edit_message_text(text,
                                      reply_markup=get_back_to_dashboard_keyboard(),
                                      parse_mode=ParseMode.HTML)


async def confirm_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    plan_key = query.data.replace('confirm_', '')
    plan = PRICING.get(plan_key)

    if not plan:
        await query.edit_message_text("Invalid plan selected.", reply_markup=get_back_to_dashboard_keyboard())
        return

    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.", parse_mode=ParseMode.HTML)
        return

    user_id = session['user_id']
    user_balance = session['balance']
    plan_price = plan['price']
    duration_days = plan['days']

    if user_balance < plan_price:
        await query.edit_message_text("Error: Insufficient balance.", reply_markup=get_back_to_dashboard_keyboard())
        return

    key_record = None
    if STOCK_MODE:
        key_record = get_available_key(duration_days)
        if not key_record:
   
