import requests 
from bs4 import BeautifulSoup 
import json 
import os 

base_url = "https://www.bubilet.com.tr" 
url = "https://www.bubilet.com.tr/isparta"

# Siteye robot olmadığımızı göstermek için header bilgisi
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

def veri_cek_final():
    print(f"Sunucu isteği gönderiliyor: {url}")
    
    try:
        # SİTEYE BAĞLANMA
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Hata: Siteye bağlanılamadı. Kod: {response.status_code}")
            return

        # Gelen ham veriyi işlenebilir HTML yapısına çevirme 
        soup = BeautifulSoup(response.content, "html.parser")
        
        tarih_etiketleri = soup.find_all("p", class_="mt-0.5 text-xs text-gray-500")
        
        print(f"Bulunan Etkinlik Sayısı: {len(tarih_etiketleri)}")
        
        sonuc_listesi = []

        for tarih_tag in tarih_etiketleri:
            try:
                # Verileri toplama
                
                # Tarih verisi
                tarih = tarih_tag.text.strip()
                
                yazi_kutusu = tarih_tag.parent
                ana_kart = yazi_kutusu.parent.parent 

                # Mekan verisi
                mekan_tag = yazi_kutusu.find("span", class_="truncate")
                mekan = mekan_tag.text.strip() if mekan_tag else ""

                # Fiyat Verisi
                fiyat_tag = ana_kart.find("span", class_="tracking-tight")
                raw_fiyat_text = "" 
                fiyat = "Fiyat Yok"

                if fiyat_tag:
                    raw_fiyat_text = fiyat_tag.text.strip()
                    if raw_fiyat_text.isdigit():
                        fiyat = f"{raw_fiyat_text} TL"
                    else:
                        fiyat = raw_fiyat_text

                # Resim verisi
                img_tag = ana_kart.find("img")
                resim_url = "https://via.placeholder.com/150" 

                if img_tag:
                    ham_link = img_tag.get("data-src") or img_tag.get("src")
                    
                    if ham_link:
                        if ham_link.startswith("/"):
                            resim_url = base_url + ham_link
                        else:
                            resim_url = ham_link

                # Sanatçı ismini temizleme
                ham_metin = yazi_kutusu.text
                
                temiz_isim = ham_metin.replace(tarih, "").replace(mekan, "")
                
                if raw_fiyat_text:
                    temiz_isim = temiz_isim.replace(raw_fiyat_text, "")
                
                temiz_isim = temiz_isim.replace("TL", "").replace("tl", "").replace("₺", "")
                isim = " ".join(temiz_isim.split()) 

                # Listeyi oluşturma
                veri = {
                    "sanatci": isim,
                    "tarih": tarih,
                    "mekan": mekan,
                    "price": fiyat,
                    "image": resim_url
                }
                sonuc_listesi.append(veri)
                
            except AttributeError:
                continue

        # --- JSON OLARAK KAYDETME (FLUTTER PROJESİ İÇİNE) ---
        
        # 1. Şu anki Python dosyasının yerini bul
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. Bir üst klasöre çık ve 'ispartaapp/assets' klasörüne git
        # NOT: Flutter'ın görebilmesi için 'jsons' yerine 'assets' kullandık.
        target_folder = os.path.join(current_dir, "..", "ispartaapp", "jsons")
        
        # 3. Yolu düzelt (Windows/Mac uyumu için)
        target_folder = os.path.normpath(target_folder)

        # 4. Klasör yoksa oluştur
        os.makedirs(target_folder, exist_ok=True)
        
        # 5. Dosya yolu
        dosya_yolu = os.path.join(target_folder, "etkinlik.json")

        # 6. Kaydet
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            json.dump(sonuc_listesi, f, ensure_ascii=False, indent=4)
        
        print("-" * 30)
        print(f"BAŞARILI! Dosya şuraya kaydedildi:")
        print(f"📂 {dosya_yolu}")
        print(f"Toplam {len(sonuc_listesi)} etkinlik kaydedildi.")

    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {e}")

if __name__ == "__main__":
    veri_cek_final()