import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from gemini_pro_bot.handlers import (
    start,
    help_command,
    newchat_command,
    handle_message,
    handle_image,
    admin_command,  # Import the new command handler
)

# Load environment variables from .env file
load_dotenv()

# Create the Application and pass it your bot's token.
application = Application.builder().token(os.getenv("BOT_TOKEN")).build()

# on different commands - answer in Telegram
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("new", newchat_command))
application.add_handler(CommandHandler("admin", admin_command))  # Add the new command handler

# Any text message is sent to LLM to generate a response
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Any image is sent to LLM to generate a response
application.add_handler(MessageHandler(filters.PHOTO, handle_image))

# Run the bot until the user presses Ctrl-C
application.run_polling()
