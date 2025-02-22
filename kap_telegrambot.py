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

def check_kap():
    try:
        logger.info("KAP duyuruları kontrol ediliyor...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # KAP'ın ana bildirim sayfasını çek
        response = requests.get("https://www.kap.org.tr/tr/bildirimler", headers=headers)
        logger.info(f"KAP yanıt kodu: {response.status_code}")
        logger.info(f"KAP yanıt içeriği uzunluğu: {len(response.text)}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tüm duyuru container'larını bul
        announcements = soup.find_all('div', class_='w-list-notification')
        logger.info(f"Bulunan duyuru sayısı: {len(announcements)}")
        
        for item in announcements[:5]:
            try:
                # Yeni CSS seçicilerle elementleri bul
                time_str = item.find('span', class_='np-time').text.strip()
                company = item.find('div', class_='np-company-name').text.strip()
                subject = item.find('div', class_='np-type').text.strip()
                
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
                logger.error(f"Duyuru HTML: {item}")
                continue
                
    except Exception as e:
        logger.error(f"KAP veri çekme hatası: {e}")

def bot_loop():
    while True:
        try:
            logger.info(f"Bot döngüsü başlıyor... ({datetime.now()})")
            check_kap()
            logger.info("Bot döngüsü tamamlandı, 5 dakika bekleniyor...")
            time.sleep(300)
        except Exception as e:
            logger.error(f"Bot döngüsü hatası: {e}")
            time.sleep(60)

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
