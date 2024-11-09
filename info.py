import re
from os import environ
id_pattern = re.compile(r'^.\d+$')

# Bot information
SESSION = environ.get('SESSION', 'SinglePageMessageCompilerBot')
API_ID = int(environ.get('API_ID', '10261086'))
API_HASH = environ.get('API_HASH', '9195dc0591fbdb22b5711bcd1f437dab')
BOT_TOKEN = environ.get('BOT_TOKEN', '5890914076:AAGifAR3sQ1Ayfv_kdPHyWfY16oZgAfA8BM')
PORT = environ.get('PORT', '8080')

# Scraper Settings
BASE_URL = environ.get('BASE_URL', 'https://www.1tamilmv.wf')
CHECK_INTERVAL = int(environ.get('CHECK_INTERVAL', '300'))  # 5 minutes by default
CHANNEL_ID = int(environ.get('CHANNEL_ID', '-1001919732447'))

# MongoDB Settings
MONGO_URI = environ.get('MONGO_URI', 'mongodb+srv://KingSrilanga:KingSrilanga10@cluster0.w6gdp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')


ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '1426588906, 556766661').split()]
