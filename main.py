import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from urllib.parse import urlparse
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

# Load the environment variables from the .env file
load_dotenv()

# Access the TOKEN environment variable
TOKEN = os.getenv("TOKEN")

chrome_options = Options()
chrome_options.add_argument("--headless")

from threading import Thread, Lock

cache = {}
cache_lock = Lock()

from telegram import Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

# Define a few command handlers. These usually take the two arguments update and
# context.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_text(
        f"Hi <code>{user.first_name}</code>\n\n"
        + "<strong>I'm a bot 🤖 that helps you extract video URLs 🔗 from YouTube playlists.</strong>"
        + "\n\nTo use me, simply send me the <strong>/send</strong> command\nfollowed by the URL of a YouTube playlist, and I'll send you back\na list of the URLs of all the videos in the playlist.",
        parse_mode="HTML",
    )


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text("Help!")


def is_valid_url(url) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def send_command(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    # send message to user "Past YouTube video url here"
    update.message.reply_text("Past YouTube playlist url here")


def send_videos(update: Update, sorted_videos: dict) -> None:
    """Send the video URLs to the user"""
    for url in sorted_videos.values():
        update.message.reply_text(url)
        time.sleep(3)


def playlist_url_receiver(update: Update, context: CallbackContext) -> None:
    """Get the playlist url from user and send back the video urls"""
    # send message to user "Past YouTube video url here"
    playlist_url = update.message.text
    if is_valid_url(playlist_url):
        # Check the cache
        with cache_lock:
            if playlist_url in cache:
                sorted_videos = cache[playlist_url]
            else:
                # Open the URL in a headless Chrome browser
                driver = webdriver.Chrome(chrome_options=chrome_options)
                driver.get(playlist_url)
                driver.implicitly_wait(5)
                update.message.reply_text("Processing...")

                # Find all the "a" tags with the specified class
                links = driver.find_elements(
                    By.CSS_SELECTOR,
                    "a.yt-simple-endpoint.inline-block.style-scope.ytd-thumbnail",
                )

                # Create an empty dictionary to store the video URLs
                videos = {}

                # Iterate over the links to extract the video URLs and indexes
                for link in links:
                    # Get the "href" attribute of the link
                    href = link.get_attribute("href")
                    if href:
                        # Split the "href" string by the "&" character
                        parts = href.split("&")
                        # Get the video URL from the first part of the split string
                        url = parts[0]
                        # Get the index from the third part of the split string
                        index = parts[2].split("=")[1]
                        # Add the index and URL to the dictionary
                        videos[index] = url

                driver.close()
                # Sort the dictionary by index
                sorted_videos = dict(
                    sorted(videos.items(), key=lambda item: int(item[0]))
                )
                # Add the sorted videos to the cache
                cache[playlist_url] = sorted_videos

        # Send the video URLs to the user in a separate thread
        thread = Thread(target=send_videos, args=(update, sorted_videos))
        thread.start()
    else:
        update.message.reply_text("Please send a valid YouTube playlist url 🤷‍♂️")


def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("send", send_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    # on noncommand i.e message - echo the message on Telegram
    dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, playlist_url_receiver)
    )

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == "__main__":
    main()
