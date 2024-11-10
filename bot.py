import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import FloodWait
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import re
from typing import Dict, List
from motor.motor_asyncio import AsyncIOMotorClient
import time
from aiohttp import web
import json
import cloudscraper
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Config:
    # Bot Configuration
    API_ID = "10261086"
    API_HASH = "9195dc0591fbdb22b5711bcd1f437dab" 
    BOT_TOKEN = "5890914076:AAGifAR3sQ1Ayfv_kdPHyWfY16oZgAfA8BM"
    
    # Channel Configuration
    CHANNEL_ID = -1001919732447  # Your channel ID
    BACKUP_CHANNEL_ID = -1001919732447  # Backup channel ID
    
    # Site Configuration
    SITE_URL = "https://www.1tamilmv.wf"
    SCRAPE_INTERVAL = 300  # 5 minutes
    
    # Categories to scrape
    CATEGORIES = [
        "/forum/tamil-new-movies-hdrips-bdrips-dvdrips-hdtv.6/",
        "/forum/tamil-new-movies-webrips-web-dl-web-hd.50/",
        "/forum/tamil-new-movies-hdrips-bdrips-dvdrips-hdtv.6/"
    ]
    
    # MongoDB Configuration
    DB_URL = "mongodb+srv://KingSrilanga:KingSrilanga10@cluster0.w6gdp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    
    # Web Configuration
    WEB_PORT = 8080
    WEB_HOST = '0.0.0.0'
    
    # Custom Messages
    MOVIE_POST_TEMPLATE = """
🎬 **{title}**

📥 Quality: {quality}
🎭 Genre: {genre}
📅 Release: {year}
⭐️ Rating: {rating}
💾 Size: {size}

🎯 Screenshots:
{screenshots}

📥 Download Links:

🧲 Magnet Link:
`{magnet_link}`

💻 Torrent Link:
{torrent_link}

#Tamil #Movie #{tags}
    """

class Database:
    def __init__(self):
        self.client = AsyncIOMotorClient(Config.DB_URL)
        self.db = self.client['tamilmv_bot']
        self.posted = self.db['posted_movies']
        self.failed = self.db['failed_posts']
    
    async def is_posted(self, movie_id: str) -> bool:
        doc = await self.posted.find_one({'movie_id': movie_id})
        return bool(doc)
    
    async def mark_posted(self, movie_data: dict):
        await self.posted.update_one(
            {'movie_id': movie_data['movie_id']},
            {'$set': {
                **movie_data,
                'posted_at': datetime.now(),
                'status': 'success'
            }},
            upsert=True
        )
    
    async def mark_failed(self, movie_data: dict, error: str):
        await self.failed.insert_one({
            **movie_data,
            'error': str(error),
            'failed_at': datetime.now()
        })
    
    async def get_stats(self):
        total_posted = await self.posted.count_documents({})
        total_failed = await self.failed.count_documents({})
        recent_posts = await self.posted.find().sort('posted_at', -1).limit(5).to_list(length=5)
        
        return {
            'total_posted': total_posted,
            'total_failed': total_failed,
            'recent_posts': recent_posts
        }

