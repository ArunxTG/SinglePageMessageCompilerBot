import re
from os import environ
id_pattern = re.compile(r'^.\d+$')

# Bot information
SESSION = environ.get('SESSION', 'SinglePageMessageCompilerBot')
API_ID = int(environ.get('API_ID', '10261086'))
API_HASH = environ.get('API_HASH', '9195dc0591fbdb22b5711bcd1f437dab')
BOT_TOKEN = environ.get('BOT_TOKEN', '6874843676:AAErl1i5vtb0yEmdsYoGGvXsOtM9t5K8yn8')
PORT = environ.get('PORT', '8080')

ADMINS = [int(admin) if id_pattern.search(admin) else admin for admin in environ.get('ADMINS', '1426588906, 556766661').split()]
