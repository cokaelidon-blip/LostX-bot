# bot.py
import logging
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          ConversationHandler, MessageHandler, filters)

import config
from database import init_database
from handlers.common import (start, login_start, login_username, login_password,
                           cancel_login, logout_callback, unknown_command,
                           USERNAME, PASSWORD)
from handlers.user import (dashboard_callback, download_ipa_callback, add_balance_callback)
from handlers.admin import (admin_panel_callback, admin_users_callback, admin_keys_callback,
                          view_stock_callback, admin_stats_callback, cancel_admin_action,
                          admin_create_user_callback, create_user_username, create_user_password,
                          admin_add_balance_callback, add_balance_username, add_balance_amount,
                          toggle_user_command, reset_device_command,
                          admin_set_link_start, admin_receive_new_link,
                          add_custom_keys_start, select_key_duration, receive_keys_list,
                          cancel_bulk_add, CREATE_USER_USERNAME, CREATE_USER_PASSWORD,
                          ADD_BALANCE_USERNAME, ADD_BALANCE_AMOUNT, SET_IPA_LINK,
                          SELECT_KEY_DURATION, RECEIVE_KEYS_LIST) # Correctly imported here

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

# Suppress noisy HTTPX logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext.Application").setLevel(logging.INFO)


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
        per_user=True,
        per_chat=True,
    )

    create_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_create_user_callback, pattern='^admin_create_user$')],
        states={
            CREATE_USER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_user_username)],
            CREATE_USER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_user_password)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
    )

    add_balance_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_balance_callback, pattern='^admin_add_balance$')],
        states={
            ADD_BALANCE_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_username)],
            ADD_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_amount)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
    )

    set_link_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_link_start, pattern='^admin_set_ipa_link$')],
        states={
            SET_IPA_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_new_link)]
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
    )

    add_keys_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_custom_keys_start, pattern='^admin_add_custom_keys$')],
        states={
            SELECT_KEY_DURATION: [CallbackQueryHandler(select_key_duration, pattern='^add_keys_duration_')],
            # THIS IS THE CORRECTED LINE:
            RECEIVE_KEYS_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_keys_list)],
        },
        fallbacks=[CallbackQueryHandler(cancel_bulk_add, pattern='^cancel_bulk_add$')],
    )

    # --- Command Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("toggleuser", toggle_user_command))
    application.add_handler(CommandHandler("resetdevice", reset_device_command))

    # --- Add Conversation Handlers to Application ---
    application.add_handler(login_conv)
    application.add_handler(create_user_conv)
    application.add_handler(add_balance_conv)
    application.add_handler(set_link_conv)
    application.add_handler(add_keys_conv)

    # --- Callback Query Handlers (User) ---
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout$'))
    application.add_handler(CallbackQueryHandler(dashboard_callback, pattern='^back_to_dashboard$'))
    application.add_handler(CallbackQueryHandler(add_balance_callback, pattern='^add_balance$'))
    application.add_handler(CallbackQueryHandler(download_ipa_callback, pattern='^download_ipa$'))

    # --- Callback Query Handlers (Admin) ---
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_users_callback, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_keys_callback, pattern='^admin_keys$'))
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(view_stock_callback, pattern='^view_stock$'))
    application.add_handler(CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$'))

    # --- Fallback for unknown commands ---
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logging.info("Starting Modder IPA Bot...")
    application.run_polling()


if __name__ == '__main__':
    main()
