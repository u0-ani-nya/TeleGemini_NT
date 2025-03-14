import os
import asyncio
from dotenv import load_dotenv, set_key
from gemini_pro_bot.llm import model, img_model
from google.generativeai.types.generation_types import (
    StopCandidateException,
    BlockedPromptException,
)
from telegram import Update, User
from telegram.ext import ContextTypes
from telegram.error import NetworkError, BadRequest
from telegram.constants import ChatAction, ParseMode
from gemini_pro_bot.html_format import format_message
import PIL.Image as load_image
from io import BytesIO

# Load environment variables from .env file
load_dotenv()

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

def new_chat(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data["chat"] = model.start_chat()

async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.effective_message.reply_html(
        f"Hi {user.mention_html()}!\n\nStart sending messages with me to generate a response.\n\nSend /new to start a new chat session.",
    )

async def help_command(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = """
Basic commands:
/start - Start the bot
/help - Get help. Shows this message

Chat commands:
/new - Start a new chat session (model will forget previously generated messages)

Send a message to the bot to generate a response.
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
    init_msg = await update.effective_message.reply_text(
        text="Generating...", reply_to_message_id=update.message.message_id
    )
    await update.message.chat.send_action(ChatAction.TYPING)
    # Generate a response using the text-generation pipeline
    chat = context.chat_data.get("chat")  # Get the chat session for this chat
    response = None
    try:
        response = await chat.send_message_async(
            text, stream=True
        )  # Generate a response
    except StopCandidateException as sce:
        print("Prompt: ", text, " was stopped. User: ", update.message.from_user)
        print(sce)
        await init_msg.edit_text("The model unexpectedly stopped generating.")
        chat.rewind()  # Rewind the chat session to prevent the bot from getting stuck
        return
    except BlockedPromptException as bpe:
        print("Prompt: ", text, " was blocked. User: ", update.message.from_user)
        print(bpe)
        await init_msg.edit_text("Blocked due to safety concerns.")
        if response:
            # Resolve the response to prevent the chat session from getting stuck
            await response.resolve()
        return
    full_plain_message = ""
    # Stream the responses
    async for chunk in response:
        try:
            if chunk.text:
                full_plain_message += chunk.text
                message = format_message(full_plain_message)
                init_msg = await init_msg.edit_text(
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
        except StopCandidateException as sce:
            await init_msg.edit_text("The model unexpectedly stopped generating.")
            chat.rewind()  # Rewind the chat session to prevent the bot from getting stuck
            continue
        except BadRequest:
            await response.resolve()  # Resolve the response to prevent the chat session from getting stuck
            continue
        except NetworkError:
            raise NetworkError(
                "Looks like you're network is down. Please try again later."
            )
        except IndexError:
            await init_msg.reply_text(
                "Some index error occurred. This response is not supported."
            )
            await response.resolve()
            continue
        except Exception as e:
            print(e)
            if chunk.text:
                full_plain_message = chunk.text
                message = format_message(full_plain_message)
                init_msg = await update.message.reply_text(
                    text=message,
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=init_msg.message_id,
                    disable_web_page_preview=True,
                )
        # Sleep for a bit to prevent the bot from getting rate-limited
        await asyncio.sleep(0.1)

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming images with captions and generate a response."""
    # Check if the image is from a group chat and if the bot is mentioned or replied to
    if update.message.chat.type in ['group', 'supergroup']:
        if not (f'@{context.bot.username}' in update.message.caption or 
                (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id)):
            return

    init_msg = await update.effective_message.reply_text(
        text="Generating...", reply_to_message_id=update.message.message_id
    )
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
    prompt = None
    if update.message.caption:
        prompt = update.message.caption
    else:
        prompt = "Analyse this image and generate response"
    response = await img_model.generate_content_async([prompt, a_img], stream=True)
    full_plain_message = ""
    async for chunk in response:
        try:
            if chunk.text:
                full_plain_message += chunk.text
                message = format_message(full_plain_message)
                init_msg = await init_msg.edit_text(
                    text=message,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                )
        except StopCandidateException:
            await init_msg.edit_text("The model unexpectedly stopped generating.")
        except BadRequest:
            await response.resolve()
            continue
        except NetworkError:
            raise NetworkError(
                "Looks like you're network is down. Please try again later."
            )
        except IndexError:
            await init_msg.reply_text(
                "Some index error occurred. This response is not supported."
            )
            await response.resolve()
            continue
        except Exception as e:
            print(e)
            if chunk.text:
                full_plain_message = chunk.text
                message = format_message(full_plain_message)
                init_msg = await update.message.reply_text(
                    text=message,
                    parse_mode=ParseMode.HTML,
                    reply_to_message_id=init_msg.message_id,
                    disable_web_page_preview=True,
                )
        await asyncio.sleep(0.1)
