import requests
import json
import time
import yfinance as yf
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from flask import Flask
import threading
import os

app = Flask(__name__)

# Telegram Bot Bilgileri
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SEEN_ANNOUNCEMENTS_FILE = "seen_announcements.json"

[... önceki fonksiyonlar aynen kalacak ...]

def bot_thread():
    main()

@app.route('/')
def home():
    return 'KAP Bot çalışıyor!'

if __name__ == "__main__":
    # Bot'u ayrı bir thread'de başlat
    thread = threading.Thread(target=bot_thread)
    thread.daemon = True
    thread.start()
    
    # Flask uygulamasını başlat
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
