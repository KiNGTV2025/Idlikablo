import requests
import json
import gzip
from io import BytesIO
import os
import time
import re
from datetime import datetime

# GitHub için dosya yolu
M3U_DOSYA_YOLU = "1UmitTV.m3u"

# Özel grup ön eki
GRUP_ON_EKI = "🜲ÜⲘ𝖎ţ KabloNet🜲"
HEDEF_GRUP = "http://45.159.95.10:8880/STORE/DIZI.SON.BOLUMLER/Esref.Ruya.SON.mkv"

def temizle_tum_eski_kablo_url(icerik):
    """Tüm eski KabloTV URL'lerini temizler (süresine bakmadan)"""
    temiz_icerik = []
    i = 0
    while i < len(icerik):
        satir = icerik[i]
        
        # Eğer bu bir EXTINF satırıysa ve sonraki satır URL ise kontrol et
        if satir.startswith('#EXTINF') and i+1 < len(icerik):
            url = icerik[i+1].strip()
            
            # Tüm kablonet URL'lerini sil
            if 'kablowebtv.net' in url and 'wmsAuthSign=' in url:
                print(f"🗑️ Eski KabloTV URL silindi: {url[:50]}...")
                i += 2  # Hem EXTINF hem de URL satırını atla
                continue
        
        temiz_icerik.append(satir)
        i += 1
    
    return temiz_icerik

def id_ekle(icerik):
    """M3U içeriğine artan ID numaraları ekler"""
    yeni_icerik = []
    kanal_id = 1
    
    i = 0
    while i < len(icerik):
        satir = icerik[i]
        
        if satir.startswith('#EXTINF'):
            # ID'yi mevcut satıra ekle
            if 'tvg-id="' not in satir:
                # Eğer tvg-id yoksa ekle
                satir = satir.replace('#EXTINF:', f'#EXTINF:-1 tvg-id="{kanal_id}",', 1)
            else:
                # Eğer varsa güncelle
                satir = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{kanal_id}"', satir)
            
            yeni_icerik.append(satir)
            
            # URL satırını ekle
            if i+1 < len(icerik):
                yeni_icerik.append(icerik[i+1])
                i += 1
            
            kanal_id += 1
        else:
            yeni_icerik.append(satir)
        
        i += 1
    
    return yeni_icerik

