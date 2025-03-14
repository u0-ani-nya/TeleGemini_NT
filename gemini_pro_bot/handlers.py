import os
import asyncio
from dotenv import load_dotenv, set_key
from google import genai
from telegram import Update, User
from telegram.ext import ContextTypes, CommandHandler
from telegram.constants import ChatAction, ParseMode
from gemini_pro_bot.html_format import format_message
from PIL import Image as load_image
from io import BytesIO
from telegram.error import BadRequest

# Load environment variables from .env file
load_dotenv()

# Initialize the GenAI Client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Load the system instruction from the environment variable
SYSTEM_INSTRUCTION = os.getenv("INSTRUCTION", "")

def get_admins() -> list:
    """Get the list of admin user IDs from the ADMINS environment variable."""
    admins = os.getenv("ADMINS", "")
    return [int(admin_id) for admin_id in admins.split(",") if admin_id.strip().isdigit()]

def save_admins(admins: list) -> None:
    """Save the list of admin user IDs to the ADMINS environment variable in the .env file."""
    admins_str = ",".join(map(str, admins))
    set_key(".env", "ADMINS", admins_str)
    # Reload the .env file to reflect changes
    load_dotenv(override=True)

def save_instruction(instruction: str) -> None:
    """Save the system instruction to the INSTRUCTION environment variable in the .env file."""
    set_key(".env", "INSTRUCTION", instruction)
    # Reload the .env file to reflect changes
    global SYSTEM_INSTRUCTION
    SYSTEM_INSTRUCTION = instruction
    load_dotenv(override=True)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /admin command to add or remove admin users."""
    user_id = update.effective_user.id
    admins = get_admins()
    bot_owner_id = admins[0] if admins else None

    if not context.args or len(context.args) < 1:
        await update.effective_message.reply_text("Usage: /admin <add|del|check>")
        return

    action = context.args[0]

    if action == "check":
        await update.effective_message.reply_text(f"Current Admins: {admins}\nYour User ID: {user_id}")
        return

    if user_id != bot_owner_id:
        await update.effective_message.reply_text("You do not have permission to manage admins.")
        return

    if action == "add":
        if not update.message.reply_to_message:
            await update.effective_message.reply_text("Please reply to the user's message to add them as an admin.")
            return

        target_user: User = update.message.reply_to_message.from_user
        target_user_id = target_user.id

        if target_user_id in admins:
            await update.effective_message.reply_text(f"User {target_user.mention_html()} is already an admin.", parse_mode=ParseMode.HTML)
        else:
            admins.append(target_user_id)
            save_admins(admins)
            await update.effective_message.reply_text(f"User {target_user.mention_html()} has been added as an admin.", parse_mode=ParseMode.HTML)

    elif action == "del":
        if not update.message.reply_to_message:
            await update.effective_message.reply_text("Please reply to the user's message to remove them from admins.")
            return

        target_user: User = update.message.reply_to_message.from_user
        target_user_id = target_user.id

        if target_user_id == bot_owner_id:
            await update.effective_message.reply_text("You cannot remove the bot owner from admins.")
        elif target_user_id not in admins:
            await update.effective_message.reply_text(f"User {target_user.mention_html()} is not an admin.", parse_mode=ParseMode.HTML)
        else:
            admins.remove(target_user_id)
            save_admins(admins)
            await update.effective_message.reply_text(f"User {target_user.mention_html()} has been removed from admins.", parse_mode=ParseMode.HTML)
    else:
        await update.effective_message.reply_text("Invalid action. Use 'add', 'del', or 'check'.")

async def instruction_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /instruction command to update the system instruction."""
    user_id = update.effective_user.id
    admins = get_admins()

    if user_id not in admins:
        await update.effective_message.reply_text("You do not have permission to update the system instruction.")
        return

    if not context.args:
        await update.effective_message.reply_text("Usage: /instruction <new_instruction>")
        return

    new_instruction = " ".join(context.args)
    save_instruction(new_instruction)
    await update.effective_message.reply_text(f"System instruction updated to: {new_instruction}")

