import html
import logging
import time
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from pymongo import MongoClient
from telegram.utils.helpers import mention_markdown
from config import LOGGER, MONGO_URI, DB_NAME, TELEGRAM_TOKEN, OWNER_ID, SUDO_ID, BOT_NAME, SUPPORT_ID, API_ID, API_HASH

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB initialization
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_collection = db['users']
chats_collection = db['chats']  # Added collection for chats

# List of sudo users
sudo_users = SUDO_ID.copy()  # Copy initial SUDO_ID list
sudo_users.append(OWNER_ID)  # Add owner to sudo users list initially

# Start time
StartTime = time.time()

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time

def check_edit(update: Update, context: CallbackContext):
    bot: Bot = context.bot

    # Check if the update is an edited message
    if update.edited_message:
        edited_message = update.edited_message
        
        # Get the chat ID and message ID
        chat_id = edited_message.chat_id
        message_id = edited_message.message_id
        
        # Get the user who edited the message
        user_id = edited_message.from_user.id
        
        # Create the mention for the user
        user_mention = f"<a href='tg://user?id={user_id}'>{html.escape(edited_message.from_user.first_name)}</a>"
        
        # Delete the message if the editor is not the owner or a sudo user
        if user_id not in sudo_users:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
            
            # Send a message notifying about the deletion
            bot.send_message(chat_id=chat_id, text=f"{user_mention} 𝗷𝘂𝘀𝘁 𝗲𝗱𝗶𝘁 𝗮 𝗺𝗲𝘀𝘀𝗮𝗴𝗲. 𝗜 𝗱𝗲𝗹𝗲𝘁𝗲𝗱 𝗵𝗶𝘀 𝗲𝗱𝗶𝘁𝗲𝗱 𝗺𝗲𝘀𝘀𝗮𝗴𝗲.", parse_mode='HTML')

# Command handler for /start
def start(update: Update, context: CallbackContext):
    uptime = get_readable_time(time.time() - StartTime)
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if update.effective_chat.type == "private":
        update.effective_message.reply_text(
            f"Hello {update.effective_user.first_name}, I'm {BOT_NAME}. Uptime: {uptime}.",   
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Help", callback_data="help")]
            ]),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        update.effective_message.reply_photo(
            "https://path_to_image",  # Add a proper image URL or path here
            caption=f"ɪ ᴀᴍ ᴀʟɪᴠᴇ ʙᴀʙʏ! ʀᴇᴀᴅʏ ᴛᴏ ᴍᴀɴᴀɢᴇ ᴇᴅɪᴛ ᴍᴇssᴀɢᴇs\n<b>ᴜᴘᴛɪᴍᴇ :</b> <code>{uptime}</code>",
            parse_mode=ParseMode.HTML
        )

# Function to list sudo users
def sudo_list(update: Update, context: CallbackContext):
    # Check if the user is the owner
    if update.effective_user.id != OWNER_ID:
        update.message.reply_text("You are not authorized to use this command.")
        return

    # Prepare the response message with SUDO_ID users
    text = "List of sudo users:\n"
    count = 1

    try:
        owner = context.bot.get_chat(OWNER_ID)
        owner_mention = mention_markdown(OWNER_ID, owner.first_name)
        text += f"{count} {owner_mention}\n"
    except Exception as e:
        update.message.reply_text(f"Failed to get owner details: {e}")

    for user_id in sudo_users:
        if user_id != OWNER_ID:
            try:
                user = context.bot.get_chat(user_id)
                user_mention = mention_markdown(user_id, user.first_name)
                count += 1                
                text += f"{count} {user_mention}\n"
            except Exception as e:
                update.message.reply_text(f"Failed to get user details for user_id {user_id}: {e}")

    if not text.strip():
        update.message.reply_text("No sudo users found.")
    else:
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# Function to add sudo users
def add_sudo(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    if user.id != OWNER_ID:
        update.message.reply_text("You do not have permission to use this command.")
        return
    
    if len(context.args) != 1:
        update.message.reply_text("Usage: /addsudo <username or user ID>")
        return
    
    sudo_user = context.args[0]
    
    try:
        sudo_user_obj = context.bot.get_chat_member(chat_id=chat_id, user_id=sudo_user)
        sudo_user_id = sudo_user_obj.user.id
    except Exception as e:
        update.message.reply_text(f"Failed to resolve user: {e}")
        return
    
    if sudo_user_id not in sudo_users:
        sudo_users.append(sudo_user_id)
        update.message.reply_text(f"Added {sudo_user_obj.user.username} as a sudo user.")
    else:
        update.message.reply_text(f"{sudo_user_obj.user.username} is already a sudo user.")

# Command to get bot stats
def send_stats(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if user.id != OWNER_ID:
        update.message.reply_text("You are not authorized to use this command.")
        return
    
    try:
        users_count = users_collection.count_documents({})
        chat_count = chats_collection.count_documents({})
        
        stats_msg = f"Total Users: {users_count}\nTotal Chats: {chat_count}\n"
        update.message.reply_text(stats_msg)
        
    except Exception as e:
        logger.error(f"Error in send_stats function: {e}")
        update.message.reply_text("Failed to fetch statistics.")

# Main function to start the bot
def main():
    # Create the Updater and pass it your bot's token
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.update.edited_message, check_edit))
    dispatcher.add_handler(CommandHandler("addsudo", add_sudo))
    dispatcher.add_handler(CommandHandler("sudolist", sudo_list))
    dispatcher.add_handler(CommandHandler("stats", send_stats))

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
