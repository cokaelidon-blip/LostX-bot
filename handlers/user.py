# handlers/user.py
import html
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (check_session, get_setting, find_available_key,
                      assign_key_to_user, update_balance)
from keyboards import (get_main_dashboard_keyboard, get_modder_ipa_keyboard,
                       get_back_to_dashboard_keyboard)
from config import PRICING

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    """Displays the main user dashboard."""
    query = update.callback_query
    safe_username = html.escape(session['username'])
    dashboard_text = f"""
👋 Welcome, <b>{safe_username}</b>!

💰 Your Balance: <b>${session['balance']:.2f}</b>

Please choose an option below.
    """
    keyboard = get_main_dashboard_keyboard(session['is_admin'])
    
    if query:
        await query.edit_message_text(dashboard_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(dashboard_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)

async def dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the 'Back to Dashboard' button."""
    session = check_session(update.effective_user.id)
    if not session:
        await update.callback_query.edit_message_text("Your session has expired. Please /start again.")
        return
    await show_dashboard(update, context, session)

async def modder_ipa_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the Modder IPA menu with buy options."""
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.")
        return

    text = "📱 <b>Modder IPA Menu</b>\n\nPlease select an option to continue."
    await query.edit_message_text(text, reply_markup=get_modder_ipa_keyboard(), parse_mode=ParseMode.HTML)

async def buy_key_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the logic when a user clicks a 'Buy' button."""
    query = update.callback_query
    await query.answer()

    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.")
        return

    plan_key = query.data.replace('buy_plan_', '')
    plan = PRICING.get(plan_key)

    if not plan:
        await query.edit_message_text("❌ Error: Plan not found.", reply_markup=get_back_to_dashboard_keyboard())
        return

    price = plan['price']
    duration = plan['days']
    user_id = session['id']
    user_balance = session['balance']

    # 1. Check user balance
    if user_balance < price:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ <b>Purchase Failed</b>\n\nYour balance of ${user_balance:.2f} is not enough to buy the {plan['label']} plan for ${price:.2f}.",
            parse_mode=ParseMode.HTML
        )
        return

    # 2. Check for key in stock
    available_key = find_available_key(duration)
    if not available_key:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ <b>Out of Stock</b>\n\nWe are currently out of stock for {plan['label']} keys. Please try again later.",
            parse_mode=ParseMode.HTML
        )
        return
        
    # 3. Process the purchase
    # a. Deduct balance
    success, _ = update_balance(user_id, price, 'debit')
    if not success:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="An unexpected error occurred while updating your balance.")
        return

    # b. Assign key
    assign_key_to_user(available_key['id'], user_id)
    
    # 4. Notify user
    success_text = f"""
✅ <b>Purchase Successful!</b>

You have purchased the <b>{plan['label']}</b> plan.

Your license key is:
<pre>{available_key['key']}</pre>

Your new balance is <b>${user_balance - price:.2f}</b>.
    """
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=success_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_to_dashboard_keyboard()
    )

async def download_ipa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides the IPA download link."""
    query = update.callback_query
    await query.answer()
    ipa_link = get_setting('ipa_download_link')
    if not ipa_link:
        text = "The download link has not been set by the admin yet. Please check back later."
    else:
        text = f"⬇️ Here is your download link:\n\n{ipa_link}"
    await query.edit_message_text(text, reply_markup=get_back_to_dashboard_keyboard(), disable_web_page_preview=True)

# Placeholder for history function
async def history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("This feature is coming soon!", show_alert=True)
