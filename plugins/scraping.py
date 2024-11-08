import feedparser
import requests
import asyncio
from pyrogram import Client, enums
from bs4 import BeautifulSoup
from pymongo import MongoClient


CHANNEL_ID = -1001919732447  # Replace with your Telegram Channel ID
RSS_FEED_URL = 'https://www.1tamilmv.wf/'  # Replace with the actual RSS feed URL if it's different
MONGO_URI = 'mongodb+srv://KingSrilanga:KingSrilanga10@cluster0.w6gdp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'  # Replace with your MongoDB URI


# Connect to MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client['telegram_bot']  # Database name
posted_links_collection = db['posted_links']  # Collection name

def fetch_feed():
    feed = feedparser.parse(RSS_FEED_URL)
    return feed.entries

def build_message(entry):
    title = entry.title
    link = entry.link
    magnet_link = extract_magnet_link(entry.link)

    message = (
        f"<b>🎬 New Movie:</b> {title}\n\n"
        f"🔗 <a href='{link}'>Watch/Download</a>\n"
        f"🧲 <a href='{magnet_link}'>Magnet Link</a>\n\n"
        "Follow our channel for more updates!"
    )
    return message

def extract_magnet_link(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    magnet_link = soup.find('a', href=True, text='Magnet')
    magnet_link = magnet_link['href'] if magnet_link else "No magnet link found"
    return magnet_link

def link_already_posted(link):
    # Check if the link is in the MongoDB collection
    return posted_links_collection.find_one({"link": link}) is not None

def mark_link_as_posted(link):
    # Add the link to the MongoDB collection
    posted_links_collection.insert_one({"link": link})

async def check_and_post_updates():
    while True:
        feed = fetch_feed()
        if feed:
            latest_entry = feed[0]
            if not link_already_posted(latest_entry.link):
                message = build_message(latest_entry)
                await app.send_message(CHANNEL_ID, text=message, parse_mode=enums.ParseMode.HTML)
                mark_link_as_posted(latest_entry.link)
        await asyncio.sleep(600)
