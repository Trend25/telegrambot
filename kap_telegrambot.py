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
import feedparser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

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

def extract_company_name(title):
    try:
        # Başlıktan şirket adını çıkar
        parts = title.split(' - ')
        if len(parts) > 1:
            return parts[0].strip()
    except:
        pass
    return None

def check_kap():
    try:
        logger.info("KAP duyuruları kontrol ediliyor...")
        
        # KAP RSS feed'ini kullan
        feed = feedparser.parse('https://www.kap.org.tr/tr/rss/ek')
        logger.info(f"RSS feed durumu: {feed.status if hasattr(feed, 'status') else 'Bilinmiyor'}")
        logger.info(f"Bulunan duyuru sayısı: {len(feed.entries)}")
        
        for entry in feed.entries[:10]:  # Son 10 duyuruyu kontrol et
            try:
                time_str = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M')
                company = extract_company_name(entry.title)
                subject = entry.title
                
                if not company:
                    logger.warning(f"Şirket adı çıkarılamadı: {entry.title}")
                    continue
                
                logger.info(f"Duyuru ayrıştırıldı: {company} - {subject}")
                
                announcement_id = f"{company}-{subject}-{time_str}"
                
                if announcement_id not in seen_announcements:
                    stock_price = get_stock_price(company)
                    
                    message = f"""
                    <b>📢 Yeni KAP Duyurusu</b>
                    <b>📅 Tarih:</b> {time_str}
                    <b>🏢 Şirket:</b> {company} ({stock_price})
                    <b>📝 Konu:</b> {subject}
                    <b>🔗 Link:</b> {entry.link}
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
        logger.exception("Detaylı hata:")

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
    
    bot_thread = threading.Thread(target=bot_loop)
    bot_thread.daemon = True
    bot_thread.start()
    logger.info("Bot thread'i başlatıldı")
    
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Web sunucusu başlatılıyor - Port: {port}")
    app.run(host='0.0.0.0', port=port)