def new_chat(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data["chat"] = []

async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.effective_message.reply_html(
        f"Hi {user.mention_html()}!\n\nStart sending messages with me to generate a response.\n\nSend /new to start a new chat session.",
    )

async def help_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
普通指令:
/start - 启动bot.
/help - 显示本帮助.
/new - 忘记聊天记录, 开始新对话.

管理员特权指令:
/instruction <new_instruction> - 更新提示词 (只有管理员可用).
/admin <add|del|check> - 设置/取消/检查管理员(仅bot所有者可用, admin的第0号).

发条消息 开始对话吧.
"""
    await update.effective_message.reply_text(help_text)

async def newchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a new chat session."""
    await update.effective_message.reply_text("New chat session started.")
    new_chat(context)

# Define the function that will handle incoming messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text messages from users.

    Checks if a chat session exists for the user, initializes a new session if not.
    Sends the user's message to the chat session to generate a response.
    Streams the response back to the user, handling any errors.
    """
    # Check if the message is from a group chat and if the bot is mentioned or replied to
    if update.message.chat.type in ['group', 'supergroup']:
        if not (f'@{context.bot.username}' in update.message.text or 
                (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)):
            return

    if context.chat_data.get("chat") is None:
        new_chat(context)
    text = update.message.text
    try:
        init_msg = await update.effective_message.reply_text(
            text="Generating...", reply_to_message_id=update.message.message_id
        )
    except BadRequest as e:
        print(e)
        init_msg = await update.effective_message.reply_text("Generating...")

    await update.message.chat.send_action(ChatAction.TYPING)

    # Generate a response using the text-generation pipeline
    try:
        response = await client.aio.models.generate_content(
            model='gemini-2.0-flash-exp',
            config=genai.types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
            contents=[text]
        )
        full_plain_message = response.text  # Use response.text for the message content
        await asyncio.sleep(0.1)  # Ensure the event loop is not blocked
        try:
            await init_msg.edit_text(
                text=full_plain_message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except BadRequest:
            await update.effective_message.reply_text(
                text=full_plain_message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
    except Exception as e:
        print(e)
        try:
            await init_msg.edit_text("An unexpected error occurred.")
        except BadRequest:
            await update.effective_message.reply_text("An unexpected error occurred.")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming images with captions and generate a response."""
    # Check if the image is from a group chat and if the bot is mentioned or replied to
    if update.message.chat.type in ['group', 'supergroup']:
        caption = update.message.caption if update.message.caption else ""
        if not (f'@{context.bot.username}' in caption or 
                (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)):
            return

    try:
        init_msg = await update.effective_message.reply_text(
            text="Generating...", reply_to_message_id=update.message.message_id
        )
    except BadRequest as e:
        print(e)
        init_msg = await update.effective_message.reply_text("Generating...")

    images = update.message.photo
    unique_images: dict = {}
    for img in images:
        file_id = img.file_id[:-7]
        if file_id not in unique_images:
            unique_images[file_id] = img
        elif img.file_size > unique_images[file_id].file_size:
            unique_images[file_id] = img
    file_list = list(unique_images.values())
    file = await file_list[0].get_file()
    a_img = load_image.open(BytesIO(await file.download_as_bytearray()))
    prompt = update.message.caption if update.message.caption else "Analyse this image and generate response"
    try:
        response = await client.aio.models.generate_content(
            model='gemini-2.0-flash-exp',
            config=genai.types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION),
            contents=[prompt, a_img]
        )
        full_plain_message = response.text  # Use response.text for the message content
        await asyncio.sleep(0.1)  # Ensure the event loop is not blocked
        try:
            await init_msg.edit_text(
                text=full_plain_message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except BadRequest:
            await update.effective_message.reply_text(
                text=full_plain_message,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
    except Exception as e:
        print(e)
        try:
            await init_msg.edit_text("An unexpected error occurred.")
        except BadRequest:
            await update.effective_message.reply_text("An unexpected error occurred.")
