# EPİAŞ Veri İndirici — Streamlit Cloud Kurulum

## Dosya Yapısı

```
epias_streamlit/
├── app.py
├── api.py
├── cache.py
├── excel_writer.py
├── requirements.txt
└── README.md
```

## Streamlit Cloud'a Yükleme

1. **GitHub'a yükle**
   - Yeni bir GitHub reposu oluştur (private olabilir)
   - Bu klasördeki tüm dosyaları repoya yükle

2. **Streamlit Cloud'da deploy et**
   - https://share.streamlit.io adresine git
   - "New app" → GitHub reposunu seç
   - Main file path: `app.py`
   - Deploy!

## Lokal Test

```bash
pip install streamlit requests openpyxl
streamlit run app.py
```

## Kullanım Akışı

1. **Sol panel → EPİAŞ bilgilerini gir → Giriş Yap**
2. **Tarih aralığını seç**
3. **🔄 Tesis Listesini Yenile** (ilk kez veya güncel liste için)
   - Tesis listesi `facility_cache.json` dosyasına kaydedilir
   - Sonraki açılışlarda otomatik yüklenir, tekrar çekmene gerek yok
4. **Arama kutusuna tesis adı yaz** → sonuçlardan seç → Ekle
5. **Veriyi Çek & Excel Oluştur**
6. **📥 Excel İndir**

## Cache Hakkında

- Tesis listesi `facility_cache.json` dosyasında saklanır
- Streamlit Cloud'da bu dosya deploy edilen repoda oluşur
- Uygulama yeniden başlatılsa bile tesis listesi kaybolmaz
- Yeni tesisler EPİAŞ'a eklendiğinde manuel olarak yenile butonuna bas

## UEVM Eşleştirmesi

UEVM verisi için tesis adı ENTSO listesiyle eşleştirilir.
Tam eşleşme bulunamazsa kısmi eşleşme denenir.
Eşleşme bulunamazsa o tesise ait UEVM sütunu boş kalır.
