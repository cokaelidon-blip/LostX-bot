# bot.py
import logging
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          ConversationHandler, MessageHandler, filters)

import config
from database import init_database
from handlers.common import (start, login_start, login_username, login_password,
                           cancel_login, logout_callback, unknown_command,
                           USERNAME, PASSWORD)
from handlers.user import * # Import all user handlers
from handlers.admin import * # Import all admin handlers

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

    # --- Conversation Handlers ---
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(login_start, pattern='^login$')],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel_login)],
    )
    
    create_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_create_user_callback, pattern='^admin_create_user$')],
        states={
            CREATE_USER_USERNAME: [MessageHandler(filters.TEXT, create_user_username)],
            CREATE_USER_PASSWORD: [MessageHandler(filters.TEXT, create_user_password)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
    )

    add_balance_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_balance_callback, pattern='^admin_add_balance$')],
        states={
            ADD_BALANCE_USERNAME: [MessageHandler(filters.TEXT, add_balance_username)],
            ADD_BALANCE_AMOUNT: [MessageHandler(filters.TEXT, add_balance_amount)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
    )

    set_link_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_link_start, pattern='^admin_set_ipa_link$')],
        states={SET_IPA_LINK: [MessageHandler(filters.TEXT, admin_receive_new_link)]},
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
    )

    add_keys_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_keys_start, pattern='^admin_add_keys$')],
        states={
            SELECT_KEY_DURATION: [CallbackQueryHandler(select_key_duration, pattern='^add_keys_duration_')],
            RECEIVE_KEYS_LIST: [MessageHandler(filters.TEXT, receive_keys_list)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
    )

    # --- Add All Handlers ---
    application.add_handler(CommandHandler("start", start))
    
    # Conversations
    application.add_handler(login_conv)
    application.add_handler(create_user_conv)
    application.add_handler(add_balance_conv)
    application.add_handler(set_link_conv)
    application.add_handler(add_keys_conv)
    
    # User Callbacks
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout$'))
    application.add_handler(CallbackQueryHandler(dashboard_callback, pattern='^back_to_dashboard$'))
    application.add_handler(CallbackQueryHandler(modder_ipa_menu_callback, pattern='^modder_ipa_menu$'))
    # --- TYPO CORRECTED HERE ---
    application.add_handler(CallbackQueryHandler(buy_key_callback, pattern='^buy_plan_'))
    application.add_handler(CallbackQueryHandler(download_ipa_callback, pattern='^download_ipa$'))
    application.add_handler(CallbackQueryHandler(history_callback, pattern='^history$'))
    application.add_handler(CallbackQueryHandler(check_balance_callback, pattern='^check_balance$'))

    # Admin Callbacks
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_users_callback, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_keys_callback, pattern='^admin_keys$'))
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(view_stock_callback, pattern='^view_stock$'))
    
    # Fallback
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logging.info("Starting Modder IPA Bot...")
    application.run_polling()


if __name__ == '__main__':
    main()
