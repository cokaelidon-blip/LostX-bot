# bot.py
import logging
from telegram import Update
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, filters, ConversationHandler,
                          ContextTypes)

# Import configurations and handlers
import config
from database import init_database
from handlers.common import (start, login_start, login_username,
                             login_password, register_start,
                             register_username, register_password,
                             cancel_login, logout_callback, unknown_command)
from handlers.user import (dashboard_callback, modder_ipa_callback,
                           buy_menu_callback, buy_callback,
                           confirm_purchase_callback, balance_callback,
                           history_callback, ipa_link_callback)
from handlers.admin import (
    admin_panel_callback, admin_users_callback, admin_keys_callback,
    view_stock_callback, admin_stats_callback, admin_create_user_callback,
    create_user_username, create_user_password, admin_add_balance_callback,
    add_balance_username, add_balance_amount, cancel_admin_action,
    toggle_user_command, reset_device_command, admin_set_link_start,
    admin_receive_new_link,
    # NEW imports for bulk key add
    add_custom_keys_start,
    select_key_duration,
    receive_keys_list,
    cancel_bulk_add,
    # States
    CREATE_USER_USERNAME,
    CREATE_USER_PASSWORD,
    ADD_BALANCE_USERNAME,
    ADD_BALANCE_AMOUNT,
    SET_IPA_LINK,
    SELECT_KEY_DURATION,
    RECEIVE_KEYS_LIST)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)


def main() -> None:
    # Initialize database
    init_database()

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(config.BOT_TOKEN).build()

    # --- Conversation Handlers ---
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(login_start, pattern='^login$')],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel_login)],
        per_message=False)

    register_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(register_start, pattern='^register$')
        ],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_username)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel_login)],
        per_message=False)
    
    create_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_create_user_callback, pattern='^admin_create_user$')],
        states={
            CREATE_USER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_user_username)],
            CREATE_USER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_user_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_action), CallbackQueryHandler(cancel_admin_action, pattern='^cancel$')],
        per_message=False)

    add_balance_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_balance_callback, pattern='^admin_add_balance$')],
        states={
            ADD_BALANCE_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_username)],
            ADD_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_amount)],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_action), CallbackQueryHandler(cancel_admin_action, pattern='^cancel$')],
        per_message=False)

    set_link_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_link_start, pattern='^admin_set_link$')],
        states={
            SET_IPA_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_new_link)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin_action)],
        per_message=False)

    add_keys_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_custom_keys_start, pattern='^add_custom_keys_start$')],
        states={
            SELECT_KEY_DURATION: [CallbackQueryHandler(select_key_duration, pattern='^duration_select_')],
            RECEIVE_KEYS_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_keys_list)],
        },
        fallbacks=[CallbackQueryHandler(cancel_bulk_add, pattern='^cancel_bulk_add$'), CommandHandler('cancel', cancel_bulk_add)],
        per_message=False)

    application.add_handler(login_conv)
    application.add_handler(register_conv)
    application.add_handler(create_user_conv)
    application.add_handler(add_balance_conv)
    application.add_handler(set_link_conv)
    application.add_handler(add_keys_conv)

    # --- Command Handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("toggleuser", toggle_user_command))
    application.add_handler(CommandHandler("resetdevice", reset_device_command))

    # --- CallbackQuery Handlers for buttons ---
    application.add_handler(CallbackQueryHandler(dashboard_callback, pattern='^dashboard$'))
    application.add_handler(CallbackQueryHandler(modder_ipa_callback, pattern='^modder_ipa$'))
    application.add_handler(CallbackQueryHandler(buy_menu_callback, pattern='^buy_menu$'))
    application.add_handler(CallbackQueryHandler(buy_callback, pattern='^buy_'))
    application.add_handler(CallbackQueryHandler(confirm_purchase_callback, pattern='^confirm_'))
    application.add_handler(CallbackQueryHandler(balance_callback, pattern='^balance$'))
    application.add_handler(CallbackQueryHandler(history_callback, pattern='^history$'))
    application.add_handler(CallbackQueryHandler(ipa_link_callback, pattern='^ipa_link$'))
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout$'))

    # Admin callbacks
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_users_callback, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_keys_callback, pattern='^admin_keys$'))
    application.add_handler(CallbackQueryHandler(view_stock_callback, pattern='^view_stock$'))
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern='^admin_stats$'))

    # --- Message Handlers ---
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Run the bot
    logging.info("Starting Modder IPA Bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
