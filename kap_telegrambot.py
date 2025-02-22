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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        session = requests.Session()
        
        # İlk olarak ana sayfaya git (cookie'leri almak için)
        logger.info("KAP ana sayfası ziyaret ediliyor...")
        main_page = session.get("https://www.kap.org.tr/tr", headers=headers, allow_redirects=True)
        logger.info(f"Ana sayfa yanıt kodu: {main_page.status_code}")
        
        # Sonra bildirimleri al
        logger.info("Bildirimler sayfası ziyaret ediliyor...")
        response = session.get("https://www.kap.org.tr/tr/bist-sirketler", headers=headers, allow_redirects=True)
        logger.info(f"Bildirimler sayfası yanıt kodu: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            logger.info(f"Sayfa içeriği uzunluğu: {len(response.text)}")
            logger.info(f"Sayfa başlığı: {soup.title.string if soup.title else 'Başlık bulunamadı'}")
            
            # Duyuruları bul
            announcements = soup.find_all('div', {'class': ['announcement-item', 'w-list-notification']})
            logger.info(f"Bulunan duyuru sayısı: {len(announcements)}")
            
            if len(announcements) == 0:
                # Alternatif seçicileri dene
                announcements = soup.find_all('tr', {'data-id': True})
                logger.info(f"Alternatif seçici ile bulunan duyuru sayısı: {len(announcements)}")
            
            for item in announcements[:5]:
                try:
                    # Farklı HTML yapıları için kontrol
                    time_str = (
                        item.find('div', class_='time').text.strip() if item.find('div', class_='time') else
                        item.find('td', class_='date').text.strip() if item.find('td', class_='date') else
                        datetime.now().strftime("%Y-%m-%d %H:%M")
                    )
                    
                    company = (
                        item.find('div', class_='company-name').text.strip() if item.find('div', class_='company-name') else
                        item.find('td', class_='company').text.strip() if item.find('td', class_='company') else
                        "Şirket bilgisi bulunamadı"
                    )
                    
                    subject = (
                        item.find('div', class_='announcement-title').text.strip() if item.find('div', class_='announcement-title') else
                        item.find('td', class_='disclosure').text.strip() if item.find('td', class_='disclosure') else
                        "Konu bulunamadı"
                    )
                    
                    logger.info(f"Duyuru ayrıştırıldı: {company} - {subject}")
                    
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
                    
                except Exception as e:
                    logger.error(f"Duyuru işleme hatası: {e}")
                    continue
        else:
            logger.error(f"KAP yanıt kodu başarısız: {response.status_code}")
            
    except Exception as e:
        logger.error(f"KAP veri çekme hatası: {e}")
        logger.exception("Detaylı hata:")

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