class MovieScraper:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    
    def _get_soup(self, url: str) -> BeautifulSoup:
        response = self.scraper.get(url, headers=self.headers)
        return BeautifulSoup(response.text, 'lxml')
    
    async def get_movie_details(self, movie_url: str) -> Dict:
        try:
            # Use cloudscraper to bypass cloudflare
            soup = self._get_soup(movie_url)
            
            # Extract basic info
            title = self._extract_title(soup)
            quality = self._extract_quality(soup)
            size = self._extract_size(soup)
            
            # Extract download links
            magnet_link = self._extract_magnet_link(soup)
            torrent_link = self._extract_torrent_link(soup)
            
            # Extract screenshots
            screenshots = self._extract_screenshots(soup)
            
            if not (magnet_link or torrent_link):
                return None
            
            return {
                'movie_id': self._generate_movie_id(title),
                'title': title,
                'quality': quality,
                'size': size,
                'magnet_link': magnet_link,
                'torrent_link': torrent_link,
                'screenshots': screenshots,
                'genre': self._extract_genre(soup),
                'year': self._extract_year(soup),
                'rating': self._extract_rating(soup),
                'tags': self._generate_tags(title),
                'scraped_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error getting movie details from {movie_url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_elem = soup.find('h1', class_='p-title-value')
        if title_elem:
            # Clean up the title
            title = title_elem.text.strip()
            # Remove quality tags, year, etc
            title = re.sub(r'\[(.*?)\]|\((.*?)\)', '', title)
            return title.strip()
        return "Unknown Title"
    
    def _extract_magnet_link(self, soup: BeautifulSoup) -> str:
        magnet_links = soup.find_all('a', href=re.compile(r'^magnet:'))
        return magnet_links[0]['href'] if magnet_links else None
    
    def _extract_torrent_link(self, soup: BeautifulSoup) -> str:
        torrent_links = soup.find_all('a', href=re.compile(r'\.torrent$'))
        if torrent_links:
            return torrent_links[0]['href']
        return None
    
    def _extract_screenshots(self, soup: BeautifulSoup) -> List[str]:
        screenshots = []
        img_tags = soup.find_all('img', class_='bbImage')
        for img in img_tags:
            if 'src' in img.attrs:
                screenshots.append(img['src'])
        return screenshots[:4]  # Limit to 4 screenshots
    
    def _extract_quality(self, soup: BeautifulSoup) -> str:
        quality_patterns = [
            r'720p|1080p|2160p|HDRip|WebRip|WEB-DL|BluRay|WEB-HD',
            r'HDCAMRip|PreDVDRip|DTHRip|HDTVRip'
        ]
        
        for pattern in quality_patterns:
            match = re.search(pattern, soup.text, re.IGNORECASE)
            if match:
                return match.group()
        return "Unknown Quality"
    
    def _extract_size(self, soup: BeautifulSoup) -> str:
        size_pattern = r'\d+(?:\.\d+)?\s*(?:GB|MB)'
        match = re.search(size_pattern, soup.text)
        return match.group() if match else "Unknown Size"
    
    def _extract_genre(self, soup: BeautifulSoup) -> str:
        genre_patterns = ['Action', 'Drama', 'Comedy', 'Thriller', 'Romance', 'Horror']
        found_genres = []
        
        for genre in genre_patterns:
            if re.search(genre, soup.text, re.IGNORECASE):
                found_genres.append(genre)
        
        return ', '.join(found_genres) if found_genres else "Unknown Genre"
    
    def _extract_year(self, soup: BeautifulSoup) -> str:
        year_pattern = r'\b(19|20)\d{2}\b'
        match = re.search(year_pattern, soup.text)
        return match.group() if match else "Unknown Year"
    
    def _extract_rating(self, soup: BeautifulSoup) -> str:
        rating_pattern = r'\b\d(?:\.\d)?\s*\/\s*10\b'
        match = re.search(rating_pattern, soup.text)
        return match.group() if match else "N/A"
    
    def _generate_movie_id(self, title: str) -> str:
        return re.sub(r'[^a-zA-Z0-9]', '', title.lower())
    
    def _generate_tags(self, title: str) -> List[str]:
        words = re.findall(r'\w+', title)
        return [word.lower() for word in words if len(word) > 3]
    
    async def get_movie_links(self, category_url: str) -> List[str]:
        try:
            full_url = Config.SITE_URL + category_url
            soup = self._get_soup(full_url)
            
            links = []
            threads = soup.find_all('div', class_='structItem-title')
            
            for thread in threads:
                link = thread.find('a')
                if link and not 'prefix' in link.get('class', []):
                    thread_url = link['href']
                    if not thread_url.startswith('http'):
                        thread_url = Config.SITE_URL + thread_url
                    links.append(thread_url)
            
            return links
            
        except Exception as e:
            logger.error(f"Error getting movie links from {category_url}: {e}")
            return []

class AutoChannelBot:
    def __init__(self):
        self.app = Client(
            "TamilMVBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        self.db = Database()
        self.scraper = MovieScraper()
        self.web_server = WebServer(self)
    
    async def post_to_channel(self, movie_data: Dict):
        try:
            # Format screenshots for message
            screenshots_text = "\n".join(movie_data.get('screenshots', []))
            
            # Create message text using template
            message_text = Config.MOVIE_POST_TEMPLATE.format(
                **movie_data,
                screenshots=screenshots_text
            )
            
            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🧲 Download Magnet", url=movie_data['magnet_link'])
                ]
            ]
            
            if movie_data.get('torrent_link'):
                keyboard.append([
                    InlineKeyboardButton("💻 Download Torrent", url=movie_data['torrent_link'])
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Post to channel
            await self.app.send_message(
                chat_id=Config.CHANNEL_ID,
                text=message_text,
                reply_markup=reply_markup,
                disable_web_page_preview=False
            )
            
            # Mark as posted
            await self.db.mark_posted(movie_data)
            logger.info(f"Successfully posted: {movie_data['title']}")
            
        except FloodWait as e:
            logger.warning(f"FloodWait: Sleeping for {e.value} seconds")
            await asyncio.sleep(e.value)
            return await self.post_to_channel(movie_data)
            
        except Exception as e:
            logger.error(f"Error posting movie: {e}")
            await self.db.mark_failed(movie_data, str(e))
            
            # Try posting to backup channel
            try:
                await self.app.send_message(
                    chat_id=Config.BACKUP_CHANNEL_ID,
                    text=f"❌ Failed to post to main channel:\n\n{message_text}"
                )
            except Exception as backup_error:
                logger.error(f"Error posting to backup channel: {backup_error}")
    
    async def scrape_and_post(self):
        try:
            for category in Config.CATEGORIES:
                movie_links = await self.scraper.get_movie_links(category)
                
                for movie_url in movie_links:
                    try:
                        movie_data = await self.scraper.get_movie_details(movie_url)
                        
                        if movie_data and not await self.db.is_posted(movie_data['movie_id']):
                            await self.post_to_channel(movie_data)
                            await asyncio.sleep(5)  # Avoid flooding
                            
                    except Exception as e:
                        logger.error(f"Error processing movie URL {movie_url}: {e}")
                        continue
                
                await asyncio.sleep(10)  # Delay between categories
                
        except Exception as e:
            logger.error(f"Error in scrape_and_post: {e}")
    
    async def start_polling(self):
        while True:
            try:
                await self.scrape_and_post()
                await asyncio.sleep(Config.SCRAPE_INTERVAL)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def start(self):
        """Start both the bot and web server"""
        await self.app.start()
        await self.web_server.start()
        logger.info("Bot and web server started successfully!")
        
        # Start polling in background
        asyncio.create_task(self.start_polling())
    
    def run(self):
        logger.info("Starting TamilMV Auto Channel Bot...")
        
        # Run both bot and web server in the event loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        
        # Keep running
        loop.run_forever()


class WebServer:
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        self.app.router.add_get('/', self.handle_home)
        self.app.router.add_get('/api/stats', self.handle_stats)
        self.app.router.add_post('/api/force_scan', self.handle_force_scan)
    
    async def handle_home(self, request):
        return web.Response(text="""
        <html>
            <head><title>Auto Channel Bot Dashboard</title></head>
            <body>
                <h1>Auto Channel Bot Dashboard</h1>
                <div id="stats">Loading stats...</div>
                <button onclick="forceScan()">Force Scan Now</button>
                <script>
                    async function loadStats() {
                        const response = await fetch('/api/stats');
                        const stats = await response.json();
                        document.getElementById('stats').innerHTML = `
                            <p>Total Posted: ${stats.total_posted}</p>
                            <p>Total Failed: ${stats.total_failed}</p>
                            <h3>Recent Posts:</h3>
                            <ul>${stats.recent_posts.map(post => 
                                `<li>${post.title} - ${new Date(post.posted_at.$date).toLocaleString()}</li>`
                            ).join('')}</ul>
                        `;
                    }
                    
                    async function forceScan() {
                        await fetch('/api/force_scan', {method: 'POST'});
                        alert('Scan initiated!');
                    }
                    
                    loadStats();
                    setInterval(loadStats, 30000);
                </script>
            </body>
        </html>
        """, content_type='text/html')
    
    async def handle_stats(self, request):
        stats = await self.bot.db.get_stats()
        return web.json_response(stats, dumps=lambda x: json.dumps(x, default=str))
    
    async def handle_force_scan(self, request):
        asyncio.create_task(self.bot.scrape_and_post())
        return web.json_response({'status': 'scan_initiated'})
    
    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, Config.WEB_HOST, Config.WEB_PORT)
        await site.start()
        logger.info(f"Web server started at http://{Config.WEB_HOST}:{Config.WEB_PORT}")

class AutoChannelBot:
    def __init__(self):
        self.app = Client(
            "AutoChannelBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        self.db = Database()
        self.scraper = MovieScraper()
        self.web_server = WebServer(self)
    
    # ... [Previous AutoChannelBot methods remain the same] ...
    
    async def start(self):
        """Start both the bot and web server"""
        await self.app.start()
        await self.web_server.start()
        logger.info("Bot and web server started successfully!")
        
        # Start polling in background
        asyncio.create_task(self.start_polling())
    
    def run(self):
        logger.info("Starting Auto Channel Bot with Web Support...")
        
        # Run both bot and web server in the event loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        
        # Keep running
        loop.run_forever()

# Main execution
if __name__ == "__main__":
    try:
        bot = AutoChannelBot()
        bot.run()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
