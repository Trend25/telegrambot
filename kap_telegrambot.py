from flask import Flask
import threading
import os
import requests
import json
import time
import yfinance as yf
from datetime import datetime
from bs4 import BeautifulSoup

app = Flask(__name__)

# Bot konfigürasyonu
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
seen_announcements = {}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload)
        print(f"Telegram yanıtı: {response.status_code}")
    except Exception as e:
        print(f"Telegram mesaj hatası: {e}")

def get_stock_price(company_name):
    try:
        ticker = company_name.strip().upper() + ".IS"
        stock = yf.Ticker(ticker)
        today_data = stock.history(period='1d')
        if not today_data.empty:
            price = today_data['Close'].iloc[-1]
            return f"{price:.2f} TL"
    except Exception as e:
        print(f"Fiyat çekme hatası ({company_name}): {e}")
    return "Fiyat alınamadı"

def check_kap():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get("https://www.kap.org.tr/tr/bildirim-sorgu", headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for item in soup.select('.notification-row')[:5]:
            try:
                time_str = item.select_one('.time').text.strip()
                company = item.select_one('.company-title').text.strip()
                subject = item.select_one('.notification-subject').text.strip()
                
                announcement_id = f"{company}-{subject}-{time_str}"
                
                if announcement_id not in seen_announcements:
                    stock_price = get_stock_price(company)
                    
                    message = f"""
                    <b>📢 Yeni KAP Duyurusu</b>
                    <b>📅 Tarih:</b> {time_str}
                    <b>🏢 Şirket:</b> {company} ({stock_price})
                    <b>📝 Konu:</b> {subject}
                    """
                    
                    send_telegram_message(message)
                    seen_announcements[announcement_id] = True
                    print(f"Yeni duyuru gönderildi: {company}")
                    
            except Exception as e:
                print(f"Duyuru işleme hatası: {e}")
                continue
                
    except Exception as e:
        print(f"KAP veri çekme hatası: {e}")

def bot_loop():
    while True:
        print(f"Duyurular kontrol ediliyor... ({datetime.now()})")
        check_kap()
        time.sleep(300)  # 5 dakika bekle

@app.route('/')
def home():
    return 'KAP Bot Aktif!'

if __name__ == "__main__":
    # Bot'u ayrı bir thread'de başlat
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Web sunucusunu başlat
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
