import requests 
from bs4 import BeautifulSoup 
import json 
import os 
import urllib3 

# Sertifika hatalarını gizleme (Site bazen SSL hatası verebiliyor)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
url = "https://www.eczaneler.gen.tr/nobetci-isparta"

# Chrome gibi gözükmek için header
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

def eczaneleri_cek():
    print(f"Bağlanılıyor: {url}")
    
    # Siteye bağlanma
    try:
        # Güvenlik sertifikası eski olsa da kabul et (verify=False)
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if response.status_code != 200:
            print("Hata: Siteye erişilemedi.")
            return
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")
    
    # Günü bulma filtresi
    # Sitede 3 günün hepsi aynı anda yükleniyor, bugünün tarihinde 'img' ikonu var.
    tab_linkleri = soup.find_all("a", class_="nav-link")
    aktif_tab_id = None
    
    for link in tab_linkleri:
        ikon = link.find("img")
        
        if ikon:
            href_degeri = link.get("href")
            if href_degeri:
                aktif_tab_id = href_degeri.replace("#", "") 
                print(f"Aktif Sekme (Bugün) Tespit Edildi: {aktif_tab_id}")
                break
    
    # İkon bulunmazsa varsayılan olarak 'nav-bugun' kullan
    if not aktif_tab_id:
        aktif_tab_id = "nav-bugun"

    # Aramayı daraltma (Sadece bugünün kutusuna bak)
    aktif_kutu = soup.find("div", id=aktif_tab_id)
    
    if not aktif_kutu:
        print("Hata: İçerik kutusu bulunamadı.")
        return

    # Sadece aktif kutunun içindeki satırları al
    eczane_satirlari = aktif_kutu.find_all("div", class_="row")
    print(f"Bu sekmede {len(eczane_satirlari)} adet nöbetçi eczane işleniyor.")
    
    eczane_listesi = []

    for satir in eczane_satirlari:
        try:
            # İlçe/Merkez filtresi (Genelde 'Isparta' veya ilçe adı yazar)
            ilce_etiketi = satir.find("span", class_="bg-info")
            if not ilce_etiketi: continue
                
            ilce = ilce_etiketi.text.strip()
            
            # Verileri çekme
            link_etiketi = satir.find("a")
            if not link_etiketi: continue
            
            eczane_adi = link_etiketi.text.strip()
            detay_url = "https://www.eczaneler.gen.tr" + link_etiketi.get("href")

            sutunlar = satir.find_all("div", class_="col-lg-3")
            telefon = "Telefon Yok"
            if len(sutunlar) >= 2:
                telefon = sutunlar[1].text.strip()
            elif len(sutunlar) == 1:
                telefon = sutunlar[0].text.strip()
            
            adres_sutunu = satir.find("div", class_="col-lg-6")
            if adres_sutunu:
                raw_adres = adres_sutunu.text.strip()
                # Adresten ilçe ismini temizle ki tekrar etmesin
                adres = raw_adres.replace(ilce, "").strip()
            else:
                adres = "Adres Belirtilmemiş"

            # Listeye ekle
            veri = {
                "eczane_adi": eczane_adi,
                "telefon": telefon,
                "adres": adres,
                "ilce": ilce,
                "detay_url": detay_url
            }
            eczane_listesi.append(veri)

        except Exception as e:
            continue

    # --- JSON OLARAK KAYDETME (FLUTTER PROJESİ İÇİNE) ---
    
    # 1. Şu anki Python dosyasının yerini bul
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Bir üst klasöre çık ve 'ispartaapp/assets' klasörüne git
    target_folder = os.path.join(current_dir, "..", "ispartaapp", "jsons")
    
    # 3. Yolu düzelt (Windows/Mac uyumu için)
    target_folder = os.path.normpath(target_folder)

    # 4. Klasör yoksa oluştur
    os.makedirs(target_folder, exist_ok=True)
    
    # 5. Dosya yolu
    dosya_yolu = os.path.join(target_folder, "nobetci_eczaneler.json")

    # 6. Kaydet
    with open(dosya_yolu, "w", encoding="utf-8") as f:
        json.dump(eczane_listesi, f, ensure_ascii=False, indent=4)
        
    print("-" * 30)
    print(f"BAŞARILI! Dosya şuraya kaydedildi:")
    print(f"📂 {dosya_yolu}")
    print(f"Toplam {len(eczane_listesi)} eczane kaydedildi.")

if __name__ == "__main__":
    eczaneleri_cek()