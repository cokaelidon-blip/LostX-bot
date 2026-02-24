# bot.py
import logging
import config
from telegram.ext import (Application, CommandHandler, ConversationHandler, 
                          CallbackQueryHandler, MessageHandler, filters)

from database import init_database

# Import handlers from their respective files
from handlers.common import *
from handlers.user import *
from handlers.admin import *

# --- Logging Setup ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

def main() -> None:
    """Run the bot."""
    # Initialize the database first
    init_database()
    
    application = Application.builder().token(config.BOT_TOKEN).build()

    # --- Conversation Handlers ---
    login_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(login_start, pattern='^login$')],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel_login)],
        per_message=False
    )
    
    create_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_create_user_start, pattern='^admin_create_user$')],
        states={
            A_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_username)],
            A_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_password)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
        per_message=False
    )

    add_balance_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_balance_start, pattern='^admin_add_balance$')],
        states={
            A_GET_USERNAME_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_username_for_balance)],
            A_GET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_amount)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
        per_message=False
    )
    
    set_link_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_ipa_link_start, pattern='^admin_set_ipa_link$')],
        states={A_GET_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_ipa_link)]},
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
        per_message=False
    )

    add_keys_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_keys_start, pattern='^admin_add_keys$')],
        states={
            A_CHOOSE_DURATION: [CallbackQueryHandler(admin_choose_key_duration, pattern='^add_keys_for_')],
            A_GET_KEYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_keys)],
        },
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
        per_message=False
    )

    remove_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_remove_user_start, pattern='^admin_remove_user$')],
        states={A_GET_USERNAME_REMOVE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_confirm_remove_user)]},
        fallbacks=[CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')],
        per_message=False
    )

    # --- Add all handlers ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(login_conv)
    application.add_handler(create_user_conv)
    application.add_handler(add_balance_conv)
    application.add_handler(set_link_conv)
    application.add_handler(add_keys_conv)
    application.add_handler(remove_user_conv)

    # Common callbacks
    application.add_handler(CallbackQueryHandler(back_to_dashboard_callback, pattern='^back_to_dashboard$'))
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout$'))

    # User menu callbacks
    application.add_handler(CallbackQueryHandler(modder_ipa_menu_callback, pattern='^modder_ipa_menu$'))
    application.add_handler(CallbackQueryHandler(download_ipa_callback, pattern='^download_ipa$'))
    application.add_handler(CallbackQueryHandler(check_balance_callback, pattern='^check_balance$'))
    application.add_handler(CallbackQueryHandler(history_callback, pattern='^history$'))
    
    # Purchase flow
    application.add_handler(CallbackQueryHandler(buy_key_menu_callback, pattern='^buy_key_menu$'))
    application.add_handler(CallbackQueryHandler(buy_key_callback, pattern='^buy_'))

    # Admin panel navigation
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_users_callback, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_keys_callback, pattern='^admin_keys$'))
    application.add_handler(CallbackQueryHandler(admin_stats_callback, pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(view_stock_callback, pattern='^view_stock$'))

    # Fallback
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    print("Starting Modder IPA Bot...")
    application.run_polling()

if __name__ == "__main__":
    main()
