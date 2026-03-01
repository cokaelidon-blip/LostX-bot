# handlers/user.py
import html
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (check_session, get_user_by_telegram_id, 
                      get_user_purchase_history, get_setting, 
                      find_available_key, assign_key_to_user, update_balance, get_key_stock)

from keyboards import (get_dashboard_keyboard, get_ipa_menu_keyboard,
                       get_buy_key_keyboard)
                       
from config import PRICING

# --- Dashboard Navigation ---

async def back_to_dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigates back to the main user dashboard."""
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        await query.edit_message_text("Your session has expired. Please /start again.")
        return

    text = f"Welcome back, {html.escape(session['username'])}!"
    await query.edit_message_text(text, reply_markup=get_dashboard_keyboard(session.get('is_admin')), parse_mode=ParseMode.HTML)

# --- IPA Menu ---

async def modder_ipa_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the IPA download and purchase menu."""
    query = update.callback_query
    await query.answer()
    text = "📱 *Modder IPA Menu*\n\nSelect an option below."
    await query.edit_message_text(text, reply_markup=get_ipa_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def download_ipa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides the user with the IPA download link."""
    query = update.callback_query
    await query.answer()
    link = get_setting('ipa_download_link', 'No download link has been set by the admin yet.')
    await query.message.reply_text(f"Here is the link to download the IPA:\n{link}")

# --- User Information ---

async def check_balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the user's current balance."""
    query = update.callback_query
    session = check_session(update.effective_user.id)
    if not session:
        await query.answer("Session expired. Please /start again.", show_alert=True)
        return

    user_db = get_user_by_telegram_id(update.effective_user.id)
    
    # --- THIS IS THE FIX ---
    # Changed from the faulty user_db.get('balance') to the correct user_db['balance']
    balance = user_db['balance'] if user_db else 0.0
    
    await query.answer(f"Your current balance is: ${balance:.2f}", show_alert=True)

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
        history_list = [f"- `{item['key']}` ({item['duration_days']} days) on {item['activation_date']}" for item in history_items]
        history_text = "📜 *Your Purchase History*\n\n" + "\n".join(history_list)

    await query.edit_message_text(history_text, reply_markup=get_dashboard_keyboard(session.get('is_admin')), parse_mode=ParseMode.MARKDOWN)

# --- Purchase Flow ---

async def buy_key_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the menu for buying different key durations, including stock info."""
    query = update.callback_query
    await query.answer()

    stock_data = get_key_stock()
    stock_map = {item['duration_days']: item['count'] for item in stock_data}

    stock_text = (
        f"📦 *Current Stock*\n"
        f"1-Day Keys: {stock_map.get(1, 0)}\n"
        f"7-Day Keys: {stock_map.get(7, 0)}\n"
        f"30-Day Keys: {stock_map.get(30, 0)}\n\n"
    )

    main_text = "🛒 *Buy Key*\n\nSelect a plan to purchase. The cost will be deducted from your balance."
    full_text = stock_text + main_text
    
    await query.edit_message_text(
        text=full_text, 
        reply_markup=get_buy_key_keyboard(), 
        parse_mode=ParseMode.MARKDOWN
    )

async def buy_key_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the actual key purchase logic."""
    query = update.callback_query
    plan_id = query.data.split('_', 1)[1]
    
    if plan_id not in PRICING:
        await query.answer("Invalid plan selected.", show_alert=True)
        return

    plan = PRICING[plan_id]
    price = plan['price']
    duration = plan['days']

    session = check_session(update.effective_user.id)
    if not session:
        await query.answer("Session expired. Please /start again.", show_alert=True)
        return
    
    user_db = get_user_by_telegram_id(update.effective_user.id)
    if not user_db or user_db['balance'] < price:
        current_balance = user_db['balance'] if user_db else 0.0
        await query.answer(f"Insufficient balance. You need ${price:.2f}, but you only have ${current_balance:.2f}.", show_alert=True)
        return

    key_data = find_available_key(duration)
    if not key_data:
        await query.answer(f"Sorry, {duration}-day keys are out of stock. Please contact an admin.", show_alert=True)
        return

    try:
        await query.answer("Processing your purchase...")
        update_balance(user_db['id'], price, 'debit')
        assign_key_to_user(key_data['id'], user_db['id'])
        
        success_text = (
            f"✅ *Purchase Successful!*\n\n"
            f"Your new {duration}-day access key is:\n\n"
            f"`{key_data['key']}`\n\n"
            f"${price:.2f} has been deducted from your balance."
        )
        await query.message.reply_text(success_text, parse_mode=ParseMode.MARKDOWN)
        await query.edit_message_text("📱 *Modder IPA Menu*\n\nSelect an option below.", reply_markup=get_ipa_menu_keyboard(), parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await query.message.reply_text("An unexpected error occurred. Please try again or contact support.")
        update_balance(user_db['id'], price, 'credit')
