from flask import Flask
import threading
import os
import requests
import json
import time
import yfinance as yf
from datetime import datetime
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
        
        # KAP API endpoint'i
        url = "https://www.kap.org.tr/tr/api/disclosureRss"
        
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        logger.info(f"API yanıt kodu: {response.status_code}")
        
        if response.status_code == 200:
            try:
                announcements = response.json()
                logger.info(f"Bulunan duyuru sayısı: {len(announcements)}")
                
                for announcement in announcements[:10]:  # Son 10 duyuruyu işle
                    try:
                        company = announcement.get('companyTitle', 'Bilinmiyor')
                        subject = announcement.get('title', 'Bilinmiyor')
                        time_str = datetime.fromtimestamp(announcement.get('publishDate', 0)/1000).strftime('%Y-%m-%d %H:%M')
                        disclosure_url = f"https://www.kap.org.tr/tr/Bildirim/{announcement.get('disclosureId')}"
                        
                        announcement_id = f"{company}-{subject}-{time_str}"
                        
                        if announcement_id not in seen_announcements:
                            stock_price = get_stock_price(company)
                            
                            message = f"""
                            <b>📢 Yeni KAP Duyurusu</b>
                            <b>📅 Tarih:</b> {time_str}
                            <b>🏢 Şirket:</b> {company} ({stock_price})
                            <b>📝 Konu:</b> {subject}
                            <b>🔗 Link:</b> {disclosure_url}
                            """
                            
                            send_telegram_message(message)
                            seen_announcements[announcement_id] = True
                            logger.info(f"Yeni duyuru gönderildi: {company}")
                            
                    except Exception as e:
                        logger.error(f"Duyuru işleme hatası: {e}")
                        continue
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON ayrıştırma hatası: {e}")
        else:
            logger.error(f"API yanıt hatası: {response.status_code}")
            
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
