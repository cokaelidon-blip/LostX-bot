# handlers/user.py
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    check_session, get_user_balance, get_available_key, 
    sell_key, update_balance, record_purchase, get_stock_count
)
from keyboards import (
    get_pricing_keyboard, get_confirm_purchase_keyboard, 
    get_back_keyboard, get_dashboard_keyboard
)
from config import PRICING, STOCK_MODE, USDT_ADDRESS, ADMIN_USERNAME

async def dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not session:
        await query.edit_message_text(
            "❌ Session expired. Please login again.",
            reply_markup=get_start_keyboard()
        )
        return
    
    dashboard_text = f"""
🎮 *Modder IPA Dashboard*

👤 User: *{session['username']}*
💰 Balance: *${session['balance']:.2f}*

Select an option below:
    """
    
    await query.edit_message_text(
        dashboard_text,
        reply_markup=get_dashboard_keyboard(session['is_admin']),
        parse_mode='Markdown'
    )

async def modder_ipa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text(
            "❌ Session expired. Please login again.",
            reply_markup=get_start_keyboard()
        )
        return
    
    # Get stock info if in stock mode
    stock_info = ""
    if STOCK_MODE:
        stock = get_stock_count()
        stock_info = "\n📦 *Stock Available:*\n"
        stock_info += f"• 1 Day: {stock.get(1, 0)} keys\n"
        stock_info += f"• 7 Days: {stock.get(7, 0)} keys\n"
        stock_info += f"• 1 Month: {stock.get(30, 0)} keys\n"
    
    text = f"""
🔑 *Modder IPA Keys*

Select the duration you need:
{stock_info}
💰 Your Balance: *${session['balance']:.2f}*
    """
    
    await query.edit_message_text(
        text,
        reply_markup=get_pricing_keyboard(),
        parse_mode='Markdown'
    )

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text(
            "❌ Session expired. Please login again.",
            reply_markup=get_start_keyboard()
        )
        return
    
    plan_key = query.data.replace("buy_", "")
    plan = PRICING.get(plan_key)
    
    if not plan:
        await query.edit_message_text("Invalid plan selected.")
        return
    
    # Check stock if in stock mode
    if STOCK_MODE:
        available = get_available_key(plan['days'])
        if not available:
            await query.edit_message_text(
                f"❌ *Out of Stock*\n\nSorry, {plan['label']} keys are currently out of stock.\n\nPlease contact admin @{ADMIN_USERNAME} or try again later.",
                reply_markup=get_back_keyboard(),
                parse_mode='Markdown'
            )
            return
    
    # Check balance
    if session['balance'] < plan['price']:
        await query.edit_message_text(
            f"❌ *Insufficient Balance*\n\n"
            f"Required: *${plan['price']:.2f}*\n"
            f"Your Balance: *${session['balance']:.2f}*\n\n"
            f"Please contact admin @{ADMIN_USERNAME} to add balance.\n\n"
            f"💳 *USDT (TRC20) Address:*\n`{USDT_ADDRESS}`",
            reply_markup=get_back_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    text = f"""
🛒 *Confirm Purchase*

📦 Product: *Modder IPA Key*
📅 Duration: *{plan['label']}*
💰 Price: *${plan['price']:.2f}*

Your Balance: *${session['balance']:.2f}*
After Purchase: *${session['balance'] - plan['price']:.2f}*

Confirm your purchase?
    """
    
    await query.edit_message_text(
        text,
        reply_markup=get_confirm_purchase_keyboard(plan_key),
        parse_mode='Markdown'
    )

async def confirm_purchase_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text(
            "❌ Session expired. Please login again.",
            reply_markup=get_start_keyboard()
        )
        return
    
    plan_key = query.data.replace("confirm_", "")
    plan = PRICING.get(plan_key)
    
    if not plan:
        await query.edit_message_text("Invalid plan selected.")
        return
    
    # Double check balance
    current_balance = get_user_balance(session['user_id'])
    if current_balance < plan['price']:
        await query.edit_message_text(
            "❌ Insufficient balance. Please add funds first.",
            reply_markup=get_back_keyboard()
        )
        return
    
    # Get and sell key
    if STOCK_MODE:
        key_data = get_available_key(plan['days'])
        if not key_data:
            await query.edit_message_text(
                "❌ Sorry, this key is no longer available.",
                reply_markup=get_back_keyboard()
            )
            return
        
        key_id, key_value = key_data
        sell_key(key_id, session['user_id'])
    else:
        # Auto-generate mode
        from database import add_key_to_stock, generate_key
        key_value = generate_key()
        success, _ = add_key_to_stock(plan['days'], key_value)
        key_id = None
    
    # Deduct balance
    update_balance(
        session['user_id'], 
        -plan['price'], 
        'purchase', 
        f"Purchased {plan['days']} day key"
    )
    
    # Record purchase
    record_purchase(session['user_id'], key_id, plan['price'], plan['days'])
    
    success_text = f"""
✅ *Purchase Successful!*

🔑 *Your Key:*
`{key_value}`

📅 Duration: *{plan['label']}*
💰 Amount Paid: *${plan['price']:.2f}*

⚠️ *Important:* Save this key! It won't be shown again.

Thank you for your purchase!
    """
    
    await query.edit_message_text(
        success_text,
        reply_markup=get_back_keyboard(),
        parse_mode='Markdown'
    )

async def balance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text(
            "❌ Session expired. Please login again.",
            reply_markup=get_start_keyboard()
        )
        return
    
    text = f"""
💰 *Your Balance*

Current Balance: *${session['balance']:.2f}*

To add funds, contact admin @{ADMIN_USERNAME}

💳 *USDT (TRC20) Address:*
`{USDT_ADDRESS}`

Send the amount and transaction proof to admin.
    """
    
    await query.edit_message_text(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode='Markdown'
    )

async def history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    session = check_session(telegram_id)
    
    if not session:
        from keyboards import get_start_keyboard
        await query.edit_message_text(
            "❌ Session expired. Please login again.",
            reply_markup=get_start_keyboard()
        )
        return
    
    from database import get_connection
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT amount, duration_days, purchased_at 
        FROM purchases 
        WHERE user_id = ? 
        ORDER BY purchased_at DESC 
        LIMIT 10
    ''', (session['user_id'],))
    
    purchases = cursor.fetchall()
    conn.close()
    
    if not purchases:
        text = "📜 *Purchase History*\n\nNo purchases yet."
    else:
        text = "📜 *Purchase History (Last 10)*\n\n"
        for i, (amount, days, date) in enumerate(purchases, 1):
            text += f"{i}. {days} days - ${amount:.2f} - {date[:10]}\n"
    
    await query.edit_message_text(
        text,
        reply_markup=get_back_keyboard(),
        parse_mode='Markdown'
    )