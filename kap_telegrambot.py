#!/usr/bin/env python
# coding: utf-8

# In[1]:


import requests
import json
import time
import yfinance as yf
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta

# 📌 Telegram Bot Bilgilerini Gir!
TELEGRAM_BOT_TOKEN = "8158333498:AAG15cr7KVKvaxk_vCLN1cxRHYdDOKD0jQg"  # Buraya kendi bot token'ını yaz
TELEGRAM_CHAT_ID = "6143078737"  # Buraya kendi Chat ID'ni yaz

# 📌 Daha önce gönderilen duyuruların takibi için JSON dosyası
SEEN_ANNOUNCEMENTS_FILE = "seen_announcements.json"

# 📌 Daha önce gönderilen duyuruları yükle
def load_seen_announcements():
    try:
        with open(SEEN_ANNOUNCEMENTS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# 📌 Yeni duyuruları JSON dosyasına kaydet
def save_seen_announcements(seen_announcements):
    with open(SEEN_ANNOUNCEMENTS_FILE, "w") as file:
        json.dump(seen_announcements, file)

# 📌 Telegram'a mesaj gönderme fonksiyonu
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    response = requests.post(url, json=payload)
    print("📨 Telegram Yanıtı: ", response.json())

# 📌 Yahoo Finance API ile hisse fiyatı çekme fonksiyonu
def get_stock_price(company_name):
    try:
        ticker = company_name + ".IS"
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")["Close"].iloc[-1]
        return f"{price:.2f} TL"
    except:
        return "Fiyat alınamadı"

# 📌 Telegram için özel karakterleri kaçırma fonksiyonu
def escape_html(text):
    if not text:
        return "Bilinmiyor"
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text

# 📌 Daha önce gönderilen duyuruları yükle
seen_announcements = load_seen_announcements()

# 📌 Edge WebDriver'ı başlat
options = webdriver.EdgeOptions()
options.add_argument("start-maximized")  
driver = webdriver.Edge(options=options)

# 📌 KAP sayfasını aç
driver.get("https://www.kap.org.tr/tr/")

# 📌 Sayfanın tam yüklenmesini bekle
WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "notifications-row")))

# 📌 Yeni CSS Seçicilerle Bildirimleri Çek
notifications = driver.find_elements(By.CLASS_NAME, "notifications-row")

print("📢 KAP Üzerindeki Son 15 Dakikalık Duyurular:")
new_announcements = {}

# 📌 Şu anki saat ve son 15 dakikalık zaman aralığı
current_time = datetime.now()
time_threshold = current_time - timedelta(minutes=15)  # Sadece son 15 dakika içindeki duyurular

for i, notif in enumerate(notifications[:5]):  
    try:
        time_element = notif.find_element(By.CLASS_NAME, "_2").text.strip()
        company_element = escape_html(notif.find_element(By.CLASS_NAME, "_4").text)
        subject_element = escape_html(notif.find_element(By.CLASS_NAME, "_6").text)
        summary_element = escape_html(notif.find_element(By.CLASS_NAME, "_7").text) if notif.find_element(By.CLASS_NAME, "_7").text else "Özet Yok"

        # 📌 "Bugün" kelimesini gerçek tarihe çevirme
        if "Bugün" in time_element:
            time_element = time_element.replace("Bugün", current_time.strftime("%Y-%m-%d"))

        # 📌 Duyuru saatini `datetime` formatına çevirme
        announcement_time = datetime.strptime(time_element, "%Y-%m-%d %H:%M")

        # 📌 Eğer duyuru son 15 dakikadan önce paylaşılmışsa, atla
        if announcement_time < time_threshold:
            continue

        announcement_id = f"{company_element}-{subject_element}-{time_element}"

        # 📌 Eğer duyuru daha önce gönderilmişse, atla
        if announcement_id in seen_announcements:
            continue

        # 📌 Hisse senedi fiyatını çek
        stock_price = get_stock_price(company_element)

        # 📌 Telegram mesaj formatı
        message = f"""
        <b>📢 Yeni KAP Duyurusu 📢</b>\n
        <b>📅 Tarih:</b> {time_element}\n
        <b>🏢 Şirket:</b> {company_element} ({stock_price})\n
        <b>📝 Konu:</b> {subject_element}\n
        <b>📄 Özet:</b> {summary_element}
        """

        # 📩 Telegram'a mesaj gönder
        send_telegram_message(message)

        # 📌 Yeni duyuruyu listeye ekle
        new_announcements[announcement_id] = True

    except Exception as e:
        print(str(i+1) + ". ❌ Veri alınamadı! Hata: " + str(e))

# 📌 Yeni duyuruları JSON dosyasına kaydet
seen_announcements.update(new_announcements)
save_seen_announcements(seen_announcements)

# 📌 Tarayıcıyı kapat
driver.quit()

