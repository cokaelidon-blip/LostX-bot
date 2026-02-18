# bot.py
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters
)

from config import BOT_TOKEN, ADMIN_IDS
from database import init_database, create_user

from handlers.auth import (
    start, login_start, login_username, login_password, 
    login_cancel, logout, LOGIN_USERNAME, LOGIN_PASSWORD
)
from handlers.user import (
    dashboard_callback, modder_ipa_callback, buy_callback,
    confirm_purchase_callback, balance_callback, history_callback
)
from handlers.admin import (
    admin_panel_callback, admin_users_callback, admin_keys_callback,
    add_key_callback, view_stock_callback, admin_stats_callback,
    admin_create_user_callback, create_user_username, create_user_password,
    admin_add_balance_callback, add_balance_username, add_balance_amount,
    cancel_admin_action, toggle_user_command, reset_device_command,
    CREATE_USER_USERNAME, CREATE_USER_PASSWORD,
    ADD_BALANCE_USERNAME, ADD_BALANCE_AMOUNT
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Initialize database
    init_database()
    
    # Create default admin user (change credentials!)
    create_user("admin", "DoniXLost", is_admin=True)
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Login conversation handler
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(login_start, pattern="^login$")],
        states={
            LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler("cancel", login_cancel)],
    )
    
    # Create user conversation handler
    create_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_create_user_callback, pattern="^admin_create_user$")],
        states={
            CREATE_USER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_user_username)],
            CREATE_USER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_user_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action)],
    )
    
    # Add balance conversation handler
    add_balance_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_balance_callback, pattern="^admin_add_balance$")],
        states={
            ADD_BALANCE_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_username)],
            ADD_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_amount)],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_action)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(login_conv)
    application.add_handler(create_user_conv)
    application.add_handler(add_balance_conv)
    
    # User callbacks
    application.add_handler(CallbackQueryHandler(dashboard_callback, pattern="^dashboard$"))
    application.add_handler(CallbackQueryHandler(modder_ipa_callback, pattern="^modder_ipa$"))
    application.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(confirm_purchase_callback, pattern="^confirm_"))
    application.add_handler(CallbackQueryHandler(balance_callback, pattern="^balance$"))
    application.add_handler(CallbackQueryHandler(history_callback, pattern="^history$"))
    application.add_handler(CallbackQueryHandler(logout, pattern="^logout$"))
    
    # Admin callbacks
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_users_callback, pattern="^admin_users$"))
    application.add_handler(CallbackQueryHandler(admin_keys_callback, pattern="^admin_keys$"))
    application.add_handler(CallbackQueryHandler(add_key_callback, pattern="^add_key_"))
    application.add_handler(CallbackQueryHandler(view_stock_callback, pattern="^view_stock$"))
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern="^admin_stats$"))
    
    # Admin commands
    application.add_handler(CommandHandler("toggleuser", toggle_user_command))
    application.add_handler(CommandHandler("resetdevice", reset_device_command))
    
    # Start bot
    logger.info("Starting Modder IPA Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()