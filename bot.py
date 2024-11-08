from info import *
from aiohttp import web
from pyrogram import types
from pyrogram import Client
from plugins import web_server
from typing import Union, Optional, AsyncGenerator
import logging
import asyncio
from bs4 import BeautifulSoup
import aiohttp
from datetime import datetime
from pymongo import MongoClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MovieScraper:
    def __init__(self):
        self.mongo_client = MongoClient(MONGO_URI)
        self.db = self.mongo_client['telegram_bot']
        self.posted_links = self.db['posted_links']
        self.domains = self.db['domains']
        self.current_domain = self.get_latest_domain() or BASE_URL
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.running = True

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
        except Exception as e:
            logger.error(f"Error checking domain: {str(e)}")

    async def get_movie_links(self):
        try:
            await self.check_domain_redirect()
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.current_domain}", headers=self.headers) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
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
            logger.error(f"Error getting movies: {str(e)}")
            return []

    async def get_magnet_links(self, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    magnet_links = []
                    
                    for a in soup.find_all('a', href=True):
                        if a['href'].startswith('magnet:'):
                            quality = "Unknown Quality"
                            quality_text = a.find_previous(text=re.compile(r'720p|1080p|2160p|4K|HDRip|WebRip|BRRip', re.I))
                            if quality_text:
                                quality = quality_text.strip()
                            magnet_links.append({
                                'quality': quality,
                                'link': a['href']
                            })
                    
                    return magnet_links
        except Exception as e:
            logger.error(f"Error getting magnets: {str(e)}")
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
            logger.error(f"Error saving link: {str(e)}")

    async def process_movies(self, bot):
        while self.running:
            try:
                movies = await self.get_movie_links()
                for movie in movies:
                    if not self.link_exists(movie['link']):
                        magnet_links = await self.get_magnet_links(movie['link'])
                        if magnet_links:
                            message = self.build_message(movie, magnet_links)
                            if message:
                                if len(message) > 4096:
                                    chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
                                    for chunk in chunks:
                                        await bot.send_message(
                                            chat_id=CHANNEL_ID,
                                            text=chunk,
                                            disable_web_page_preview=True,
                                            parse_mode="html"
                                        )
                                else:
                                    await bot.send_message(
                                        chat_id=CHANNEL_ID,
                                        text=message,
                                        disable_web_page_preview=True,
                                        parse_mode="html"
                                    )
                                self.save_link(movie['link'])
                                logger.info(f"Posted: {movie['title']}")
                                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Error in process_movies: {str(e)}")
            await asyncio.sleep(CHECK_INTERVAL)

    async def start(self):
        self.running = True

    async def stop(self):
        self.running = False

class Bot(Client):
    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )
        self.scraper = MovieScraper()

    async def start(self):
        await super().start()
        await self.scraper.start()
        # Start scraping in background
        asyncio.create_task(self.scraper.process_movies(self))
        print("Scraping Started")
        
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()
        print("Bot Started")

    async def stop(self, *args):
        await self.scraper.stop()
        await super().stop()
        print("Bot Stopped")
    
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1

def main():
    app = Bot()
    app.run()

if __name__ == "__main__":
    main()
