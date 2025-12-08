import requests
from bs4 import BeautifulSoup
import json
import os
import urllib3

# SSL uyarılarını kapatma
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base_url = "http://www.isparta.gov.tr"
url = "http://www.isparta.gov.tr/duyurular"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

def son_duyuruyu_cek():
    print(f"Bağlanılıyor: {url}")
    
    try:
        # SSL hatalarını aşmak için HTTP protokolü ve verify=False kullanıyoruz
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if response.status_code != 200:
            print(f"Hata: Siteye erişilemedi. Kod: {response.status_code}")
            return

    except Exception as e:
        print(f"Bağlantı Hatası: {e}")
        return

    # gelen veriyi HTML yapısına çevirme
    soup = BeautifulSoup(response.content, "html.parser")
    
    # sayfadaki tüm linkleri taramak yerine doğrudan duyuru başlığının sahip olduğu özel class hedefliyoruz.
    hedef_duyuru = soup.find("a", class_="announce-text")
    
    son_duyuru = None

    if hedef_duyuru:
        baslik = hedef_duyuru.text.strip()
        href = hedef_duyuru.get("href")
        
        # gelen link yarım ise başına adres ekleniyor
        if href.startswith("/"):
            full_link = base_url + href
        else:
            full_link = href
            
        son_duyuru = {
            "baslik": baslik,
            "link": full_link
        }
    else:
        # eğer site tasarımı değişir ve bu sınıf silinirse uyarı veriyoruz
        print("Uyarı: 'announce-text' sınıfına sahip link bulunamadı.")

    if son_duyuru:
        # assets klasörünü bul yoksa oluştur
        klasor_yolu = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
        os.makedirs(klasor_yolu, exist_ok=True)
        dosya_yolu = os.path.join(klasor_yolu, "son_duyuru.json")

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(son_duyuru, f, ensure_ascii=False, indent=4)
            
        print("-" * 30)
        print(f"Başarılı! En güncel duyuru kaydedildi.")
        print(f"Başlık: {son_duyuru['baslik']}")
        print(f"Dosya: {dosya_yolu}")
    else:
        print("Kayıt başarısız.")

if __name__ == "__main__":
    son_duyuruyu_cek()