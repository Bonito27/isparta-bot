import requests 
from bs4 import BeautifulSoup 
import json 
import os 
import re 

# Scraping yapılacak site
url = "https://www.gazete32.com.tr/isparta-sehir-ici-otobus-seferleri/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

def otobus_saatlerini_cek():
    print(f"Bağlanılıyor: {url}")
    
    try:
        # Siteden request isteme
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Hata: Siteye erişilemedi. Kod: {response.status_code}")
            return

        # Gelen veriyi işlenebilir hale getirme
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Sayfadaki açılıp kapanabilen butonları bulma
        butonlar = soup.find_all("button", class_="accordion")
        print(f"Sitede toplam {len(butonlar)} adet hat bulundu, işleniyor...")
        
        otobus_listesi = []

        for buton in butonlar:
            try:
                ham_isim = buton.text.strip()
                
                # Hat ismini temizleme
                # Sitedeki özel - işaretlerini standart - işaretine çevirme
                ham_isim = ham_isim.replace("–", "-").replace("—", "-")
                
                # Tireden bölüp sadece hat ismini (Örn: 'Hat 1') alma 
                if "-" in ham_isim:
                    hat_adi = ham_isim.split("-")[0].strip()
                else:
                    hat_adi = ham_isim # Tire yoksa ismin kendisini al
                
                # Saatleri bulma (Panel butondan hemen sonra gelen div'dir)
                panel = buton.find_next_sibling("div", class_="panel")
                if not panel: continue 

                panel_metni = panel.text
                
                # Regex ile saat formatına (00:00 veya 00.00) uyanları bulma
                bulunan_saatler = re.findall(r'\d{2}[:.]\d{2}', panel_metni)
                
                temiz_saatler = []
                for saat in bulunan_saatler:
                    # Noktaları iki noktaya çevir (12.30 -> 12:30)
                    saat = saat.replace(".", ":")
                    temiz_saatler.append(saat)

                # Eğer saat verisi boşsa bu hattı atla
                if not temiz_saatler: continue

                # Listeye ekleme
                veri = {
                    "hat_adi": hat_adi,
                    "saatler": temiz_saatler
                }
                otobus_listesi.append(veri)
                print(f" > {hat_adi} eklendi ({len(temiz_saatler)} saat)")

            except Exception as e:
                print(f"Bir hat işlenirken hata oluştu: {e}")
                continue

        # --- JSON OLARAK KAYDETME (KRİTİK GÜNCELLEME) ---
        
        # 1. Şu anki Python dosyasının olduğu yeri bul
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Bir üst klasöre çık (..) ve 'ispartaapp/assets' klasörüne git
        # Bu yapı senin 'ZAGROPYA' klasör yapına göre ayarlandı.
        target_folder = os.path.join(current_dir, "..", "ispartaapp", "jsons")
        
        # 3. Yolu normalize et (işletim sistemine uygun hale getir)
        target_folder = os.path.normpath(target_folder)

        # 4. Eğer 'ispartaapp/assets' klasörü yoksa oluştur (Hata almamak için)
        os.makedirs(target_folder, exist_ok=True)
        
        # 5. Dosya adını belirle
        dosya_yolu = os.path.join(target_folder, "otobus_saatleri.json")

        # Veriyi kaydet
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(otobus_listesi, f, ensure_ascii=False, indent=4)
            
        print("-" * 40)
        print(f"BAŞARILI! Dosya şuraya kaydedildi:")
        print(f"📂 {dosya_yolu}")
        print(f"Toplam {len(otobus_listesi)} hat verisi güncellendi.")

    except Exception as genel_hata:
        print(f"Beklenmedik bir hata oluştu: {genel_hata}")

if __name__ == "__main__":
    otobus_saatlerini_cek()