# bot.py
import logging
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          ConversationHandler, MessageHandler, filters)

import config
from database import init_database
from handlers.common import (start, login_start, login_username, login_password,
                           cancel_login, logout_callback, unknown_command,
                           USERNAME, PASSWORD)
# Updated user handlers
from handlers.user import (dashboard_callback, modder_ipa_menu_callback,
                           buy_key_callback, download_ipa_callback, history_callback)
# Admin handlers remain for the next phase
from handlers.admin import *

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

def main() -> None:
    """Start the bot."""
    init_database()
    logging.info("Database initialized successfully.")

    application = Application.builder().token(config.BOT_TOKEN).build()

    # Conversation handlers (unchanged)
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(login_start, pattern='^login$')],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel_login)],
        per_user=True, per_chat=True,
    )
    # Admin conversations will be re-integrated in the next phase

    # Command Handlers
    application.add_handler(CommandHandler("start", start))

    # Add Conversation Handlers to Application
    application.add_handler(login_conv)

    # --- NEW & UPDATED Callback Query Handlers (User) ---
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout$'))
    application.add_handler(CallbackQueryHandler(dashboard_callback, pattern='^back_to_dashboard$'))
    application.add_handler(CallbackQueryHandler(modder_ipa_menu_callback, pattern='^modder_ipa_menu$'))
    application.add_handler(CallbackQueryHandler(buy_key_callback, pattern='^buy_plan_')) # Handles all buy buttons
    application.add_handler(CallbackQueryHandler(download_ipa_callback, pattern='^download_ipa$'))
    application.add_handler(CallbackQueryHandler(history_callback, pattern='^history$'))
    
    # --- Admin handlers will be re-activated here in the next step ---
    # application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern='^admin_panel$'))

    # Fallback for unknown commands
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logging.info("Starting Modder IPA Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
