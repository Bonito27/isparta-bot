import requests
from bs4 import BeautifulSoup
import urllib3
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import re 

# --- 1. FIREBASE BAĞLANTISI ---
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print(" Firebase bağlantısı başarılı!")
except Exception as e:
    print(f" Firebase Hatası: {e}")
    print("Lütfen 'serviceAccountKey.json' dosyasını kontrol et.")
    exit() 

# --- ORTAK AYARLAR ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/53736"
}

# --- YARDIMCI FONKSİYON: FIREBASE GÜNCELLEME (Silme ve yeniden oluşturma) ---
def firestore_guncelle(koleksiyon_adi, veri_listesi):
    """
    Belirtilen koleksiyondaki eski verileri siler ve yeni listeyi yükler.
    """
    if not veri_listesi:
        print(f" '{koleksiyon_adi}' koleksiyonuna gönderilecek yeni veri yok. Güncelleme atlandı.")
        return

    print(f" '{koleksiyon_adi}' koleksiyonu güncelleniyor...")
    
    collection_ref = db.collection(koleksiyon_adi)
    
    # 1. Adım: Eski dökümanları sil
    while True:
        docs = collection_ref.limit(500).stream()
        silinecek_docs = list(docs)
        if not silinecek_docs:
            break

        silme_batch = db.batch()
        for doc in silinecek_docs:
            silme_batch.delete(doc.reference)
        
        silme_batch.commit()
        print(f"    {len(silinecek_docs)} eski kayıt silindi.")
        
        if len(silinecek_docs) < 500:
            break

    # 2. Adım: Yeni verileri ekle
    yeni_batch = db.batch()
    
    for veri in veri_listesi:
        doc_ref = collection_ref.document() 
        yeni_batch.set(doc_ref, veri)
        
    yeni_batch.commit()
    print(f"    {len(veri_listesi)} yeni kayıt başarıyla yüklendi.\n")


# --- 1. MODÜL: DUYURULARI ÇEK (Aynı Kaldı) ---
def son_duyuruyu_cek():
    print(" 1/3: Duyurular Taranıyor...")
    base_url = "http://www.isparta.gov.tr"
    url = "http://www.isparta.gov.tr/duyurular"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        response.raise_for_status() 

        soup = BeautifulSoup(response.content, "html.parser")
        duyuru_linkleri = soup.find_all("a", class_="announce-text")
        
        duyuru_listesi = []
        for link_etiketi in duyuru_linkleri:
            try:
                baslik = link_etiketi.text.strip()
                href = link_etiketi.get("href")
                full_link = base_url + href if href.startswith("/") else href
                
                duyuru_listesi.append({
                    "baslik": baslik,
                    "link": full_link,
                    "tarih": firestore.SERVER_TIMESTAMP 
                })
            except Exception as e: 
                print(f" [DEBUG] Duyuru işleme hatası: {e}")
                continue

        if duyuru_listesi:
            firestore_guncelle("duyurular", duyuru_listesi)
        else:
            print(" Duyuru bulunamadı.")

    except Exception as e:
        print(f" Duyuru Hatası: {e}")


