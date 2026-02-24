# bot.py
import logging
import os
import sys

# --- START DIAGNOSTIC BLOCK ---
# This block will run first to get information about the container's environment.
print("--- STARTING DIAGNOSTIC CHECK ---", file=sys.stderr)
try:
    print(f"Current User ID (UID): {os.getuid()}", file=sys.stderr)
    print(f"Current Group ID (GID): {os.getgid()}", file=sys.stderr)
    print(f"Current Working Directory: {os.getcwd()}", file=sys.stderr)
    print(f"DATABASE_URL is set to: {os.getenv('DATABASE_URL', 'Not Set, using default')}", file=sys.stderr)
    
    print("\n--- Checking /app directory permissions ---", file=sys.stderr)
    os.system('ls -ld /app >&2')

    print("\n--- Checking /tmp directory permissions ---", file=sys.stderr)
    os.system('ls -ld /tmp >&2')

except Exception as e:
    print(f"An error occurred during diagnostics: {e}", file=sys.stderr)
print("\n--- END OF DIAGNOSTIC CHECK ---\n", file=sys.stderr)
# --- END DIAGNOSTIC BLOCK ---


from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          ConversationHandler, MessageHandler, filters)

import config
from database import init_database
from handlers.common import (start, login_start, login_username, login_password,
                           cancel_login, logout_callback, unknown_command,
                           USERNAME, PASSWORD)
from handlers.user import *
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

    # Define a single cancel handler for all admin conversations
    cancel_handler = CallbackQueryHandler(cancel_admin_action, pattern='^cancel_admin_action$')

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
            CREATE_USER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_user_username)],
            CREATE_USER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_user_password)],
        },
        fallbacks=[cancel_handler],
        conversation_timeout=60
    )

    add_balance_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_balance_callback, pattern='^admin_add_balance$')],
        states={
            ADD_BALANCE_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_username)],
            ADD_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_balance_amount)],
        },
        fallbacks=[cancel_handler],
        conversation_timeout=60
    )

    set_link_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_link_start, pattern='^admin_set_ipa_link$')],
        states={SET_IPA_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_receive_new_link)]},
        fallbacks=[cancel_handler],
        conversation_timeout=60
    )

    add_keys_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_keys_start, pattern='^admin_add_keys$')],
        states={
            SELECT_KEY_DURATION: [CallbackQueryHandler(select_key_duration, pattern='^add_keys_for_')],
            RECEIVE_KEYS_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_keys_list)],
        },
        fallbacks=[cancel_handler],
        conversation_timeout=120 
    )

    remove_user_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_remove_user_start, pattern='^admin_remove_user$')],
        states={
            REMOVE_USER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_user_username)],
        },
        fallbacks=[cancel_handler],
        conversation_timeout=60
    )

    # --- Add All Handlers ---
    application.add_handler(CommandHandler("start", start))
    
    # Conversations
    application.add_handler(login_conv)
    application.add_handler(create_user_conv)
    application.add_handler(add_balance_conv)
    application.add_handler(set_link_conv)
    application.add_handler(add_keys_conv)
    application.add_handler(remove_user_conv)
    
    # User Callbacks
    application.add_handler(CallbackQueryHandler(logout_callback, pattern='^logout$'))
    application.add_handler(CallbackQueryHandler(dashboard_callback, pattern='^back_to_dashboard$'))
    application.add_handler(CallbackQueryHandler(modder_ipa_menu_callback, pattern='^modder_ipa_menu$'))
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
