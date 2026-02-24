# handlers/user.py
import html
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (check_session, get_user_by_telegram_id, get_setting, find_available_key,
                      assign_key_to_user, update_balance, get_user_purchase_history,
                      get_key_stock) # <-- Added get_key_stock
from keyboards import (get_main_dashboard_keyboard, get_modder_ipa_keyboard,
                       get_back_to_dashboard_keyboard)
from config import PRICING

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, session: dict):
    """Displays the main user dashboard."""
    query = update.callback_query
    safe_username = html.escape(session['username'])
    
    current_user_state = get_user_by_telegram_id(session['telegram_id'])
    
    dashboard_text = f"""
👋 Welcome, <b>{safe_username}</b>!

💰 Your Balance: <b>${current_user_state['balance']:.2f}</b>

Please choose an option below.
    """
    keyboard = get_main_dashboard_keyboard(current_user_state['is_admin'])
    
    if query:
        await query.edit_message_text(dashboard_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=dashboard_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )


async def dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the 'Back to Dashboard' button."""
    session = check_session(update.effective_user.id)
    if not session:
        await update.callback_query.edit_message_text("Your session has expired. Please /start again.")
        return
    await show_dashboard(update, context, session)


async def check_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refreshes the dashboard to show the latest balance."""
    query = update.callback_query
    await query.answer(text="🔄 Refreshing balance...", show_alert=False)
    await dashboard_callback(update, context)


async def history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the user's purchase history."""
    query = update.callback_query
    await query.answer()

    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.")
        return

    history_items = get_user_purchase_history(session['id'])

    if not history_items:
        history_text = "You have no purchase history."
    else:
        formatted_items = []
        for item in history_items:
            formatted_items.append(
                f"• <b>{item['duration_days']}-Day Key</b> (<code>{item['key']}</code>)\n  Purchased on: {item['activation_date']}"
            )
        history_text = "📜 <b>Your Purchase History</b>\n\n" + "\n\n".join(formatted_items)

    await query.edit_message_text(
        history_text,
        reply_markup=get_back_to_dashboard_keyboard(),
        parse_mode=ParseMode.HTML
    )


async def modder_ipa_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the Modder IPA menu with buy options AND current stock."""
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.")
        return

    # --- NEW LOGIC TO FETCH AND DISPLAY STOCK ---
    stock_levels = get_key_stock()
    stock_dict = {item['duration_days']: item['count'] for item in stock_levels}
    
    stock_text_lines = []
    # Loop through pricing to maintain a consistent order
    for plan_key, plan_details in PRICING.items():
        days = plan_details['days']
        label = plan_details['label']
        count = stock_dict.get(days, 0) # Get count, default to 0 if not in stock
        stock_text_lines.append(f"     - {label}: {count} keys")

    if not stock_text_lines:
        stock_display = "   All items are currently out of stock."
    else:
        stock_display = "\n".join(stock_text_lines)

    text = f"""📱 <b>Modder IPA Menu</b>

   <b>Stock:</b>
{stock_display}

Please select an option to continue.
"""
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
    
    current_user_state = get_user_by_telegram_id(session['telegram_id'])
    user_balance = current_user_state['balance']

    if user_balance < price:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ <b>Purchase Failed</b>\n\nYour balance of ${user_balance:.2f} is not enough to buy the {plan['label']} plan for ${price:.2f}.",
            parse_mode=ParseMode.HTML
        )
        return

    available_key = find_available_key(duration)
    if not available_key:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"❌ <b>Out of Stock</b>\n\nWe are currently out of stock for {plan['label']} keys. Please try again later.",
            parse_mode=ParseMode.HTML
        )
        return
        
    update_balance(user_id, price, 'debit')
    assign_key_to_user(available_key['id'], user_id)
    
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
