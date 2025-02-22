import requests
import json
import time
import yfinance as yf
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Telegram Bot Bilgileri
TELEGRAM_BOT_TOKEN = "8158333498:AAG15cr7KVKvaxk_vCLN1cxRHYdDOKD0jQg"
TELEGRAM_CHAT_ID = "6143078737"
SEEN_ANNOUNCEMENTS_FILE = "seen_announcements.json"

def load_seen_announcements():
    try:
        with open(SEEN_ANNOUNCEMENTS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_seen_announcements(seen_announcements):
    with open(SEEN_ANNOUNCEMENTS_FILE, "w") as file:
        json.dump(seen_announcements, file)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    response = requests.post(url, json=payload)
    return response.json()

def get_stock_price(company_name):
    try:
        ticker = company_name.strip().upper() + ".IS"
        stock = yf.Ticker(ticker)
        today_data = stock.history(period='1d')
        
        if not today_data.empty:
            price = today_data['Close'].iloc[-1]
            return f"{price:.2f} TL"
        else:
            last_data = stock.history(period='5d')
            if not last_data.empty:
                price = last_data['Close'].iloc[-1]
                return f"{price:.2f} TL"
            return "Fiyat alınamadı"
    except Exception as e:
        print(f"Fiyat çekme hatası ({company_name}): {str(e)}")
        return "Fiyat alınamadı"

def get_kap_announcements():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get("https://www.kap.org.tr/tr/bildirim-sorgu", headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        announcements = []
        for item in soup.select('.notification-row')[:10]:  # Son 10 bildirimi al
            try:
                time_str = item.select_one('.time').text.strip()
                company = item.select_one('.company-title').text.strip()
                subject = item.select_one('.notification-subject').text.strip()
                summary = item.select_one('.notification-summary').text.strip() if item.select_one('.notification-summary') else "Özet Yok"
                
                announcements.append({
                    'time': time_str,
                    'company': company,
                    'subject': subject,
                    'summary': summary
                })
            except Exception as e:
                print(f"Duyuru ayrıştırma hatası: {str(e)}")
                continue
                
        return announcements
    except Exception as e:
        print(f"KAP verisi çekme hatası: {str(e)}")
        return []

def main():
    print("Bot başlatılıyor...")
    seen_announcements = load_seen_announcements()
    
    while True:
        try:
            print(f"Duyurular kontrol ediliyor... ({datetime.now()})")
            announcements = get_kap_announcements()
            
            for announcement in announcements:
                try:
                    announcement_id = f"{announcement['company']}-{announcement['subject']}-{announcement['time']}"
                    
                    if announcement_id in seen_announcements:
                        continue
                        
                    stock_price = get_stock_price(announcement['company'])
                    
                    message = f"""
                    <b>📢 Yeni KAP Duyurusu 📢</b>\n
                    <b>📅 Tarih:</b> {announcement['time']}\n
                    <b>🏢 Şirket:</b> {announcement['company']} ({stock_price})\n
                    <b>📝 Konu:</b> {announcement['subject']}\n
                    <b>📄 Özet:</b> {announcement['summary']}
                    """
                    
                    send_telegram_message(message)
                    seen_announcements[announcement_id] = True
                    print(f"Yeni duyuru gönderildi: {announcement['company']}")
                    
                except Exception as e:
                    print(f"İşlem hatası: {str(e)}")
                    continue
            
            save_seen_announcements(seen_announcements)
            time.sleep(300)  # 5 dakika bekle
            
        except Exception as e:
            print(f"Ana döngü hatası: {str(e)}")
            time.sleep(60)  # Hata durumunda 1 dakika bekle

if __name__ == "__main__":
    main()
