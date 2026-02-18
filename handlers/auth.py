# handlers/auth.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database import authenticate_user, logout_user, check_session
from keyboards import get_start_keyboard, get_dashboard_keyboard

# Conversation states
LOGIN_USERNAME, LOGIN_PASSWORD = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    
    # Check if user already logged in (AUTO-LOGIN CHECK)
    session = check_session(telegram_id)
    
    if session:
        # User is already logged in, show dashboard directly
        await show_dashboard(update, context, session)
        return ConversationHandler.END
    
    welcome_text = """
🎮 *Welcome to Modder IPA Bot!*

This bot provides premium IPA keys for your needs.

Please login to access the dashboard.
If you don't have an account, contact the admin.
    """
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            welcome_text,
            reply_markup=get_start_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=get_start_keyboard(),
            parse_mode='Markdown'
        )

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    
    # Check if already logged in
    session = check_session(telegram_id)
    if session:
        await show_dashboard(update, context, session)
        return ConversationHandler.END
    
    await query.edit_message_text(
        "🔐 *Login Process*\n\nPlease enter your username:",
        parse_mode='Markdown'
    )
    
    return LOGIN_USERNAME

async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['login_username'] = update.message.text
    
    await update.message.reply_text(
        "🔑 Now enter your password:"
    )
    
    return LOGIN_PASSWORD

async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get('login_username')
    password = update.message.text
    telegram_id = update.effective_user.id
    
    # Delete the password message for security
    try:
        await update.message.delete()
    except:
        pass
    
    success, result = authenticate_user(username, password, telegram_id)
    
    if success:
        session = check_session(telegram_id)
        await update.message.reply_text(
            f"✅ *Login Successful!*\n\nWelcome, *{username}*!\n\n💡 You will stay logged in until you logout.",
            parse_mode='Markdown'
        )
        await show_dashboard_message(update, context, session)
    else:
        await update.message.reply_text(
            f"❌ *Login Failed*\n\n{result}\n\nPlease try again or contact admin.",
            reply_markup=get_start_keyboard(),
            parse_mode='Markdown'
        )
    
    return ConversationHandler.END

async def login_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Login cancelled.",
        reply_markup=get_start_keyboard()
    )
    return ConversationHandler.END

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, session):
    dashboard_text = f"""
🎮 *Modder IPA Dashboard*

👤 User: *{session['username']}*
💰 Balance: *${session['balance']:.2f}*

Select an option below:
    """
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            dashboard_text,
            reply_markup=get_dashboard_keyboard(session['is_admin']),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            dashboard_text,
            reply_markup=get_dashboard_keyboard(session['is_admin']),
            parse_mode='Markdown'
        )

async def show_dashboard_message(update: Update, context: ContextTypes.DEFAULT_TYPE, session):
    dashboard_text = f"""
🎮 *Modder IPA Dashboard*

👤 User: *{session['username']}*
💰 Balance: *${session['balance']:.2f}*

Select an option below:
    """
    
    await update.message.reply_text(
        dashboard_text,
        reply_markup=get_dashboard_keyboard(session['is_admin']),
        parse_mode='Markdown'
    )

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    logout_user(telegram_id)
    
    await query.edit_message_text(
        "👋 You have been logged out successfully!\n\nYou will need to login again next time.",
        reply_markup=get_start_keyboard()
    )