def kanallari_guncelle():
    """Kanal listesini günceller ve dosyaya kaydeder"""
    url = "https://core-api.kablowebtv.com/api/channels"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Referer": "https://tvheryerde.com",
        "Origin": "https://tvheryerde.com",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJMSVZFIiwiaXBiIjoiMCIsImNnZCI6IjA5M2Q3MjBhLTUwMmMtNDFlZC1hODBmLTJiODE2OTg0ZmI5NSIsImNzaCI6IlRSS1NUIiwiZGN0IjoiM0VGNzUiLCJkaSI6ImE2OTliODNmLTgyNmItNGQ5OS05MzYxLWM4YTMxMzIxOGQ0NiIsInNnZCI6Ijg5NzQxZmVjLTFkMzMtNGMwMC1hZmNkLTNmZGFmZTBiNmEyZCIsInNwZ2QiOiIxNTJiZDUzOS02MjIwLTQ0MjctYTkxNS1iZjRiZDA2OGQ3ZTgiLCJpY2giOiIwIiwiaWRtIjoiMCIsImlhIjoiOjpmZmZmOjEwLjAuMC4yMDYiLCJhcHYiOiIxLjAuMCIsImFibiI6IjEwMDAiLCJuYmYiOjE3NDUxNTI4MjUsImV4cCI6MTc0NTE1Mjg4NSwiaWF0IjoxNzQ1MTUyODI1fQ.OSlafRMxef4EjHG5t6TqfAQC7y05IiQjwwgf6yMUS9E"
    }
    try:
        print(f"\n⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} - Güncelleme başlıyor...")
        
        # API isteği yap
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        # Sıkıştırılmış veriyi aç
        try:
            with gzip.GzipFile(fileobj=BytesIO(response.content)) as gz:
                icerik = gz.read().decode('utf-8')
        except:
            icerik = response.content.decode('utf-8')
        
        veri = json.loads(icerik)
        
        if not veri.get('IsSucceeded') or not veri.get('Data', {}).get('AllChannels'):
            print("❌ CanliTV API'den geçerli veri alınamadı!")
            return False
        
        yeni_kanallar = veri['Data']['AllChannels']
        print(f"✅ {len(yeni_kanallar)} yeni kanal bulundu")
        
        temp_dosya_yolu = f"{M3U_DOSYA_YOLU}_temp"
        
        # Eski geçici dosyaları sil
        if os.path.exists(temp_dosya_yolu):
            os.remove(temp_dosya_yolu)
            print("♻️ Eski geçici dosya silindi")
        
        # 1. ADIM: Önce tüm eski kanalları sil (GRUP_ON_EKI içerenleri)
        print("⏳ Eski kanallar siliniyor...")
        korunacak_satirlar = []
        hedef_grubun_konumu = -1
        
        if os.path.exists(M3U_DOSYA_YOLU):
            with open(M3U_DOSYA_YOLU, "r", encoding="utf-8") as f:
                satirlar = f.readlines()
                
                # Tüm eski KabloTV URL'lerini temizle
                satirlar = temizle_tum_eski_kablo_url(satirlar)
                
                for i, satir in enumerate(satirlar):
                    # GRUP_ON_EKI içermeyen satırları koru (başlık vs.)
                    if GRUP_ON_EKI not in satir:
                        korunacak_satirlar.append(satir)
                        # Hedef grubun konumunu kaydet
                        if HEDEF_GRUP in satir:
                            hedef_grubun_konumu = len(korunacak_satirlar) - 1
                    elif HEDEF_GRUP in satir:
                        korunacak_satirlar.append(satir)
        
        # Sadece korunacak satırları yaz (eski kanallar silinmiş olacak)
        with open(temp_dosya_yolu, "w", encoding="utf-8") as f:
            f.writelines(korunacak_satirlar)
        
        # 5 saniye bekle
        print("⏳ 5 saniye bekleniyor...")
        time.sleep(5)
        
        # 2. ADIM: Yeni kanalları işle
        print("⏳ Yeni kanallar ekleniyor...")
        guncel_kanallar = []
        kanal_sayisi = 0
        
        for kanal in yeni_kanallar:
            isim = kanal.get('Name', '').strip()
            stream_veri = kanal.get('StreamData', {})
            hls_url = (stream_veri.get('HlsStreamUrl') or '').strip()
            logo = (kanal.get('PrimaryLogoImageUrl') or '').strip()
            kategoriler = kanal.get('Categories', [])
            
            if not isim or not hls_url:
                continue
            
            grup = kategoriler[0].get('Name', 'Genel') if kategoriler else 'Genel'
            if grup == "Bilgilendirme":
                continue
            
            # Grup ismine özel ön ek ekle
            grup = f"{GRUP_ON_EKI} {grup}"
            
            extinf = f'#EXTINF:-1 tvg-id="" tvg-logo="{logo}" group-title="{grup}",{isim}'
            guncel_kanallar.append(f"{extinf}\n{hls_url}\n")
            kanal_sayisi += 1
        
        # Geçici dosyayı oku ve yeni kanalları ekle
        with open(temp_dosya_yolu, "r", encoding="utf-8") as f:
            icerik = f.readlines()
        
        # Yeni içeriği oluştur
        yeni_icerik = []
        if hedef_grubun_konumu != -1:
            # Hedef gruba kadar olan kısmı ekle
            yeni_icerik.extend(icerik[:hedef_grubun_konumu+1])
            # Yeni kanalları ekle
            yeni_icerik.extend(guncel_kanallar)
            # Hedef gruptan sonraki diğer içeriği ekle
            yeni_icerik.extend(icerik[hedef_grubun_konumu+1:])
        else:
            # Hedef grup yoksa, tüm korunacak satırları yaz, sonra yeni kanalları ekle
            yeni_icerik.extend(icerik)
            yeni_icerik.extend(guncel_kanallar)
        
        # ID'leri ekle
        yeni_icerik = id_ekle(yeni_icerik)
        
        # Yeni içeriği dosyaya yaz
        with open(temp_dosya_yolu, "w", encoding="utf-8") as f:
            f.writelines(yeni_icerik)
        
        # Eski dosyayı sil ve yeni dosyayı taşı
        if os.path.exists(M3U_DOSYA_YOLU):
            os.remove(M3U_DOSYA_YOLU)
        os.rename(temp_dosya_yolu, M3U_DOSYA_YOLU)
        
        print(f"📺 {M3U_DOSYA_YOLU} dosyası güncellendi!")
        print(f"ℹ️ {kanal_sayisi} yeni kanal eklendi")
        print(f"ℹ️ {GRUP_ON_EKI} ön ekli tüm eski kanallar silindi")
        print("ℹ️ Tüm eski KabloTV URL'leri (süresine bakılmadan) silindi")
        print("ℹ️ Tüm kanallara artan ID numaraları eklendi")
        if hedef_grubun_konumu != -1:
            print(f"ℹ️ Kanallar '{HEDEF_GRUP}' grubundan sonra eklendi")
        
        return True
        
    except Exception as hata:
        print(f"❌ Hata: {str(hata)}")
        return False

if __name__ == "__main__":
    print("🜲 ÜⲘ𝖎ţ KabloNet M3U Güncelleyici Başlatıldı")
    print(f"ℹ️ Kanallar '{HEDEF_GRUP}' grubundan sonra eklenecek")
    print("ℹ️ Tüm eski KabloTV URL'leri (süresine bakılmadan) silinecek")
    print("ℹ️ Tüm kanallara artan ID numaraları (1,2,3,...) eklenecek")
    
    # GitHub Actions'ta çalışıyorsak tek seferlik çalıştır
    kanallari_guncelle()
