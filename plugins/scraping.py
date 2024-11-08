import asyncio
import aiohttp
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from pyrogram import Client
from pymongo import MongoClient
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CHANNEL_ID = -1001919732447
BASE_URL = "https://www.1tamilmv.wf"  # Initial domain
MONGO_URI = 'mongodb+srv://KingSrilanga:KingSrilanga10@cluster0.w6gdp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
CHECK_INTERVAL = 300  # Check every 5 minutes

# Telegram Configuration
API_ID = "10261086"  # Replace with your API ID
API_HASH = "9195dc0591fbdb22b5711bcd1f437dab"  # Replace with your API Hash
BOT_TOKEN = "6874843676:AAErl1i5vtb0yEmdsYoGGvXsOtM9t5K8yn8"  # Replace with your bot token

class MovieScraper:
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client['telegram_bot']
        self.posted_links = self.db['posted_links']
        self.domains = self.db['domains']
        self.app = Client("movie_scraper", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
        self.current_domain = self.get_latest_domain() or BASE_URL
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_latest_domain(self):
        domain_doc = self.domains.find_one({}, sort=[('timestamp', -1)])
        return domain_doc['domain'] if domain_doc else None

    def update_domain(self, new_domain):
        self.domains.insert_one({
            'domain': new_domain,
            'timestamp': datetime.now()
        })
        self.current_domain = new_domain
        logger.info(f"Updated domain to: {new_domain}")

    async def check_domain_redirect(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.current_domain, headers=self.headers, allow_redirects=True) as response:
                    if response.status == 200:
                        final_url = str(response.url)
                        if final_url != self.current_domain:
                            self.update_domain(final_url.rstrip('/'))
                    else:
                        logger.error(f"Failed to access domain: {response.status}")
        except Exception as e:
            logger.error(f"Error checking domain redirect: {str(e)}")

    async def get_movie_links(self):
        try:
            await self.check_domain_redirect()
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.current_domain}", headers=self.headers) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find all movie posts
                    posts = soup.find_all('article', class_='post')
                    movies = []
                    
                    for post in posts:
                        title_elem = post.find('h2', class_='entry-title')
                        if title_elem and title_elem.a:
                            movies.append({
                                'title': title_elem.a.text.strip(),
                                'link': title_elem.a['href']
                            })
                    
                    return movies
        except Exception as e:
            logger.error(f"Error getting movie links: {str(e)}")
            return []

    async def get_magnet_links(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Find all magnet links
                    magnet_links = []
                    for a in soup.find_all('a', href=True):
                        if a['href'].startswith('magnet:'):
                            quality = "Unknown Quality"
                            # Try to find quality info from nearby text
                            quality_text = a.find_previous(text=re.compile(r'720p|1080p|2160p|4K|HDRip|WebRip|BRRip', re.I))
                            if quality_text:
                                quality = quality_text.strip()
                            magnet_links.append({
                                'quality': quality,
                                'link': a['href']
                            })
                    
                    return magnet_links
        except Exception as e:
            logger.error(f"Error getting magnet links: {str(e)}")
            return []

    def build_message(self, movie, magnet_links):
        try:
            message = (
                f"🎬 <b>New Movie Release</b>\n\n"
                f"📽 <b>Title:</b> {movie['title']}\n\n"
                f"🔗 <b>Download Page:</b> {movie['link']}\n\n"
            )

            if magnet_links:
                message += "<b>🧲 Magnet Links:</b>\n"
                for idx, magnet in enumerate(magnet_links, 1):
                    message += f"{idx}. {magnet['quality']}\n"
                    message += f"<code>{magnet['link']}</code>\n\n"
            
            message += (
                f"⏰ Posted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"📢 Join our channel for more updates!"
            )
            
            return message
        except Exception as e:
            logger.error(f"Error building message: {str(e)}")
            return None

    def link_exists(self, link):
        return self.posted_links.find_one({"link": link}) is not None

    def save_link(self, link):
        try:
            self.posted_links.insert_one({
                "link": link,
                "posted_at": datetime.now()
            })
        except Exception as e:
            logger.error(f"Error saving link to database: {str(e)}")

    async def process_movies(self):
        movies = await self.get_movie_links()
        
        for movie in movies:
            try:
                if not self.link_exists(movie['link']):
                    magnet_links = await self.get_magnet_links(movie['link'])
                    if magnet_links:
                        message = self.build_message(movie, magnet_links)
                        if message:
                            # Split message if it's too long
                            if len(message) > 4096:
                                chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
                                for chunk in chunks:
                                    await self.app.send_message(
                                        chat_id=CHANNEL_ID,
                                        text=chunk,
                                        disable_web_page_preview=True,
                                        parse_mode="html"
                                    )
                            else:
                                await self.app.send_message(
                                    chat_id=CHANNEL_ID,
                                    text=message,
                                    disable_web_page_preview=True,
                                    parse_mode="html"
                                )
                            self.save_link(movie['link'])
                            logger.info(f"Successfully posted: {movie['title']}")
                            await asyncio.sleep(2)  # Avoid flooding
            except Exception as e:
                logger.error(f"Error processing movie: {str(e)}")

    async def run(self):
        try:
            async with self.app:
                while True:
                    await self.process_movies()
                    await asyncio.sleep(CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Critical error in main loop: {str(e)}")

#if __name__ == "__main__":
#    scraper = MovieScraper()
#    asyncio.run(scraper.run())
