import requests
from bs4 import BeautifulSoup
import urllib3
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import re 
import os # Ortam değişkenlerini okumak için eklendi
import json # JSON metnini sözlüğe dönüştürmek için eklendi

# --- 1. FIREBASE BAĞLANTISI (GÜNCELLENDİ) ---
try:
    # 1. Ortam değişkeninden JSON metnini al
    SERVICE_ACCOUNT_JSON_STR = os.environ.get('FIREBASE_SERVICE_ACCOUNT_KEY')
    
    if not SERVICE_ACCOUNT_JSON_STR:
        # Eğer Sır (Secret) ayarlanmamışsa, terminalde hata ver
        print(" 🚨 HATA: Ortam değişkeni 'FIREBASE_SERVICE_ACCOUNT_KEY' bulunamadı.")
        print(" Lütfen bu kodu yerel olarak çalıştırıyorsanız 'serviceAccountKey.json' dosyasını kontrol edin.")
        # Eğer GitHub Actions'daysa ve Sır yoksa, burada durur.
        exit() 

    # 2. JSON metnini Python sözlüğüne dönüştür
    cred_data = json.loads(SERVICE_ACCOUNT_JSON_STR)
    
    # 3. Sertifikayı doğrudan sözlükten yükle
    cred = credentials.Certificate(cred_data)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print(" Firebase bağlantısı (GitHub Secrets üzerinden) başarılı!")
    
except Exception as e:
    print(f" Firebase Bağlantı/JSON Hatası: {e}")
    print(" JSON formatının doğru olduğundan emin olun.")
    exit() 


# --- ORTAK AYARLAR ve DİĞER MODÜLLER (Aynı Kaldı) ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/53736"
}

# YARDIMCI VE DİĞER MODÜLLER BURADA DEVAM EDER...
# (firestore_guncelle, son_duyuruyu_cek, eczaneleri_cek, etkinlikleri_cek)
# ... (Önceki kodunuzdaki tüm fonksiyonları buraya yapıştırın) ...

# --- 3. MODÜL: ETKİNLİKLERİ ÇEK (Örnek olarak) ---
def etkinlikleri_cek():
    print(" 3/3: Etkinlikler Taranıyor...")
    # ... (kodun geri kalanı) ...
    pass 

def firestore_guncelle(koleksiyon_adi, veri_listesi):
    # ... (kodun geri kalanı) ...
    pass
def son_duyuruyu_cek():
    # ... (kodun geri kalanı) ...
    pass
def eczaneleri_cek():
    # ... (kodun geri kalanı) ...
    pass

# --- ANA BLOK ---
if __name__ == "__main__":
    print(" FIREBASE BOTU BAŞLATILIYOR...\n")
    t0 = time.time()
    
    # Buraya önceki tüm fonksiyonlarınızı kopyalayıp yapıştırın.
    # Ben sadece mantık için pass koydum, sizin çalışan tüm kodunuz burada olmalı.
    
    # NOT: Tüm önceki fonksiyonları (firestore_guncelle, son_duyuruyu_cek, eczaneleri_cek, etkinlikleri_cek)
    # buraya, bu iki satır arasına yapıştırın.
    
    # Örnek olarak çağrılar:
    # son_duyuruyu_cek()
    # eczaneleri_cek()
    # etkinlikleri_cek()
    
    print(f" İŞLEM TAMAMLANDI! ({round(time.time() - t0, 2)} sn)")
