# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# type: ignore

# Lazy import - Google AI sadece ihtiyaç duyulduğunda yüklenecek
from typing import Dict, List, Optional, Any, TYPE_CHECKING
import json
import time
import os
import datetime
import re
from .settings_manager import SettingsManager

# Type checking için - çalışma zamanında import edilmez
if TYPE_CHECKING:
    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
    except ImportError:
        # Fallback type hints
        genai = Any
        HarmCategory = Any
        HarmBlockThreshold = Any

# AI analiz hataları için özel Exception sınıfı
class AIAnalysisError(Exception):
    """AI analizi başarısız olduğunda fırlatılacak özel hata."""
    def __init__(self, message, error_type="generic_error", details=None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details

class AIIntegration:
    def __init__(self, settings_manager: SettingsManager):
        self.settings_manager = settings_manager
        self.api_key: str = ""
        self.model_name: str = "gemini-1.5-flash"
        # Add separate models for each analysis type
        self.models = {
            "style_analysis": "gemini-1.5-flash",
            "grammar_check": "gemini-1.5-flash",
            "content_review": "gemini-1.5-pro", # İçerik analizi için daha güçlü bir model
            "novel_context": "gemini-1.5-pro" # Özetleme için daha güçlü bir model
        }
        self.model_instances = {}
        self.prompts: Dict[str, str] = self.load_default_prompts()
    
    def update_settings(self, api_key: str, model_name: str, models_config: Dict[str, str] = None):
        """AI ayarlarını güncelle"""
        self.api_key = api_key
        self.model_name = model_name
        
        # Update individual models if provided
        if models_config:
            self.models.update(models_config)
        
        if api_key:
            try:
                import google.generativeai as genai
                from google.generativeai.types import HarmCategory, HarmBlockThreshold
                genai.configure(api_key=api_key)

                # En az kısıtlayıcı güvenlik ayarlarını tanımla
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
                
                # Create model instances for each analysis type with safety settings
                self.model_instances = {}
                print("AI Modelleri güvenlik ayarlarıyla başlatılıyor...")
                for analysis_type, model_name_str in self.models.items():
                    print(f"  - {analysis_type}: {model_name_str}")
                    self.model_instances[analysis_type] = genai.GenerativeModel(
                        model_name=model_name_str,
                        safety_settings=safety_settings
                    )
                
                # Also create a default model instance with safety settings
                self.model = genai.GenerativeModel(
                    model_name=self.model_name,
                    safety_settings=safety_settings
                )
                print("✅ Tüm AI modelleri en az kısıtlayıcı güvenlik ayarlarıyla yapılandırıldı.")
                return True
            except Exception as e:
                print(f"AI ayar hatası: {e}")
                return False
        return False
    
    def load_default_prompts(self) -> Dict[str, str]:
        """Varsayılan promptları yükle"""
        return {
            "style_analysis": """
Sen, kelimelerin ahengine ve cümlelerin ritmine odaklanan bir Üslup Editörüsün. Görevin, aşağıdaki roman bölümünü dil ve anlatım zarafeti açısından incelemektir. Olay örgüsü veya karakter gelişimi gibi içerik konularıyla ilgilenme.

{context_section}

SADECE aşağıdaki konulara odaklan:
1. CÜMLE YAPISI: Çok uzun veya çok kısa cümleler, cümle akıcılığı, devrik cümlelerin doğru kullanımı.
2. KELİME SEÇİMİ: Tekrar eden kelimeler, daha etkili kelime alternatifleri, argo veya metnin tonuna uymayan ifadeler.
3. ANLATIM TONU: Anlatımın genel tonu (örn: şiirsel, sade, mesafeli) bölümün atmosferiyle uyumlu mu?
4. AKICILIK VE RİTİM: Paragraflar arası geçişler ne kadar pürüzsüz? Metnin okunma ritminde bir sorun var mı?

ÖNEMLİ: Yanıtını SADECE Türkçe ve aşağıda belirtilen JSON formatında ver. Başka hiçbir metin veya açıklama ekleme.

**KURALLAR:**
1. Yanıtın BAŞINDAN SONUNA KADAR geçerli bir JSON formatında olmalıdır.
2. JSON listesi `[` ile başlamalı ve `]` ile bitmelidir. Asla yarım bırakma.
3. JSON dışında KESİNLİKLE hiçbir metin, açıklama veya not ekleme.
4. Eğer incelenecek metinde hiçbir hata bulamazsan, boş bir JSON listesi `[]` döndür.

**CEVAP FORMATI:**
```json
[
  {{
    "original_sentence": "üslup açısından sorunlu orijinal cümle",
    "suggested_sentence": "daha akıcı ve etkili hale getirilmiş cümle",
    "explanation": "Bu değişikliğin üsluba ne gibi bir katkı sağladığının kısa açıklaması.",
    "editor_type": "Üslup Editörü",
    "severity": "low"
  }}
]
```

İncelenecek roman bölümü:
{content}
""",
            
            "grammar_check": """
Sen bir metin editörüsün.
{context_section}
Aşağıdaki roman bölümünde SADECE dilbilgisi, yazım ve noktalama hatalarını tespit et.

ÖNEMLİ: Bu bir ROMAN METİNDİR. Lütfen sadece dil bilgisi açısından hata arayın.

Aranacak hatalar:
1. YAZIM HATALARI: Yanlış yazılan kelimeler, büyük-küçük harf hataları
2. DİLBİLGİSİ HATALARI: Özne-yüklem uyumsuzluğu, zamir kullanım hataları, durum eki hataları
3. NOKTALAMA HATALARI: Virgül kullanımı, nokta ve soru işareti, tırnak işaretleri
4. TÜRKÇE YAZIM KURALLARI: Ayrı/bitişik yazım, kesme işareti kullanımı

ÖNEMLİ: Yanıtını SADECE Türkçe olarak ver. Sadece dilbilgisi ile ilgili öneriler yap, politik, dini veya hassas konularda yorum yapma.

**KURALLAR:**
1. Yanıtın BAŞINDAN SONUNA KADAR geçerli bir JSON formatında olmalıdır.
2. JSON listesi `[` ile başlamalı ve `]` ile bitmelidir. Asla yarım bırakma.
3. JSON dışında KESİNLİKLE hiçbir metin, açıklama veya not ekleme.
4. Eğer incelenecek metinde hiçbir hata bulamazsan, boş bir JSON listesi `[]` döndür.

**CEVAP FORMATI: Sadece JSON formatında yanıt verin. Başka hiçbir açıklama eklemeyin.**

JSON formatı:
```json
[
  {{
    "original_sentence": "hatalı cümle tam olarak buraya",
    "suggested_sentence": "doğru yazılış tam olarak buraya",
    "explanation": "Hangi dil bilgisi kuralının ihlal edildiği ve neden düzeltilmesi gerektiği",
    "editor_type": "Dil Bilgisi Editörü",
    "severity": "high"
  }}
]
```

Roman bölümü:
{content}
""",
            
            "content_review": """
Sen, hikayenin bütününe odaklanan bir İçerik Editörüsün. Görevin, aşağıdaki roman bölümünü olay örgüsü, karakter gelişimi ve yapısal bütünlük açısından analiz etmektir. Dil bilgisi veya basit üslup hatalarıyla ilgilenme.

{context_section}

SADECE aşağıdaki konulara odaklan:
1. OLAY ÖRGÜSÜ VE MANTIK: Bölümdeki olaylar mantıklı mı? Hikayede çelişkiler veya boşluklar var mı? Olaylar romanın genel gidişatına hizmet ediyor mu?
2. KARAKTER TUTARLILIĞI VE DERİNLİĞİ: Karakterler kendi kişilikleriyle tutarlı davranıyor mu? Diyalogları doğal ve karakterlerine uygun mu? Bu bölüm karakter gelişimine katkı sağlıyor mu?
3. TEMPO VE YAPI: Bölümün temposu uygun mu (çok hızlı, çok yavaş)? Sahne geçişleri pürüzsüz mü? Gereksiz veya sıkıcı kısımlar var mı?
4. OKUYUCU ETKİSİ: Bu bölüm okuyucunun ilgisini çekiyor mu? Merak veya gerilim unsurları doğru kullanılmış mı?

ÖNEMLİ: Yanıtını SADECE Türkçe ve aşağıda belirtilen JSON formatında ver. Başka hiçbir metin veya açıklama ekleme.

**KURALLAR:**
1. Yanıtın BAŞINDAN SONUNA KADAR geçerli bir JSON formatında olmalıdır.
2. JSON listesi `[` ile başlamalı ve `]` ile bitmelidir. Asla yarım bırakma.
3. JSON dışında KESİNLİKLE hiçbir metin, açıklama veya not ekleme.
4. Eğer incelenecek metinde hiçbir hata bulamazsan, boş bir JSON listesi `[]` döndür.

**CEVAP FORMATI:**
```json
[
  {{
    "original_sentence": "içerik veya yapısal olarak sorunlu cümle/paragraf",
    "suggested_sentence": "hikayeyi güçlendirecek alternatif versiyon",
    "explanation": "Bu değişikliğin olay örgüsüne, karaktere veya tempoya nasıl katkı sağladığının detaylı açıklaması.",
    "editor_type": "İçerik Editörü",
    "severity": "medium"
  }}
]
```

İncelenecek roman bölümü:
{content}
""",
            "novel_context": """
Sen uzman bir edebiyat analistisin. Görevin, aşağıda verilen romanın tamamını okuyup, romanın temel yapı taşlarını içeren bir "Roman Kimliği" özeti oluşturmaktır.

Bu özet, diğer yapay zeka editörleri tarafından romanın bütünlüğünü korumak için bir referans olarak kullanılacaktır. Bu nedenle özetin net, anlaşılır ve kapsamlı olması çok önemlidir.

Lütfen aşağıdaki başlıkları kullanarak bir özet oluştur:

1.  **Ana Tema ve Alt Temalar:** Romanın ana mesajı nedir? Hangi yan temalar işleniyor (örn: aşk, ihanet, adalet arayışı)?
2.  **Ana Karakterler ve Gelişimleri:** Başlıca karakterler kimlerdir? Temel kişilik özellikleri, motivasyonları ve roman boyunca geçirdikleri değişimler nelerdir?
3.  **Anlatıcı Sesi ve Bakış Açısı:** Hikaye kimin ağzından anlatılıyor (1. şahıs, 3. şahıs tanrısal bakış açısı vb.)? Anlatıcının üslubu nasıl (güvenilir, mesafeli, duygusal vb.)?
4.  **Önemli Semboller ve Motifler:** Romanda tekrar eden, simgesel anlamlar taşıyan nesneler, mekanlar veya fikirler var mı?
5.  **Zaman ve Mekan:** Hikaye hangi zaman diliminde ve coğrafyada geçiyor? Ana mekanların atmosferi ve hikayedeki rolü nedir?
6.  **Genel Üslup ve Ton:** Romanın genel yazım stili (şiirsel, sade, akıcı vb.) ve okuyucuda uyandırdığı duygu (gerilim, melankoli, mizah vb.) nedir?

ÖNEMLİ: Cevabını sadece bu başlıkları içeren düz metin olarak ver. Başka bir yorum veya giriş/sonuç cümlesi ekleme.

İşte romanın tam metni:
{content}
"""
        }
    
    def analyze_chapter(self, content: str, analysis_type: str = "style_analysis", novel_context: Optional[str] = None, full_novel_content: Optional[str] = None) -> List[Dict]:
        """Bölümü analiz et ve öneriler döndür - Timeout ve hata yönetimi ile"""
        print(f"AI ANALIZ BAŞLATILDI: Tip={analysis_type}, İçerik uzunluğu={len(content) if content else 0}")
        
        # Use the specific model for this analysis type
        model_instance = self.model_instances.get(analysis_type)
        if not model_instance:
            print(f"UYARI: {analysis_type} için özel model bulunamadı, varsayılan model kullanılacak")
            model_instance = self.model
        
        if not model_instance:
            print("HATA: AI model yapılandırılmamış (model=None)")
            print(f"API Key durumu: {len(self.api_key) if self.api_key else 0} karakter")
            print(f"Model adı: {self.model_name}")
            return []
            
        if not content or len(content.strip()) == 0:
            print("HATA: Analiz edilecek içerik boş")
            return []
        
        prompt_template = self.prompts.get(analysis_type, self.prompts["style_analysis"])
        if not prompt_template:
            print(f"HATA: {analysis_type} için prompt bulunamadı")
            return []

        # Bağlam (context) bölümünü, ayarlara göre dinamik olarak oluştur
        context_section = ""
        if full_novel_content and analysis_type in ["style_analysis", "content_review", "grammar_check"]:
            # Tam metin kullanılıyorsa
            cleaned_full_content = self._clean_content_for_ai(full_novel_content)
            context_section = (
                "Bu bölümün ait olduğu romanın tam metni referans olarak aşağıdadır. "
                "Analizini, bölümün bu bütün içindeki tutarlılığını gözeterek yap:\n\n"
                f"--- ROMAN TAM METNİ ---\n{cleaned_full_content}\n--- ROMAN TAM METNİ SONU ---\n\n"
            )
        elif novel_context:
            # Roman Kimliği (özet) kullanılıyorsa
            cleaned_novel_context = self._clean_content_for_ai(novel_context)
            context_section = (
                "Bu bölümün ait olduğu romanın genel bir özeti ('Roman Kimliği') aşağıdadır. "
                "Bu özeti, bölümdeki olayların ve karakterlerin romanın ana hatlarıyla tutarlı olup olmadığını kontrol etmek için üst düzey bir referans olarak kullan. "
                "Analizini bu özeti dikkate alarak yap:\n\n"
                f"--- ROMAN ÖZETİ ---\n{cleaned_novel_context}\n--- ROMAN ÖZETİ SONU ---\n\n"
            )

        # Prompt'u formatla
        # AI'ye göndermeden önce metindeki özel etiketleri temizle
        cleaned_content = self._clean_content_for_ai(content)
        # Not: consistency_check hala ayrı bir mantık kullanabilir, ancak şimdilik genel yapıya dahil edelim.
        prompt = prompt_template.format(content=cleaned_content, context_section=context_section)
        
        # Prompt'u dosyaya kaydet
        self._save_prompt_to_file(prompt, analysis_type)
            
        print(f"PROMPT HAZIRLANDI: {len(prompt)} karakter")
        
        # Dinamik timeout hesaplama - metin uzunluğuna göre
        timeout_seconds = self._calculate_timeout(content, analysis_type)
        max_retries = 2
        
        print(f"💡 Dinamik timeout hesaplandı: {timeout_seconds} saniye (Metin: {len(content)} karakter)")
        
        for attempt in range(max_retries):
            try:
                print(f"Google AI kütüphanesi yüklenmeye çalışılıyor... (Deneme {attempt + 1}/{max_retries})")
                import google.generativeai as genai  # type: ignore
                
                print(f"AI modeline prompt gönderiliyor... (Timeout: {timeout_seconds}s)")
                
                # Timeout ile AI isteği
                import signal
                import time
                
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"AI analizi {timeout_seconds} saniye sonra zaman aşımına uğradı")
                
                # Windows için timeout alternatifi
                start_time = time.time()
                response = None
                
                try:
                    # Threading ile timeout simülasyonu
                    import threading
                    
                    result = {'response': None, 'error': None}
                    
                    def ai_request():
                        try:
                            # Güvenlik ayarları artık modelin kendisinde yapılandırıldığı için
                            # burada tekrar belirtmeye gerek yok. Sadece generation_config yeterli.
                            generation_config = {
                                "temperature": 0.7,
                                "top_p": 0.95,
                                "top_k": 40
                            }
                            
                            result['response'] = model_instance.generate_content(
                                prompt,
                                generation_config=generation_config
                            )
                        except Exception as e:
                            result['error'] = e
                    
                    thread = threading.Thread(target=ai_request)
                    thread.daemon = True
                    thread.start()
                    thread.join(timeout=timeout_seconds)
                    
                    if thread.is_alive():
                        message = f"AI analizi {timeout_seconds} saniye sonra zaman aşımına uğradı. Lütfen internet bağlantınızı kontrol edin veya daha kısa bir metinle tekrar deneyin."
                        print(f"⚠️ {message}")
                        raise AIAnalysisError(message, error_type="timeout")

                    if result['error']:
                        raise result['error']

                    response = result['response']

                except Exception as e:
                    elapsed = time.time() - start_time
                    print(f"❌ AI istek hatası (Süre: {elapsed:.1f}s): {e}")

                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"🔄 {wait_time} saniye bekleyip tekrar denenecek...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"❌ Tüm denemeler başarısız oldu. Son hata: {e}")
                        error_message = str(e)
                        if "prompt_feedback" in error_message or "candidate" in error_message:
                            user_message = f"AI sorgusu güvenlik nedeniyle engellendi. Google AI, metninizi hassas içerik olarak değerlendirdi. Lütfen metni gözden geçirin. Sistem Detayı: {error_message[:100]}..."
                            raise AIAnalysisError(user_message, error_type="prompt_blocked", details=error_message)
                        
                        user_message = f"AI analizi sırasında bir hata oluştu. API ayarlarınızı kontrol edin. Sistem Detayı: {error_message[:150]}..."
                        raise AIAnalysisError(user_message, error_type="api_error", details=error_message)

                if not response:
                    print("HATA: AI'dan boş yanıt geldi")
                    if attempt >= max_retries - 1:
                        raise AIAnalysisError("AI'dan boş yanıt geldi. Servis geçici olarak kullanılamıyor olabilir.", error_type="empty_response")
                    continue

                # Engellenen prompt'u `response.text` erişiminden ÖNCE kontrol et
                if not response.candidates:
                    feedback_str = f"Prompt Geri Bildirimi: {getattr(response, 'prompt_feedback', 'N/A')}"
                    print(f"HATA: AI yanıtında aday bulunamadı. Muhtemelen prompt engellendi. {feedback_str}")
                    if attempt < max_retries - 1:
                        time.sleep((attempt + 1) * 2)
                        continue
                    else:
                        user_message = f"AI sorgusu güvenlik nedeniyle engellendi. Google AI, metninizi hassas içerik olarak değerlendirdi. Lütfen metni gözden geçirin. {feedback_str}"
                        raise AIAnalysisError(user_message, error_type="prompt_blocked", details=str(getattr(response, 'prompt_feedback', '')))

                if not hasattr(response, 'text') or not response.text:
                    print("HATA: AI yanıtında text bulunamadı")
                    if attempt < max_retries - 1:
                        continue
                    raise AIAnalysisError("AI yanıtı 'text' alanı olmadan geldi. Beklenmedik yanıt formatı.", error_type="invalid_response")
                
                elapsed = time.time() - start_time
                print(f"✅ AI YANITINI ALDI: {len(response.text)} karakter (Süre: {elapsed:.1f}s)")
                print(f"Yanıt önizleme: {response.text[:200]}...")
                
                # Yanıtı dosyaya kaydet
                self._save_response_to_file(response.text, analysis_type)
                
                # Update the model name in the suggestions
                suggestions = self.parse_ai_response(response.text, analysis_type)
                # Add model information to each suggestion
                for suggestion in suggestions:
                    suggestion["model_name"] = self.models.get(analysis_type, self.model_name)
                print(f"✅ PARSING TAMAMLANDI: {len(suggestions)} öneri oluşturuldu")
                
                return suggestions
                
            except AIAnalysisError:
                # Oluşturduğumuz özel hatayı tekrar fırlat, böylece çağıran modül yakalayabilir
                raise
            except ImportError as e:
                print(f"IMPORT HATASI: Google AI kütüphanesi yüklenemedi - {e}")
                raise AIAnalysisError(f"Google AI kütüphanesi ('google-generativeai') yüklenemedi. Lütfen 'pip install google-generativeai' komutuyla kurun. Hata: {e}", error_type="import_error")
            except Exception as e:
                print(f"AI ANALIZ HATASI (Genel): {str(e)}")
                print(f"Hata tipi: {type(e).__name__}")

                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    print(f"🔄 {wait_time} saniye bekleyip tekrar denenecek...")
                    time.sleep(wait_time)
                    continue
                else:
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"❌ Hata detayı: {error_details}")
                    error_message = str(e)

                    if "prompt_feedback" in error_message or "candidate" in error_message:
                        user_message = f"AI sorgusu güvenlik nedeniyle engellendi. Sistem Detayı: {error_message[:100]}..."
                        raise AIAnalysisError(user_message, error_type="prompt_blocked", details=error_details)
                    
                    user_message = f"AI analizi sırasında beklenmedik bir hata oluştu. Sistem Detayı: {error_message[:150]}..."
                    raise AIAnalysisError(user_message, error_type="unknown_error", details=error_details)
        
        # Bu satıra normalde ulaşılmamalı, ancak her ihtimale karşı bir hata fırlat
        raise AIAnalysisError("Tüm denemelerden sonra analiz tamamlanamadı.", error_type="retries_failed")

    def generate_summary(self, content: str, summary_type: str) -> str:
        """Verilen metin için bir özet oluşturur (örn: roman kimliği)."""
        print(f"AI ÖZET OLUŞTURMA BAŞLATILDI: Tip={summary_type}, İçerik uzunluğu={len(content)}")
        
        model_instance = self.model_instances.get(summary_type)
        if not model_instance:
            print(f"UYARI: {summary_type} için özel model bulunamadı, varsayılan model kullanılacak")
            model_instance = self.model

        if not model_instance:
            print("HATA: AI model yapılandırılmamış.")
            return ""

        prompt_template = self.prompts.get(summary_type)
        if not prompt_template:
            print(f"HATA: {summary_type} için özet prompt'u bulunamadı.")
            return ""

        # Metni temizle
        cleaned_content = self._clean_content_for_ai(content)
        prompt = prompt_template.format(content=cleaned_content)
        
        # Prompt'u ve yanıtı kaydet
        self._save_prompt_to_file(prompt, summary_type)
        
        try:
            import google.generativeai as genai
            print("AI modeline özet prompt'u gönderiliyor...")
            # Güvenlik ayarları artık modelin kendisinde yapılandırıldığı için
            # burada tekrar belirtmeye gerek yok.
            response = model_instance.generate_content(prompt)
            
            if response and hasattr(response, 'text') and response.text:
                print(f"✅ ÖZET ALINDI: {len(response.text)} karakter")
                self._save_response_to_file(response.text, summary_type)
                return response.text.strip()
            else:
                print("HATA: AI'dan boş özet yanıtı geldi.")
                return ""
        except Exception as e:
            print(f"AI ÖZET OLUŞTURMA HATASI: {e}")
            return ""
    
    
    def _calculate_timeout(self, content: str, analysis_type: str) -> int:
        """Metin uzunluğu ve analiz türüne göre dinamik timeout hesapla"""
        if not content:
            return 30
        
        # Kullanıcı ayarlarını kontrol et
        try:
            from .settings_manager import SettingsManager
            settings = SettingsManager()
            
            use_dynamic = settings.get_setting("use_dynamic_timeout", True)
            fixed_timeout = settings.get_setting("fixed_timeout", 120)
            
            # Eğer dinamik timeout kapalıysa sabit süreyi kullan
            if not use_dynamic:
                print(f"🕒 Sabit timeout kullanılıyor: {fixed_timeout} saniye")
                return max(30, fixed_timeout)  # En az 30 saniye
                
        except Exception as e:
            print(f"Ayarlar alınamıyor, varsayılan dinamik sistem kullanılıyor: {e}")
        
        content_length = len(content)
        
        # Temel timeout süreleri (saniye)
        base_timeouts = {
            "grammar_check": 60,      # Dil Bilgisi en hızlı
            "style_analysis": 90,     # Üslup orta hızda
            "content_review": 120,    # İçerik yavaş
            "consistency_check": 150  # Tutarlılık en yavaş
        }
        
        base_timeout = base_timeouts.get(analysis_type, 90)
        
        # Metin uzunluğuna göre ek süre hesapla
        # Her 1000 karakter için ek süre
        extra_seconds_per_1k = {
            "grammar_check": 5,       # Her 1K karakter için +5 saniye
            "style_analysis": 8,      # Her 1K karakter için +8 saniye
            "content_review": 12,     # Her 1K karakter için +12 saniye
            "consistency_check": 15   # Her 1K karakter için +15 saniye
        }
        
        extra_per_1k = extra_seconds_per_1k.get(analysis_type, 8)
        extra_time = (content_length // 1000) * extra_per_1k
        
        # Toplam timeout hesapla
        total_timeout = base_timeout + extra_time
        
        # Minimum ve maksimum sınırlar
        min_timeout = 45   # En az 45 saniye
        max_timeout = 600  # En fazla 10 dakika
        
        final_timeout = max(min_timeout, min(total_timeout, max_timeout))
        
        print(f"📊 Dinamik timeout hesaplama:")
        print(f"   📝 Metin: {content_length:,} karakter")
        print(f"   ⚙️ Analiz: {analysis_type}")
        print(f"   ⏱️ Temel süre: {base_timeout}s")
        print(f"   ➕ Ek süre: {extra_time}s ({content_length // 1000}K x {extra_per_1k}s)")
        print(f"   ⏰ Toplam timeout: {final_timeout}s ({final_timeout // 60}dk {final_timeout % 60}s)")
        
        return final_timeout
    
    def parse_ai_response(self, response_text: str, analysis_type: str) -> List[Dict]:
        """AI yanıtını yapılandırılmış önerilere çevir - JSON format destekli"""
        suggestions = []
        
        print(f"JSON PARSING BAŞLATILDI: {len(response_text)} karakter")
        print(f"Yanıt içeriği önizleme: {response_text[:300]}...")
        
        try:
            # Önce direkt JSON parse deneme
            import json
            try:
                # JSON formatindaki yanıtı parse et
                # Bazen AI öncesinde ve sonrasında açıklama yazıyor, sadece JSON kısmını al
                json_start = response_text.find('[')
                json_end = response_text.rfind(']') + 1
                
                if json_start != -1 and json_end != -1:
                    json_text = response_text[json_start:json_end]
                    print(f"JSON kısmı bulundu: {len(json_text)} karakter")
                    
                    # Control karakterleri temizle - JSON parsing hatalarını önle
                    json_text_cleaned = self._clean_json_control_chars(json_text)
                    print(f"JSON temizlendi: {len(json_text_cleaned)} karakter")
                    
                    # JSON'dan sonra gelen fazladan verileri kaldır - "Extra data" hatasını önle
                    json_text_cleaned = self._remove_extra_json_data(json_text_cleaned)
                    print(f"Fazladan veri temizlendi: {len(json_text_cleaned)} karakter")
                    
                    ai_suggestions_list = json.loads(json_text_cleaned)
                    
                    if isinstance(ai_suggestions_list, list):
                        for i, ai_suggestion in enumerate(ai_suggestions_list, 1):
                            if isinstance(ai_suggestion, dict):
                                # Zorunlu alanları kontrol et
                                original = ai_suggestion.get('original_sentence', '').strip()
                                suggested = ai_suggestion.get('suggested_sentence', '').strip()
                                explanation = ai_suggestion.get('explanation', 'Açıklama bulunamadı').strip()
                                
                                # Gereksiz önerileri filtrele
                                if self._is_useless_suggestion(original, suggested, explanation):
                                    print(f"GEREKSİZ ÖNERİ ATLANDI: '{original[:50]}...' = '{suggested[:50]}...'")
                                    continue
                                
                                if original and suggested:
                                    # Geçerli önerilerin sayısına göre doğru numara ver
                                    actual_suggestion_number = len(suggestions) + 1
                                    
                                    suggestion = {
                                        'id': f"{analysis_type}_{actual_suggestion_number}",
                                        'type': analysis_type,
                                        'title': f"{actual_suggestion_number}. Öneri",
                                        'original_sentence': original,
                                        'suggested_sentence': suggested,
                                        'explanation': explanation,
                                        'description': f"Orijinal: {original}\n\nÖnerilen: {suggested}\n\nAçıklama: {explanation}",
                                        'severity': ai_suggestion.get('severity', 'medium'),
                                        'location': original[:30] + "...",
                                        'suggested_fix': suggested,
                                        'editor_type': ai_suggestion.get('editor_type', self.get_editor_name(analysis_type)),
                                        'model_name': self.model_name
                                    }
                                    
                                    suggestions.append(suggestion)
                                    print(f"JSON önerisi eklendi: {actual_suggestion_number} - Açıklama: {explanation[:50]}...")
                    
                    print(f"JSON PARSING TAMAMLANDI: {len(suggestions)} öneri oluşturuldu")
                    return suggestions
                    
                else:
                    print("JSON formatı bulunamadı, eski parsing yöntemine geçiliyor...")
                    
            except json.JSONDecodeError as e:
                print(f"JSON parse hatası: {e}")
                print("Eski metin parsing yöntemine geçiliyor...")
                
        except Exception as e:
            print(f"JSON parsing genel hatası: {e}")
            print("Eski metin parsing yöntemine geçiliyor...")
        
        # JSON parsing başarısız olursa eski yönteme geri dön
        return self._parse_text_response(response_text, analysis_type)
    
    def _parse_text_response(self, response_text: str, analysis_type: str) -> List[Dict]:
        """Eski metin tabanlı parsing yöntemi - yedek olarak kullanılır"""
        suggestions = []
        
        print(f"METIN PARSING BAŞLATILDI: {len(response_text)} karakter")
        
        # Her satırı kontrol et ve öneri formatlarını bul
        lines = response_text.split('\n')
        current_suggestion = {}
        suggestion_counter = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            line_lower = line.lower()
            print(f"Satır {i}: {line[:100]}...")
            
            # Yeni öneri başlangıcı tespiti
            is_new_suggestion_start = False
                
            # JSON format benzeri tespiti - daha esnek
            if ('"original_sentence"' in line and ':' in line) or ('original_sentence' in line_lower and ':' in line):
                # Eğer önceki öneri tamamsa kaydet
                if (current_suggestion.get('original_sentence') and 
                    current_suggestion.get('suggested_sentence')):
                    self._save_current_suggestion(current_suggestion, suggestions, suggestion_counter + 1, analysis_type)
                    suggestion_counter += 1
                    current_suggestion = {}  # Reset
                
                original_text = self.extract_quoted_text(line)
                if not original_text:  # Tırnak yoksa JSON değerini al
                    if '"original_sentence":' in line:
                        # JSON format: "original_sentence": "metin burada"
                        parts = line.split('"original_sentence":', 1)
                        if len(parts) > 1:
                            value_part = parts[1].strip()
                            # Tırnak içindeki değeri al
                            if value_part.startswith('"'):
                                end_quote = value_part.find('"', 1)
                                if end_quote != -1:
                                    original_text = value_part[1:end_quote]
                
                if original_text:
                    current_suggestion['original_sentence'] = original_text
                    print(f"JSON format - Orijinal cümle bulundu: {original_text[:50]}...")
                is_new_suggestion_start = True
                
            # suggested_sentence tespiti - JSON format
            elif ('"suggested_sentence"' in line and ':' in line) or ('suggested_sentence' in line_lower and ':' in line):
                suggested_text = self.extract_quoted_text(line)
                if not suggested_text:  # Tırnak yoksa JSON değerini al
                    if '"suggested_sentence":' in line:
                        parts = line.split('"suggested_sentence":', 1)
                        if len(parts) > 1:
                            value_part = parts[1].strip()
                            if value_part.startswith('"'):
                                end_quote = value_part.find('"', 1)
                                if end_quote != -1:
                                    suggested_text = value_part[1:end_quote]
                
                if suggested_text:
                    current_suggestion['suggested_sentence'] = suggested_text
                    print(f"JSON format - Düzeltme bulundu: {suggested_text[:50]}...")
                    
            # explanation tespiti - JSON format
            elif ('"explanation"' in line and ':' in line) or ('explanation' in line_lower and ':' in line):
                explanation = self.extract_quoted_text(line)
                if not explanation:  # Tırnak yoksa JSON değerini al
                    if '"explanation":' in line:
                        parts = line.split('"explanation":', 1)
                        if len(parts) > 1:
                            value_part = parts[1].strip()
                            if value_part.startswith('"'):
                                end_quote = value_part.find('"', 1)
                                if end_quote != -1:
                                    explanation = value_part[1:end_quote]
                
                if explanation:
                    # JSON metadata temizle
                    explanation = self._clean_explanation_metadata(explanation)
                    current_suggestion['explanation'] = explanation
                    print(f"JSON format - Açıklama bulundu: {explanation[:50]}...")
            
            # Açıklama tespiti - SADECE mevcut öneriye ait olan açıklama
            elif ("kural:" in line_lower or "açıklama:" in line_lower or 
                  "neden:" in line_lower or "sebebi:" in line_lower or
                  "kural açıklaması:" in line_lower or "çünkü" in line_lower or
                  "gerekçe:" in line_lower or "sebep:" in line_lower or
                  line_lower.startswith("bu hata") or line_lower.startswith("bu yanlış")):
                
                # Sadece mevcut öneride orijinal ve önerilen cümle varsa açıklama ekle
                if (current_suggestion.get('original_sentence') and 
                    current_suggestion.get('suggested_sentence')):
                    
                    explanation = line.split(":", 1)[-1].strip()
                    if not explanation:  # : yoksa tüm satırı al
                        explanation = line.strip()
                    
                    # Mevcut açıklamaya ekle (birden fazla satır olabilir)
                    if explanation:
                        existing_explanation = current_suggestion.get('explanation', '')
                        if existing_explanation:
                            current_suggestion['explanation'] = f"{existing_explanation} {explanation}"
                        else:
                            current_suggestion['explanation'] = explanation
                        print(f"Açıklama bulundu: {explanation[:100]}...")
            
            # Açıklama devamı - SADECE önceki satırda açıklama varsa VE yeni öneri başlamıyorsa
            elif (not is_new_suggestion_start and
                  current_suggestion.get('explanation') and
                  current_suggestion.get('original_sentence') and
                  current_suggestion.get('suggested_sentence') and
                  '":"' not in line and  # YENİ KURAL: JSON key-value çifti gibi görünen satırları ekleme
                  not any(keyword in line_lower for keyword in ['hata:', 'doğru:', 'yanlış:', 'öneri:', 'orijinal:', 'mevcut:', 'düzeltme:']) and
                  len(line) > 10):  # Kısa satırları geç
                current_suggestion['explanation'] += f" {line.strip()}"
                print(f"Açıklama devamı: {line[:50]}...")
        
        # Son öneri için kontrol (dosya sonunda kalan)
        if (current_suggestion.get('original_sentence') and 
            current_suggestion.get('suggested_sentence')):
            self._save_current_suggestion(current_suggestion, suggestions, suggestion_counter + 1, analysis_type)
        
        print(f"PARSING TAMAMLANDI: {len(suggestions)} öneri oluşturuldu")
        
        # Debug için her önerinin açıklamasını kontrol et
        for i, suggestion in enumerate(suggestions, 1):
            print(f"Öneri {i} açıklama: {suggestion['explanation'][:100]}...")
        
        # Eğer hiç öneri oluşmadıysa detaylı debug yap
        if len(suggestions) == 0:
            print("\n⚠️ DEBUG: Hiç öneri oluşturulamadı. Muhtemel sebepler:")
            print("   1. Tüm öneriler 'hata yok' açıklaması nedeniyle filtrelendi")
            print("   2. Orijinal ve önerilen cümleler aynıydı")
            print("   3. Severity 'low' veya 'null' olan öneriler filtrelendi")
            print("   4. Text parsing formatı yanlış tanındı")
            print("\n🔍 Öneri formatı kontrolü:")
            
            # İlk birkaç satırı göster
            lines = response_text.split('\n')[:20]
            for i, line in enumerate(lines):
                if line.strip():
                    print(f"   Satır {i}: {line[:100]}...")
        
        return suggestions
    
    def _save_current_suggestion(self, current_suggestion: Dict, suggestions: List, suggestion_number: int, analysis_type: str):
        """Mevcut öneriyi kaydet - Gereksiz önerileri filtrele ve numaraları düzelt"""
        original = current_suggestion.get('original_sentence', '').strip()
        suggested = current_suggestion.get('suggested_sentence', '').strip()
        explanation = current_suggestion.get('explanation', 'Detaylı açıklama bulunamadı').strip()
        
        # Gereksiz önerileri filtrele
        if self._is_useless_suggestion(original, suggested, explanation):
            print(f"GEREKSİZ ÖNERİ ATLANDI: '{original[:50]}...' = '{suggested[:50]}...'")
            return
        
        # Geçerli önerilerin sayısına göre doğru numara ver
        actual_suggestion_number = len(suggestions) + 1
        
        suggestion = {
            'id': f"{analysis_type}_{actual_suggestion_number}",
            'type': analysis_type,
            'title': f"{actual_suggestion_number}. Öneri",
            'original_sentence': original,
            'suggested_sentence': suggested,
            'explanation': explanation,
            'description': f"Orijinal: {original}\n\nÖnerilen: {suggested}\n\nAçıklama: {explanation}",
            'severity': 'medium',
            'location': original[:30] + "...",
            'suggested_fix': suggested,
            'editor_type': self.get_editor_name(analysis_type),
            'model_name': self.model_name
        }
        
        suggestions.append(suggestion)
        print(f"Geçerli öneri eklendi: {actual_suggestion_number} - Açıklama: {explanation[:50]}...")
    
    def _is_useless_suggestion(self, original: str, suggested: str, explanation: str) -> bool:
        """Basitleştirilmiş öneri kontrolü - Sadece aynı metinleri filtrele"""
        # Boş veya çok kısa metinler
        if not original or not suggested or len(original.strip()) < 3 or len(suggested.strip()) < 3:
            return True
            
        # Aynı metinler (whitespace temizleyerek)
        original_clean = ' '.join(original.strip().split())
        suggested_clean = ' '.join(suggested.strip().split())
        
        if original_clean == suggested_clean:
            print(f"GEREKSİZ ÖNERİ FİLTRELENDİ (aynı metin): '{original[:50]}...' = '{suggested[:50]}...'")
            return True
            
        # DIĞER TÜM ÖNERİLERİ KABUL ET!
        print(f"GEÇERLİ ÖNERİ KABUL EDİLDİ: '{original[:30]}...' -> '{suggested[:30]}...'")
        return False
    
    def get_editor_name(self, analysis_type: str) -> str:
        """Analiz tipine göre editör adını döndür"""
        editor_names = {
            'grammar_check': 'Dil Bilgisi Editörü',
            'style_analysis': 'Üslup Editörü',
            'content_review': 'İçerik Editörü',
            'consistency_check': 'Tutarlılık Editörü',
            'custom': 'Özel Editör'
        }
        return editor_names.get(analysis_type, 'Bilinmeyen Editör')
    
    def extract_quoted_text(self, text: str) -> str:
        """Metin içinden tırnak içindeki kısmı çıkar - Gelişmiş pattern'ler ile"""
        # Tırnak iŞaretleri içinde içerik varsa bile tam metni al
        
        # Çift tırnak işaretleri arasındaki metni bul - En uzun eşleşmeyi tercih et
        if '"' in text:
            quote_positions = [i for i, char in enumerate(text) if char == '"']
            if len(quote_positions) >= 2:
                # En uzun tırnak arası metni bul
                longest_content = ""
                for i in range(0, len(quote_positions) - 1, 2):
                    start = quote_positions[i] + 1
                    end = quote_positions[i + 1]
                    content = text[start:end].strip()
                    if len(content) > len(longest_content):
                        longest_content = content
                if longest_content:
                    return longest_content
        
        # Tek tırnak işaretleri - aynı mantık
        if "'" in text:
            quote_positions = [i for i, char in enumerate(text) if char == "'"]
            if len(quote_positions) >= 2:
                longest_content = ""
                for i in range(0, len(quote_positions) - 1, 2):
                    start = quote_positions[i] + 1
                    end = quote_positions[i + 1]
                    content = text[start:end].strip()
                    if len(content) > len(longest_content):
                        longest_content = content
                if longest_content:
                    return longest_content
        
        # Türkçe tırnak işaretleri
        if "“" in text and "”" in text:
            start = text.find("“")
            end = text.find("”", start + 1)
            if end != -1:
                return text[start + 1:end].strip()
        
        # Bold işaretleri arasındaki metin
        if "**" in text:
            parts = text.split("**")
            for i, part in enumerate(parts):
                if i % 2 == 1 and part.strip() and len(part.strip()) > 3:  # Bold içindeki metin
                    return part.strip()
        
        # Eğer tırnak yoksa, ": " sonrasını al - ama daha dikkatli
        if ": " in text:
            after_colon = text.split(": ", 1)[1].strip()
            # Kısa ve anlamlı metin kontrolü - daha geniş kabul
            if len(after_colon) > 2:
                return after_colon
        
        # Son çare: satırın kendisi (eğer yeterince uzun ise)
        text_clean = text.strip()
        if len(text_clean) > 5 and not any(char in text_clean for char in ['*', '#', '-', '=']):
            return text_clean
        
        return ""
    
    def extract_title(self, text: str) -> str:
        """Metinden başlık çıkar"""
        lines = text.split('\n')
        first_line = lines[0].strip()
        
        # İlk satırı başlık olarak kullan, maksimum 50 karakter
        if len(first_line) > 50:
            return first_line[:47] + "..."
        return first_line
    
    def determine_severity(self, text: str) -> str:
        """Önerinin önem derecesini belirle"""
        high_keywords = ['hata', 'yanlış', 'çelişki', 'sorun', 'problem']
        medium_keywords = ['öneri', 'geliştirilmeli', 'iyileştir']
        
        text_lower = text.lower()
        
        for keyword in high_keywords:
            if keyword in text_lower:
                return 'high'
        
        for keyword in medium_keywords:
            if keyword in text_lower:
                return 'medium'
        
        return 'low'
    
    def extract_location(self, text: str) -> str:
        """Önerinin konumunu çıkarmaya çalış"""
        # Bu basit bir implementasyon, daha gelişmiş NLP teknikleri kullanılabilir
        if '"' in text:
            start = text.find('"')
            end = text.find('"', start + 1)
            if end != -1:
                return text[start:end+1]
        
        return "Genel"
    
    def extract_suggestion(self, text: str) -> str:
        """Önerinin çözüm kısmını çıkar"""
        # Çözüm önerisi içeren anahtar kelimeler
        suggestion_markers = ['öneri:', 'çözüm:', 'düzeltme:', 'iyileştirme:']
        
        text_lower = text.lower()
        for marker in suggestion_markers:
            if marker in text_lower:
                index = text_lower.find(marker)
                return text[index + len(marker):].strip()
        
        # Özel marker bulunamazsa son cümleyi kullan
        sentences = text.split('.')
        if len(sentences) > 1:
            return sentences[-2].strip() + '.'
        
        return text.strip()
    
    def custom_analysis(self, content: str, custom_prompt: str) -> List[Dict]:
        """Özel prompt ile analiz yap"""
        if not self.model or not content or not custom_prompt:
            return []
        
        full_prompt = f"{custom_prompt}\n\nMetin bölümü:\n{content}"
        
        try:
            # Google AI import'u burada yapılıyor
            import google.generativeai as genai  # type: ignore
            response = self.model.generate_content(full_prompt)
            suggestions = self.parse_ai_response(response.text, "custom")
            return suggestions
        
        except ImportError:
            print("Google AI kütüphanesi yüklenemedi. 'py -m pip install google-generativeai' komutuyla yükleyin.")
            return []
        except Exception as e:
            print(f"Özel analiz hatası: {e}")
            return []
    
    def update_prompts(self, new_prompts: Dict[str, str]):
        """Prompt'ları bir sözlükten toplu olarak güncelle."""
        self.prompts = new_prompts.copy()
    
    def update_prompt(self, prompt_type: str, new_prompt: str):
        """Prompt güncelle"""
        self.prompts[prompt_type] = new_prompt
    
    def get_prompts(self) -> Dict[str, str]:
        """Mevcut promptları döndür"""
        return self.prompts.copy()
    
    def save_prompts(self, file_path: str):
        """Promptları dosyaya kaydet"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(self.prompts, file, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Prompt kaydetme hatası: {e}")
            return False
    
    def load_prompts(self, file_path: str):
        """Promptları dosyadan yükle"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.prompts = json.load(file)
            return True
        except Exception as e:
            print(f"Prompt yükleme hatası: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Kullanılabilir modelleri döndür"""
        return [
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
            "gemini-pro",
            "gemini-pro-vision",
            "gemini-2.0-flash",
            "gemini-2.0-flash-8b",
            "gemini-2.0-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-8b",
            "gemini-2.5-pro"
        ]
    
    def _clean_explanation_metadata(self, explanation: str) -> str:
        """Açıklamalardan JSON metadata temizle"""
        # JSON alanlarını kaldır
        import re
        
        # "editor_type": "...", "severity": "..." gibi kısımları kaldır
        cleaned = re.sub(r'"\w+":\s*"[^"]*"[,\s]*', '', explanation)
        
        # Küçük harfle başlayan JSON field'ları da kaldır
        cleaned = re.sub(r'"[a-z_]+":\s*"[^"]*"[,\s]*', '', cleaned)
        
        # Fazla virgül ve boşlukları temizle
        cleaned = re.sub(r'[,\s]+$', '', cleaned.strip())
        cleaned = re.sub(r'^[,\s]+', '', cleaned)
        
        return cleaned.strip()
    
    def _remove_extra_json_data(self, json_text: str) -> str:
        """JSON'dan sonra gelen fazladan verileri temizle"""
        try:
            # JSON'un son ] karakterini bul
            last_bracket = json_text.rfind(']')
            
            if last_bracket == -1:
                return json_text
            
            # Son ] karakterinden sonra gelen herşeyi kaldır
            clean_json = json_text[:last_bracket + 1]
            
            # Öncesinde de gereksiz karakterler olabilir, ilk [ öncesini temizle
            first_bracket = clean_json.find('[')
            if first_bracket > 0:
                clean_json = clean_json[first_bracket:]
            
            print(f"Fazladan veri temizleme: {len(json_text)} -> {len(clean_json)} karakter")
            return clean_json
            
        except Exception as e:
            print(f"Fazladan veri temizleme hatası: {e}")
            return json_text
    
    def _clean_json_control_chars(self, json_text: str) -> str:
        """JSON string içindeki control karakterleri temizle"""
        import re
        
        print("Control karakter temizleme başlatılıyor...")
        
        # Önce basit control karakterleri düz metin olarak temizle
        # JSON string'leri içinde olabilecek escape edilmemiş karakterler
        
        # Problematik control karakterleri bul ve çıkar/değiştir
        # ASCII control characters (0-31 except allowed ones)
        control_chars = {
            '\x00': '',  # NULL
            '\x01': '',  # SOH
            '\x02': '',  # STX
            '\x03': '',  # ETX
            '\x04': '',  # EOT
            '\x05': '',  # ENQ
            '\x06': '',  # ACK
            '\x07': '',  # BEL
            '\x08': '',  # BS
            '\x0B': '',  # VT (Vertical Tab)
            '\x0C': '',  # FF (Form Feed)
            '\x0E': '',  # SO
            '\x0F': '',  # SI
            '\x10': '',  # DLE
            '\x11': '',  # DC1
            '\x12': '',  # DC2
            '\x13': '',  # DC3
            '\x14': '',  # DC4
            '\x15': '',  # NAK
            '\x16': '',  # SYN
            '\x17': '',  # ETB
            '\x18': '',  # CAN
            '\x19': '',  # EM
            '\x1A': '',  # SUB
            '\x1B': '',  # ESC
            '\x1C': '',  # FS
            '\x1D': '',  # GS
            '\x1E': '',  # RS
            '\x1F': '',  # US
            '\x7F': '',  # DEL
        }
        
        # Karakterleri temizle
        cleaned_text = json_text
        for char, replacement in control_chars.items():
            if char in cleaned_text:
                cleaned_text = cleaned_text.replace(char, replacement)
                print(f"Control karakter temizlendi: {repr(char)}")
        
        # Unicode ve diğer problematik karakterleri temizle
        # Unicode control karakterleri ve emoji gibi sorun çıkaran karakterler
        unicode_control_pattern = r'[\u0000-\u001F\u007F-\u009F\u2000-\u200F\u2028-\u202F\u2060-\u206F\uFEFF]'
        cleaned_text = re.sub(unicode_control_pattern, '', cleaned_text)
        
        # Problematik karakterleri daha fazla temizle
        problematic_chars = {
            '♥': '',  # Heart symbol (♥)
            '♠': '',  # Spade symbol (♠)
            '♦': '',  # Diamond symbol (♦)
            '♣': '',  # Club symbol (♣)
            ' ': ' ', # Non-breaking space
            '​': '',  # Zero-width space
            '‌': '',  # Zero-width non-joiner
            '‍': '',  # Zero-width joiner
            '﻿': '',  # Byte order mark
        }
        
        for char, replacement in problematic_chars.items():
            if char in cleaned_text:
                cleaned_text = cleaned_text.replace(char, replacement)
                print(f"Problematik karakter temizlendi: {repr(char)}")
        
        # JSON string format problemlerini düzelt
        # Problemli çift tırnak durumlarını düzelt
        # ""text"" -> "text" formatında düzelt
        cleaned_text = re.sub(r'""([^"]+)""', r'"\1"', cleaned_text)
        
        # Eksik veya fazla tırnak problemlerini çöz
        # "text" -> "text" (missing closing quote)
        lines = cleaned_text.split('\n')
        fixed_lines = []
        
        for line in lines:
            # JSON string alanlarındaki tırnak sorunlarını düzelt
            if ':' in line and '"' in line:
                # "key": "value" formatını kontrol et
                if line.strip().endswith(',') or line.strip().endswith('}') or line.strip().endswith(']'):
                    # Satır sonu karakterini koru - Fixed string slicing
                    line_stripped = line.rstrip()
                    line_end = line[len(line_stripped):]
                    line_content = line_stripped
                    
                    # Tırnak sayma ve düzeltme
                    quote_count = line_content.count('"')
                    if quote_count % 2 == 1:  # Tek sayıda tırnak varsa
                        # Son tırnağı ekle
                        if line_content.endswith('"'):
                            pass  # Zaten doğru
                        else:
                            # Value kısmına closing quote ekle
                            if ':' in line_content:
                                key_part, value_part = line_content.rsplit(':', 1)
                                value_part = value_part.strip()
                                if value_part.startswith('"') and not value_part.endswith('"'):
                                    if value_part.endswith(','):
                                        value_part = value_part[:-1] + '"'
                                        line_content = key_part + ': ' + value_part + ','
                                    else:
                                        value_part = value_part + '"'
                                        line_content = key_part + ': ' + value_part
                    
                    fixed_lines.append(line_content + line_end)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        final_text = '\n'.join(fixed_lines)
        
        print(f"Control karakter temizleme tamamlandı: {len(json_text)} -> {len(final_text)} karakter")
        
        return final_text
    
    def _clean_content_for_ai(self, text: str) -> str:
        """Metni AI'ye göndermeden önce özel biçimlendirme etiketlerini temizler."""
        if not text:
            return ""
        # Tüm biçimlendirme etiketlerini kaldır
        # Kalın, italik, altı çizili
        cleaned_text = re.sub(r'\*[BIU]\*(.*?)\*[BIU]\*', r'\1', text)
        # Başlık
        cleaned_text = re.sub(r'###(.*?)###', r'\1', cleaned_text)
        # Hizalama
        cleaned_text = re.sub(r'\{(.*?)\}', r'\1', cleaned_text)
        cleaned_text = re.sub(r'>>>(.*?)<<<', r'\1', cleaned_text)
        # Diğer özel formatlar
        cleaned_text = re.sub(r'\{\*.*?\*\}', '', cleaned_text)
        print(f"Metin temizlendi: {len(text)} -> {len(cleaned_text)} karakter (özel etiketler kaldırıldı)")
        return cleaned_text

    def test_connection(self) -> bool:
        """AI bağlantısını test et"""
        if not self.model:
            print("Model henüz yapılandırılmadı.")
            return False
        
        try:
            # Google AI import'u burada yapılıyor
            import google.generativeai as genai  # type: ignore
            
            # Basit bir test prompt'u gönder
            test_prompt = "Bu bir bağlantı testidir. Lütfen 'Bağlantı başarılı' şeklinde kısa bir yanıt verin."
            response = self.model.generate_content(test_prompt)
            
            # Yanıt geldiğini kontrol et
            if response and hasattr(response, 'text') and response.text:
                print(f"Bağlantı test edildi. Yanıt: {response.text[:50]}...")
                return True
            else:
                print("Bağlantı kuruldu ancak boş yanıt alındı.")
                return False
                
        except ImportError:
            print("Google AI kütüphanesi yüklenemedi.")
            return False
        except Exception as e:
            error_msg = str(e)
            if "API_KEY_INVALID" in error_msg:
                print("API anahtarı geçersiz.")
            elif "PERMISSION_DENIED" in error_msg:
                print("API anahtarı izinleri yetersiz.")
            elif "QUOTA_EXCEEDED" in error_msg:
                print("API kullanım limitiniz aşıldı.")
            elif "BLOCKED" in error_msg:
                print("Sorgu engellenmiş.")
            else:
                print(f"Bağlantı test hatası: {e}")
            return False

    def _save_prompt_to_file(self, prompt: str, analysis_type: str):
        """Oluşturulan prompt'u bir dosyaya kaydeder."""
        try:
            project_path = self.settings_manager.get_setting('last_project')
            if not project_path:
                print("Prompt kaydetmek için aktif proje bulunamadı.")
                return

            project_dir = os.path.dirname(project_path)
            prompts_dir = os.path.join(project_dir, "Prompts")
            os.makedirs(prompts_dir, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{analysis_type}_{timestamp}.txt"
            filepath = os.path.join(prompts_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(prompt)
            
            print(f"Prompt başarıyla kaydedildi: {filepath}")

        except Exception as e:
            print(f"Prompt dosyaya kaydedilirken hata oluştu: {e}")

    def _save_response_to_file(self, response: str, analysis_type: str):
        """AI'dan gelen yanıtı bir dosyaya kaydeder."""
        try:
            project_path = self.settings_manager.get_setting('last_project')
            if not project_path:
                print("Yanıtı kaydetmek için aktif proje bulunamadı.")
                return

            project_dir = os.path.dirname(project_path)
            responses_dir = os.path.join(project_dir, "Responses")
            os.makedirs(responses_dir, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{analysis_type}_response_{timestamp}.txt"
            filepath = os.path.join(responses_dir, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(response)
            
            print(f"Yanıt başarıyla kaydedildi: {filepath}")

        except Exception as e:
            print(f"Yanıt dosyaya kaydedilirken hata oluştu: {e}")
