import requests
from bs4 import BeautifulSoup
import urllib3
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# --- 1. FIREBASE BAĞLANTISI ---
# serviceAccountKey.json dosyasının bu kodla AYNI KLASÖRDE olması şarttır.
try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase bağlantısı başarılı!")
except Exception as e:
    print(f"🚨 Firebase Hatası: {e}")
    print("Lütfen 'serviceAccountKey.json' dosyasını kontrol et.")
    exit() # Bağlantı yoksa çalışmayı durdur

# --- ORTAK AYARLAR ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

# --- YARDIMCI FONKSİYON: FIREBASE GÜNCELLEME ---
def firestore_guncelle(koleksiyon_adi, veri_listesi):
    """
    Belirtilen koleksiyondaki eski verileri siler ve yeni listeyi yükler.
    Böylece her zaman en güncel liste veritabanında olur.
    """
    print(f"⏳ '{koleksiyon_adi}' koleksiyonu güncelleniyor...")
    
    batch = db.batch()
    collection_ref = db.collection(koleksiyon_adi)

    # 1. Adım: Eski dökümanları sil (Temizlik)
    docs = collection_ref.limit(500).stream()
    silinen_sayisi = 0
    for doc in docs:
        batch.delete(doc.reference)
        silinen_sayisi += 1
    
    # Silme işlemini onayla
    batch.commit()
    print(f"   🧹 {silinen_sayisi} eski kayıt silindi.")

    # 2. Adım: Yeni verileri ekle
    # Yeni bir batch başlatalım
    batch = db.batch()
    
    for veri in veri_listesi:
        # Yeni bir döküman referansı oluştur
        doc_ref = collection_ref.document() 
        batch.set(doc_ref, veri)
        
    batch.commit()
    print(f"   💾 {len(veri_listesi)} yeni kayıt başarıyla yüklendi.\n")


# --- 1. MODÜL: DUYURULARI ÇEK ---
def son_duyuruyu_cek():
    print("🚀 1/3: Duyurular Taranıyor...")
    base_url = "http://www.isparta.gov.tr"
    url = "http://www.isparta.gov.tr/duyurular"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20, verify=False)
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
                    "tarih": firestore.SERVER_TIMESTAMP # Sunucu saati eklendi
                })
            except: continue

        if duyuru_listesi:
            # Firestore'a gönder (Koleksiyon adı: duyurular)
            firestore_guncelle("duyurular", duyuru_listesi)
        else:
            print("❌ Duyuru bulunamadı.")

    except Exception as e:
        print(f"❌ Duyuru Hatası: {e}")


# --- 2. MODÜL: NÖBETÇİ ECZANELERİ ÇEK ---
def eczaneleri_cek():
    print("🚀 2/3: Eczaneler Taranıyor...")
    url = "https://www.eczaneler.gen.tr/nobetci-isparta"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Bugünün sekmesini bul
        tab_linkleri = soup.find_all("a", class_="nav-link")
        aktif_tab_id = "nav-bugun"
        for link in tab_linkleri:
            if link.find("img"):
                href = link.get("href")
                if href: aktif_tab_id = href.replace("#", "")
                break
        
        aktif_kutu = soup.find("div", id=aktif_tab_id)
        if not aktif_kutu: return

        eczane_listesi = []
        satirlar = aktif_kutu.find_all("div", class_="row")

        for satir in satirlar:
            try:
                ilce_tag = satir.find("span", class_="bg-info")
                if not ilce_tag: continue
                ilce = ilce_tag.text.strip()
                
                link_tag = satir.find("a")
                if not link_tag: continue
                eczane_adi = link_tag.text.strip()
                
                sutunlar = satir.find_all("div", class_="col-lg-3")
                telefon = sutunlar[1].text.strip() if len(sutunlar) >= 2 else (sutunlar[0].text.strip() if sutunlar else "Yok")
                
                adres_col = satir.find("div", class_="col-lg-6")
                adres = adres_col.text.strip().replace(ilce, "").strip() if adres_col else ""

                eczane_listesi.append({
                    "eczane_adi": eczane_adi,
                    "telefon": telefon,
                    "adres": adres,
                    "ilce": ilce
                })
            except: continue

        if eczane_listesi:
            # Firestore'a gönder (Koleksiyon adı: eczaneler)
            firestore_guncelle("eczaneler", eczane_listesi)
            
    except Exception as e:
        print(f"❌ Eczane Hatası: {e}")


# --- 3. MODÜL: ETKİNLİKLERİ ÇEK ---
def etkinlikleri_cek():
    print("🚀 3/3: Etkinlikler Taranıyor...")
    base_url = "https://www.bubilet.com.tr" 
    url = "https://www.bubilet.com.tr/isparta"

    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
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
                
                etkinlik_listesi.append({
                    "sanatci": temiz_isim,
                    "tarih": tarih,
                    "mekan": mekan,
                    "fiyat": fiyat,
                    "resim": resim_url
                })
            except: continue

        if etkinlik_listesi:
            # Firestore'a gönder (Koleksiyon adı: etkinlikler)
            firestore_guncelle("etkinlikler", etkinlik_listesi)

    except Exception as e:
        print(f"❌ Etkinlik Hatası: {e}")


# --- ANA BLOK ---
if __name__ == "__main__":
    print("🤖 FIREBASE BOTU BAŞLATILIYOR...\n")
    t0 = time.time()
    
    son_duyuruyu_cek()
    eczaneleri_cek()
    etkinlikleri_cek()
    
    print(f"🏁 İŞLEM TAMAMLANDI! ({round(time.time() - t0, 2)} sn)")