# Editöryal Süreç Yöneticisi

## Genel Bakış
Bu uygulama, Python ve Tkinter kullanılarak geliştirilmiş, roman yazarları ve editörler için tasarlanmış kapsamlı bir editöryal süreç yönetimi aracıdır. Google Gemini AI entegrasyonu sayesinde metinleri dilbilgisi, stil ve içerik açısından analiz eder, editöryal öneriler sunar ve proje bazlı olarak tüm süreci yönetmenize olanak tanır. Uygulama, `.txt` ve `.docx` formatındaki dosyaları destekler ve Word belgelerindeki temel formatlamaları (kalın, italik, altı çizili, başlıklar ve hizalama) korur.

## Temel Özellikler

- **Proje Yönetimi**: Çalışmalarınızı proje olarak kaydedin, yükleyin, silin ve daha sonra kaldığınız yerden devam edin.
- **Proje Geçmişi ve Sürüm Kontrolü**: Projenizin önceki kayıtlı sürümlerini (otomatik veya manuel) görüntüleyin ve tek tıkla istediğiniz bir sürüme geri dönün.
- **Otomatik Kaydetme**: Belirlediğiniz aralıklarla projeniz otomatik olarak kaydedilir, veri kaybı önlenir.
- **AI Destekli Analiz**:
  - **Sıralı Analiz Sistemi**: Editöryal süreci taklit ederek metinleri önce **Dilbilgisi**, sonra **Stil** ve son olarak **İçerik** açısından analiz eder.
  - **Özelleştirilebilir Modeller**: Her analiz türü (Dilbilgisi, Stil, İçerik, Roman Özeti) için farklı Gemini modelleri (örn: Flash, Pro) seçebilme.
  - **Dinamik Timeout**: Metin uzunluğuna göre AI isteklerinin bekleme süresini otomatik ayarlar.
- **Etkileşimli Arayüz**:
  - Önerileri kartlar halinde görüntüleme.
  - Önerileri tek tıkla metne uygulama veya reddetme.
  - Uygulanan değişikliklerin metin üzerinde vurgulanması ve detaylarının fare ile üzerine gelince gösterilmesi.
- **Formatlama Desteği**: `.docx` dosyalarından gelen kalın, italik, altı çizili, başlık ve hizalama gibi temel metin formatlamalarını tanır, korur ve dışa aktarır.
- **Özelleştirilebilir Promptlar**: "Ayarlar" menüsünden her bir analiz türü için AI'a gönderilen komutları (prompt) düzenleyebilirsiniz.
- **İlerleme Takibi**: Bölümlerin analiz durumunu (işlenmiş/işlenmemiş) görsel olarak takip etme ve proje geneli istatistikleri görme.
- **Hata Yönetimi ve Debug Konsolu**: Uygulama içi logları görüntüleyerek olası sorunları tespit etme.

## Kurulum

### Gereksinimler
- Python 3.8 veya üzeri
- Google Generative AI API anahtarı (Gemini için)

### Kurulum Adımları
1. Proje klasörüne gidin:
   ```bash
   cd /path/to/AIEditor4
   ```

2. Gerekli Python kütüphanelerini yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

## Uygulamayı Çalıştırma
Uygulamayı başlatmak için aşağıdaki komutu terminalde çalıştırın:
```bash
python main.py
```

## Kullanım Akışı

1.  **Roman Yükleme**: `Dosya > Roman Yükle` menüsünden `.txt` veya `.docx` formatındaki romanınızı seçin. Uygulama, metni bölümlere ayırmanız için size çeşitli seçenekler sunacaktır.
2.  **AI Ayarları**: `Ayarlar > AI Ayarları` menüsünden Google Gemini API anahtarınızı girin. İsteğe bağlı olarak her analiz türü için farklı AI modelleri seçebilir ve bağlantıyı test edebilirsiniz.
3.  **Bölüm Seçimi**: Sol panelden analiz etmek istediğiniz bölümü seçin.
4.  **Sıralı Analiz**:
    *   **"Dilbilgisi Analizi"** butonuna tıklayarak ilk aşamayı başlatın.
    *   Gelen önerileri "Uygula" veya "Reddet" butonları ile işleyin.
    *   Tüm dilbilgisi önerileri bittiğinde, buton otomatik olarak **"Stil Analizi"** olarak değişecektir.
    *   Aynı işlemi stil ve son olarak **"İçerik Analizi"** için tekrarlayın.
5.  **Proje Kaydetme**: `Dosya > Projeyi Kaydet` seçeneği ile çalışmanızın mevcut durumunu kaydedin.
6.  **Proje Geçmişi**: `Dosya > Proje Geçmişini Aç` menüsünden projenizin önceki kayıtlı sürümlerini görüntüleyebilir ve istediğiniz bir kaydı geri yükleyebilirsiniz.

## Dosya Yapısı
```
AIEditor4/
├── main.py                     # Uygulamanın giriş noktası
├── app_core.py                 # Ana uygulama sınıfı (EditorialApp)
├── ui_manager.py               # Ana arayüzün oluşturulması ve yönetimi
├── ai_manager.py               # AI ile ilgili ayarlar ve işlemlerin yönetimi
├── file_operations.py          # Dosya/proje yükleme, kaydetme, dışa aktarma
├── auto_save_manager.py        # Otomatik kaydetme mantığı
├── analysis_manager.py         # Analiz sürecinin yönetimi
├── requirements.txt            # Gerekli Python kütüphaneleri
├── README.md                   # Bu döküman
├── data/                       # Projeler ve ayarlar
│   ├── projects/               # Kaydedilen projelerin klasörleri
│   └── settings.json           # Uygulama ayarları
└── modules/                    # Uygulama modülleri
    ├── ai_integration.py       # Google Gemini AI entegrasyonu
    ├── editorial_process.py    # Editöryal analiz mantığı
    ├── file_manager.py         # Dosya ve bölüm yönetimi
    ├── formatting_manager.py   # Metin formatlama yönetimi
    ├── settings_manager.py     # Ayarların yönetimi
    └── ui_components.py        # Tkinter arayüz bileşenleri
```

## İpuçları

- **API Anahtarı**: Gemini API anahtarınızı [Google AI Studio](https://makersuite.google.com/) üzerinden alabilirsiniz.
- **Performans**: Çok büyük metinlerde analiz süresi uzayabilir. Dinamik timeout ayarı bu süreyi yönetmeye yardımcı olur.
- **Kaydetme**: Önemli değişikliklerden sonra projenizi manuel olarak kaydetmeyi unutmayın. Otomatik kaydetme ve proje geçmişi özellikleri sizi veri kaybından koruyacaktır.

## Lisans
Bu uygulama eğitim ve kişisel kullanım amaçlı geliştirilmiştir. Ticari kullanım için Google AI API kullanım şartlarına uymanız gerekmektedir.
