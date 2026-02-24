# handlers/user.py
import html
import psycopg2.extras
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import (check_session, get_user_balance, get_available_key,
                      sell_key, update_balance, record_purchase,
                      get_stock_count, get_setting, get_connection)
from keyboards import (get_pricing_keyboard, get_confirm_purchase_keyboard,
                       get_back_keyboard, get_dashboard_keyboard,
                       get_modder_ipa_keyboard)

from config import PRICING, STOCK_MODE, USDT_ADDRESS, ADMIN_USERNAME


async def dashboard_callback(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text("❌ Session expired. Please login again.", reply_markup=get_start_keyboard())
        return

    safe_username = html.escape(session['username'])
    dashboard_text = f"""
🎮 <b>Modder IPA Dashboard</b>

👤 User: <b>{safe_username}</b>
💰 Balance: <b>${session['balance']:.2f}</b>

Select an option below:
    """
    await query.edit_message_text(dashboard_text,
                                  reply_markup=get_dashboard_keyboard(session['is_admin']),
                                  parse_mode=ParseMode.HTML)


async def modder_ipa_callback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not check_session(update.effective_user.id):
        from keyboards import get_start_keyboard
        await query.edit_message_text("❌ Session expired. Please login again.", reply_markup=get_start_keyboard())
        return

    await query.edit_message_text(text="<b>🔑 Modder IPA Menu</b>\n\nSelect an option below.",
                                  reply_markup=get_modder_ipa_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def buy_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text("❌ Session expired. Please login again.", reply_markup=get_start_keyboard())
        return

    stock_info = ""
    if STOCK_MODE:
        stock = get_stock_count()
        stock_info = "\n📦 <b>Stock Available:</b>\n"
        stock_info += f"• 1 Day: {stock.get(1, 0)} keys\n"
        stock_info += f"• 7 Days: {stock.get(7, 0)} keys\n"
        stock_info += f"• 1 Month: {stock.get(30, 0)} keys\n"

    text = f"""
🔑 <b>Buy Modder IPA Key</b>

Select the duration you need:{stock_info}

💰 Your Balance: <b>${session['balance']:.2f}</b>
    """
    await query.edit_message_text(text,
                                  reply_markup=get_pricing_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text("❌ Session expired. Please login again.", reply_markup=get_start_keyboard())
        return

    plan_key = query.data.replace("buy_", "")
    plan = PRICING.get(plan_key)
    if not plan:
        await query.edit_message_text("Invalid plan selected.")
        return

    safe_admin_username = html.escape(ADMIN_USERNAME)
    safe_usdt_address = html.escape(USDT_ADDRESS)

    if STOCK_MODE:
        if not get_available_key(plan['days']):
            await query.edit_message_text(f"❌ <b>Out of Stock</b>\n\nSorry, {plan['label']} keys are currently out of stock.\n\nPlease contact admin @{safe_admin_username} or try again later.",
                                          reply_markup=get_back_keyboard(),
                                          parse_mode=ParseMode.HTML)
            return

    if session['balance'] < plan['price']:
        await query.edit_message_text(f"❌ <b>Insufficient Balance</b>\n\nRequired: <b>${plan['price']:.2f}</b>\nYour Balance: <b>${session['balance']:.2f}</b>\n\nPlease contact admin @{safe_admin_username} to add balance.\n\n💳 <b>USDT (TRC20) Address:</b>\n<code>{safe_usdt_address}</code>",
                                      reply_markup=get_back_keyboard(),
                                      parse_mode=ParseMode.HTML)
        return

    text = f"""
🛒 <b>Confirm Purchase</b>

📦 Product: <b>Modder IPA Key</b>
📅 Duration: <b>{html.escape(plan['label'])}</b>
💰 Price: <b>${plan['price']:.2f}</b>

Your Balance: <b>${session['balance']:.2f}</b>
After Purchase: <b>${session['balance'] - plan['price']:.2f}</b>

Confirm your purchase?
    """
    await query.edit_message_text(text,
                                  reply_markup=get_confirm_purchase_keyboard(plan_key),
                                  parse_mode=ParseMode.HTML)


async def confirm_purchase_callback(update: Update,
                                    context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text("❌ Session expired. Please login again.", reply_markup=get_start_keyboard())
        return

    plan_key = query.data.replace("confirm_", "")
    plan = PRICING.get(plan_key)
    if not plan:
        await query.edit_message_text("Invalid plan selected.")
        return

    if get_user_balance(session['user_id']) < plan['price']:
        await query.edit_message_text("❌ Insufficient balance. Please add funds first.", reply_markup=get_back_keyboard())
        return

    key_id, key_value = None, None
    if STOCK_MODE:
        key_data = get_available_key(plan['days'])
        if not key_data:
            await query.edit_message_text("❌ Sorry, this key is no longer available.", reply_markup=get_back_keyboard())
            return
        key_id, key_value = key_data['id'], key_data['key_value']
        sell_key(key_id, session['user_id'])
    else:
        from database import add_key_to_stock, generate_key
        key_value = generate_key()
        success, _ = add_key_to_stock(plan['days'], key_value)

    update_balance(session['user_id'], -plan['price'], 'purchase', f"Purchased {plan['days']} day key")
    record_purchase(session['user_id'], key_id, plan['price'], plan['days'])
    safe_key_value = html.escape(key_value)

    success_text = f"""
✅ <b>Purchase Successful!</b>

🔑 <b>Your Key:</b>
<code>{safe_key_value}</code>

📅 Duration: <b>{html.escape(plan['label'])}</b>
💰 Amount Paid: <b>${plan['price']:.2f}</b>

⚠️ <b>Important:</b> Save this key! It won't be shown again.

Thank you for your purchase!
    """
    await query.edit_message_text(success_text,
                                  reply_markup=get_back_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text("❌ Session expired. Please login again.", reply_markup=get_start_keyboard())
        return

    safe_admin_username = html.escape(ADMIN_USERNAME)
    safe_usdt_address = html.escape(USDT_ADDRESS)

    text = f"""
💰 <b>Your Balance</b>

Current Balance: <b>${session['balance']:.2f}</b>

To add funds, contact admin @{safe_admin_username}

💳 <b>USDT (TRC20) Address:</b>
<code>{safe_usdt_address}</code>

Send the amount and transaction proof to admin.
    """
    await query.edit_message_text(text,
                                  reply_markup=get_back_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    session = check_session(update.effective_user.id)
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text("❌ Session expired. Please login again.", reply_markup=get_start_keyboard())
        return

    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT amount, duration_days, purchased_at FROM purchases WHERE user_id = %s ORDER BY purchased_at DESC LIMIT 10', (session['user_id'],))
    purchases = cursor.fetchall()
    cursor.close()
    conn.close()

    if not purchases:
        text = "📜 <b>Purchase History</b>\n\nNo purchases yet."
    else:
        text = "📜 <b>Purchase History (Last 10)</b>\n\n"
        for i, purchase in enumerate(purchases, 1):
            amount = purchase['amount']
            days = purchase['duration_days']
            date = purchase['purchased_at']
            text += f"{i}. {days} days - ${amount:.2f} - {html.escape(str(date)[:10])}\n"

    await query.edit_message_text(text,
                                  reply_markup=get_back_keyboard(),
                                  parse_mode=ParseMode.HTML)


async def ipa_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not check_session(update.effective_user.id):
        from keyboards import get_start_keyboard
        await query.edit_message_text("❌ Session expired. Please login again.", reply_markup=get_start_keyboard())
        return

    ipa_link = get_setting('ipa_link')
    if ipa_link:
        safe_ipa_link = html.escape(ipa_link)
        text = f"🔗 <b>Here is the latest IPA link:</b>\n\n<code>{safe_ipa_link}</code>"
    else:
        text = "❌ The IPA link has not been set by the admin yet. Please check back later."
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=text,
                                   parse_mode=ParseMode.HTML)