# --- 2. MODÜL: NÖBETÇİ ECZANELERİ ÇEK (ÇALIŞAN YAPINIZ ENTEGRE EDİLDİ) ---
def eczaneleri_cek():
    print(" 2/3: Eczaneler Taranıyor... (eczaneler.gen.tr)")
    url = "https://www.eczaneler.gen.tr/nobetci-isparta"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15, verify=False)
        response.raise_for_status() # 4xx/5xx hatası varsa istisna fırlat

        soup = BeautifulSoup(response.content, "html.parser")
        
        # Günü bulma filtresi
        tab_linkleri = soup.find_all("a", class_="nav-link")
        aktif_tab_id = None
        
        for link in tab_linkleri:
            ikon = link.find("img")
            
            if ikon:
                href_degeri = link.get("href")
                if href_degeri:
                    aktif_tab_id = href_degeri.replace("#", "")
                    print(f" [DEBUG] Aktif Sekme Tespit Edildi: {aktif_tab_id}")
                    break
        
        if not aktif_tab_id:
            aktif_tab_id = "nav-bugun"
            print(f" [DEBUG] Aktif Sekme İkonu bulunamadı, varsayılan: {aktif_tab_id}")


        aktif_kutu = soup.find("div", id=aktif_tab_id)
        
        if not aktif_kutu:
            print(f" ❌ Hata: İçerik kutusu ({aktif_tab_id}) bulunamadı.")
            return

        # Eczane satırları
        eczane_satirlari = aktif_kutu.find_all("div", class_="row")
        print(f" [DEBUG] Bu sekmede {len(eczane_satirlari)} adet satır bulundu.")
        
        eczane_listesi = []

        for satir in eczane_satirlari:
            try:
                # İlçe filtresi
                ilce_etiketi = satir.find("span", class_="bg-info")
                if not ilce_etiketi: continue
                ilce = ilce_etiketi.text.strip()
                
                # Eczane Adı
                link_etiketi = satir.find("a")
                if not link_etiketi: continue
                eczane_adi = link_etiketi.text.strip()
                
                # Telefon
                sutunlar = satir.find_all("div", class_="col-lg-3")
                telefon = "Telefon Yok"
                if len(sutunlar) >= 2:
                    telefon = sutunlar[1].text.strip()
                elif len(sutunlar) == 1:
                    telefon = sutunlar[0].text.strip()
                
                # Adres
                adres_sutunu = satir.find("div", class_="col-lg-6")
                if adres_sutunu:
                    raw_adres = adres_sutunu.text.strip()
                    adres = raw_adres.replace(ilce, "").strip() # Adresten ilçe ismini temizle
                else:
                    adres = "Adres Belirtilmemiş"

                # Telefon numarası geçerliliğini kontrol et (En az 7 rakam içermeli)
                if re.search(r'\d{7,}', telefon):
                    veri = {
                        "eczane_adi": eczane_adi,
                        "telefon": telefon,
                        "adres": adres,
                        "ilce": ilce,
                    }
                    eczane_listesi.append(veri)
                else:
                    print(f" [DEBUG] Telefonu geçersiz (Regex hatası): '{telefon}' / Eczane: {eczane_adi}")


            except Exception as e:
                print(f" [DEBUG] Tekil eczane işleme hatası: {e} / Eczane: {eczane_adi if 'eczane_adi' in locals() else 'Bilinmiyor'}")
                continue

        if eczane_listesi:
            print(f" [DEBUG] Firestore'a gönderilecek kayıt sayısı: {len(eczane_listesi)}")
            firestore_guncelle("eczaneler", eczane_listesi)
        else:
            print(" Eczane bulunamadı veya çekilen liste boş.")

    except requests.RequestException as req_e:
        print(f" Eczane Hatası (Ağ/HTTP): {req_e}")
    except Exception as e:
        print(f" Eczane Hatası: {e}")


# --- 3. MODÜL: ETKİNLİKLERİ ÇEK (Aynı Kaldı) ---
def etkinlikleri_cek():
    print(" 3/3: Etkinlikler Taranıyor...")
    base_url = "https://www.bubilet.com.tr" 
    url = "https://www.bubilet.com.tr/isparta"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        tarih_etiketleri = soup.find_all("p", class_="mt-0.5 text-xs text-gray-500")
        
        etkinlik_listesi = []
        for tarih_tag in tarih_etiketleri:
            try:
                tarih = tarih_tag.text.strip()
                yazi_kutusu = tarih_tag.parent
                ana_kart = yazi_kutusu.parent.parent 

                mekan = yazi_kutusu.find("span", class_="truncate").text.strip()
                
                fiyat_tag = ana_kart.find("span", class_="tracking-tight")
                fiyat = f"{fiyat_tag.text.strip()} TL" if fiyat_tag and fiyat_tag.text.strip().isdigit() else (fiyat_tag.text.strip() if fiyat_tag else "Ücretsiz/Bilinmiyor")

                img = ana_kart.find("img")
                resim = img.get("data-src") or img.get("src")
                resim_url = base_url + resim if resim and resim.startswith("/") else (resim if resim else "")

                ham_isim = yazi_kutusu.text
                temiz_isim = ham_isim.replace(tarih, "").replace(mekan, "").replace(fiyat.replace(" TL",""),"").replace("TL","").strip()
                
                # "₺" Temizleme
                sanatci_adi = temiz_isim.replace('₺', '').strip() 
                
                etkinlik_listesi.append({
                    "sanatci": sanatci_adi,
                    "tarih": tarih,
                    "mekan": mekan,
                    "fiyat": fiyat,
                    "resim": resim_url
                })
            except Exception as e:
                print(f" [DEBUG] Tekil etkinlik işleme hatası: {e}")
                continue

        if etkinlik_listesi:
            firestore_guncelle("etkinlikler", etkinlik_listesi)

    except Exception as e:
        print(f" Etkinlik Hatası: {e}")


# --- ANA BLOK ---
if __name__ == "__main__":
    print(" FIREBASE BOTU BAŞLATILIYOR...\n")
    t0 = time.time()
    
    son_duyuruyu_cek()
    eczaneleri_cek()
    etkinlikleri_cek()
    
    print(f" İŞLEM TAMAMLANDI! ({round(time.time() - t0, 2)} sn)")
