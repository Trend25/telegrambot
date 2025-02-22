from flask import Flask
import threading
import os
import requests
import json
import time
import yfinance as yf
from datetime import datetime
from bs4 import BeautifulSoup
import logging

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Bot konfigürasyonu
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
seen_announcements = {}

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        logger.info(f"Telegram mesajı gönderiliyor: {message[:100]}...")
        response = requests.post(url, json=payload)
        logger.info(f"Telegram yanıtı: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Telegram mesaj hatası: {e}")

def get_stock_price(company_name):
    try:
        logger.info(f"Hisse fiyatı alınıyor: {company_name}")
        ticker = company_name.strip().upper() + ".IS"
        stock = yf.Ticker(ticker)
        today_data = stock.history(period='1d')
        if not today_data.empty:
            price = today_data['Close'].iloc[-1]
            logger.info(f"Fiyat alındı: {price:.2f} TL")
            return f"{price:.2f} TL"
    except Exception as e:
        logger.error(f"Fiyat çekme hatası ({company_name}): {e}")
    return "Fiyat alınamadı"

def check_kap():
    try:
        logger.info("KAP duyuruları kontrol ediliyor...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get("https://www.kap.org.tr/tr/bildirim-sorgu", headers=headers)
        logger.info(f"KAP yanıt kodu: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        announcements = soup.select('.notification-row')
        logger.info(f"Bulunan duyuru sayısı: {len(announcements)}")
        
        for item in announcements[:5]:
            try:
                time_str = item.select_one('.time').text.strip()
                company = item.select_one('.company-title').text.strip()
                subject = item.select_one('.notification-subject').text.strip()
                logger.info(f"Duyuru bulundu: {company} - {subject}")
                
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
                    logger.info(f"Yeni duyuru gönderildi: {company}")
                else:
                    logger.info(f"Bu duyuru daha önce gönderilmiş: {company}")
                    
            except Exception as e:
                logger.error(f"Duyuru işleme hatası: {e}")
                continue
                
    except Exception as e:
        logger.error(f"KAP veri çekme hatası: {e}")

def bot_loop():
    while True:
        try:
            logger.info(f"Bot döngüsü başlıyor... ({datetime.now()})")
            check_kap()
            logger.info("Bot döngüsü tamamlandı, 5 dakika bekleniyor...")
            time.sleep(300)  # 5 dakika bekle
        except Exception as e:
            logger.error(f"Bot döngüsü hatası: {e}")
            time.sleep(60)  # Hata durumunda 1 dakika bekle

@app.route('/')
def home():
    return 'KAP Bot Aktif! Son kontrol: ' + str(datetime.now())

if __name__ == "__main__":
    logger.info("Bot başlatılıyor...")
    
    # Bot'u ayrı bir thread'de başlat
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    logger.info("Bot thread'i başlatıldı")
    
    # Web sunucusunu başlat
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Web sunucusu başlatılıyor - Port: {port}")
    app.run(host='0.0.0.0', port=port)
