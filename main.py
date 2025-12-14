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

# --- YARDIMCI FONKSİYON: FIREBASE GÜNCELLEME ---
def firestore_guncelle(koleksiyon_adi, veri_listesi):
    """
    Belirtilen koleksiyondaki eski verileri siler ve yeni listeyi yükler.
    """
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


# --- 1. MODÜL: DUYURULARI ÇEK ---
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


# --- 2. MODÜL: NÖBETÇİ ECZANELERİ ÇEK (GÜÇLENDİRİLMİŞ REGEX İLE) ---
def eczaneleri_cek():
    print(" 2/3: Eczaneler Taranıyor... (eczaneler.gen.tr'nin kart yapısı hedefleniyor)")
    # URL'yi tekrar kontrol edin, bu kod eczaneler.gen.tr'deki yapıyı hedefliyor.
    url = "https://www.eczaneler.gen.tr/nobetci-isparta"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        response.raise_for_status() 
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 1. Adım: Aktif sekme ID'sini bul
        aktif_tab_id = "nav-bugun"  
        for link in soup.find_all("a", class_="nav-link"):
            if link.find("img"): 
                href = link.get("href")
                if href and href.startswith("#"): 
                    aktif_tab_id = href.replace("#", "")
                    break

        aktif_kutu = soup.find("div", id=aktif_tab_id)
        
        if not aktif_kutu: 
             print(f" ❌ Hata: Aktif eczane sekmesi ID'si ({aktif_tab_id}) bulunamadı veya boş.")
             return

        # 2. Adım: Paylaşılan HTML yapısını hedefle: <div class="trend-content">
        eczaneler_kartlari = aktif_kutu.find_all("div", class_="trend-content")
        
        print(f" [DEBUG] Toplam bulunan eczane kartı: {len(eczaneler_kartlari)}")

        if not eczaneler_kartlari:
             print(" ❌ Hata: 'trend-content' yapısına sahip kart bulunamadı.")
             return

        eczane_listesi = []
        
        for kart in eczaneler_kartlari:
            try:
                # Eczane Adı: <h3 class="theme">
                eczane_adi_tag = kart.find("h3", class_="theme")
                # İlçe: <h5>
                ilce_tag = kart.find("h5")
                
                # Adres ve Telefon <p class="mb-2"> etiketlerinde
                paragraflar = kart.find_all("p", class_="mb-2")
                
                # Temel kontroller
                if not eczane_adi_tag or not ilce_tag or len(paragraflar) < 2:
                    print(" [DEBUG] Eksik etiketler nedeniyle kart atlandı.")
                    continue

                eczane_adi = eczane_adi_tag.text.strip()
                ilce = ilce_tag.text.strip()
                
                # Adres Çekme (İlk <p class="mb-2">)
                adres_p = paragraflar[0]
                # Tüm içerik metni
                adres_metni = adres_p.text.strip()
                # İkonları kaldırmadan, sadece metni alıyoruz
                adres = re.sub(r'\s{2,}', ' ', adres_metni).strip()
                # Adres metninin temizlenmesi gerekebilir (Örn: İkon metinleri)
                
                # Telefon Çekme (İkinci <p class="mb-2">)
                telefon_p = paragraflar[1]
                telefon_ham = telefon_p.text.strip()
                
                # 🔥🔥🔥 KRİTİK DÜZELTME: Sadece rakamları çeken Regex 🔥🔥🔥
                # Telefon metnindeki tüm rakamları ve '+' işaretini çeker.
                telefon_sadece_rakam = re.sub(r'[^\d+]', '', telefon_ham)
                
                # Sadece rakam içeren ve uzunluğu 10-15 karakter arasında olanları geçerli kabul et
                if len(telefon_sadece_rakam) >= 10:
                    telefon = telefon_sadece_rakam
                    eczane_listesi.append({
                        "eczane_adi": eczane_adi,
                        "telefon": telefon,
                        "adres": adres,
                        "ilce": ilce
                    })
                else:
                    print(f" [DEBUG] Telefonu geçersiz (yeterli rakam yok): '{telefon_ham}' / Eczane: {eczane_adi}")

            except Exception as e:
                print(f" [DEBUG] Tekil eczane işleme hatası ({eczane_adi}): {e}")
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
    eczaneleri_cek() # Bu modül artık paylaştığınız HTML yapısına güvenerek çalışıyor
    etkinlikleri_cek()
    
    print(f" İŞLEM TAMAMLANDI! ({round(time.time() - t0, 2)} sn)")
