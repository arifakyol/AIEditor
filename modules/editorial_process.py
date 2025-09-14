from typing import Dict, List, Optional
import json
import datetime
from .file_manager import Chapter
from .ai_integration import AIAnalysisError

class EditorialSuggestion:
    def __init__(self, suggestion_id: str, suggestion_type: str, title: str, 
                 description: str, severity: str, location: str, suggested_fix: str):
        self.id = suggestion_id
        self.type = suggestion_type
        self.title = title
        self.description = description
        self.severity = severity
        self.location = location
        self.suggested_fix = suggested_fix
        self.status = "pending"  # pending, accepted, rejected, applied
        self.timestamp = datetime.datetime.now().isoformat()
        self.notes = ""
        
        # Yeni alanlar - daha yapılandırılmış format için
        self.original_sentence = ""
        self.suggested_sentence = ""
        self.explanation = ""
        self.editor_type = ""
        self.model_name = ""
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'title': self.title,
            'description': self.description,
            'severity': self.severity,
            'location': self.location,
            'suggested_fix': self.suggested_fix,
            'status': self.status,
            'timestamp': self.timestamp,
            'notes': self.notes,
            'original_sentence': getattr(self, 'original_sentence', ''),
            'suggested_sentence': getattr(self, 'suggested_sentence', ''),
            'explanation': getattr(self, 'explanation', ''),
            'editor_type': getattr(self, 'editor_type', ''),
            'model_name': getattr(self, 'model_name', '')
        }
    
    @classmethod
    def from_dict(cls, data):
        # severity alanı için güvenli bir varsayılan değer sağla
        severity = data.get('severity', 'medium')
        if not severity or not isinstance(severity, str):
            severity = 'medium'

        suggestion = cls(
            data.get('id', ''), data.get('type', ''), data.get('title', ''), 
            data.get('description', ''), severity, data.get('location', ''), 
            data.get('suggested_fix', '')
        )
        suggestion.status = data.get('status', 'pending')
        suggestion.timestamp = data.get('timestamp', datetime.datetime.now().isoformat())
        suggestion.notes = data.get('notes', '')
        suggestion.original_sentence = data.get('original_sentence', '')
        suggestion.suggested_sentence = data.get('suggested_sentence', '')
        suggestion.explanation = data.get('explanation', '')
        suggestion.editor_type = data.get('editor_type', '')
        suggestion.model_name = data.get('model_name', '')
        return suggestion

class EditorialProcess:
    def __init__(self):
        self.current_chapter = 1
        self.processed_chapters = set()
        self.all_suggestions = {}  # chapter_number -> List[EditorialSuggestion]
        self.editorial_log = []
        self.workflow_settings = {
            'auto_grammar_check': True,
            'auto_style_analysis': True,
            'auto_content_review': True,  # İçerik analizini de aktif yap
            'auto_consistency_check': True, # Bütünlük kontrolü için yeni editör
            'require_approval': True,
            'auto_apply_critical': False,  # Kritik önerileri otomatik uygula
            'sequential_editing': False    # Sıralı editiryal analiz - hepsini birden yap
        }
        self.novel_context = "" # Romanın genel bağlamını tutmak için
    
    def reset_state(self):
        """Resets the editorial process to its initial state."""
        self.current_chapter = 1
        self.processed_chapters = set()
        self.all_suggestions = {}
        self.editorial_log = []
        self.novel_context = ""
        print("EditorialProcess state has been reset.")

    def analyze_text_snippet(self, text_snippet: str, ai_integration, analysis_type: str, novel_context: Optional[str] = None, full_novel_content: Optional[str] = None) -> List[EditorialSuggestion]:
        """Mevcut analiz yapısını kullanarak küçük bir metin parçasını analiz eder."""
        if not text_snippet or not text_snippet.strip():
            print("HATA: Analiz edilecek metin parçası boş.")
            return []
        
        if not ai_integration:
            print("HATA: AI entegrasyon nesnesi None")
            return []

        print(f"METİN PARÇASI ANALİZİ BAŞLATILDI: Tür: {analysis_type}, Uzunluk: {len(text_snippet)}")

        try:
            phase_name = {"grammar_check": "Dil Bilgisi"}.get(analysis_type, analysis_type)
            
            # MEVCUT ANALİZ YAPISINI YENİDEN KULLAN
            # ai_integration.analyze_chapter fonksiyonunu metin parçası ve bağlam ile çağır.
            ai_suggestions = ai_integration.analyze_chapter(
                content=text_snippet, 
                analysis_type=analysis_type,
                novel_context=novel_context,
                full_novel_content=full_novel_content
            )
            
            print(f"{phase_name} analizi tamamlandı: {len(ai_suggestions) if ai_suggestions else 0} öneri")
            
            if ai_suggestions:
                converted_suggestions = self.convert_to_editorial_suggestions(ai_suggestions)
                print(f"✅ {phase_name} önerileri eklendi: {len(converted_suggestions)} geçerli öneri")
                return converted_suggestions
            else:
                print(f"⚠️ {phase_name} analizinden hiç öneri gelmedi!")
                return []

        except AIAnalysisError:
            # Hata oluşursa, hatayı yukarıya (AnalysisManager'a) bildir
            raise
        except Exception as e:
            print(f"METİN PARÇASI ANALİZ HATASI: {str(e)}")
            import traceback
            print(f"Hata detayı: {traceback.format_exc()}")
            raise AIAnalysisError(f"Metin parçası analizi sırasında beklenmedik bir hata oluştu: {e}", error_type="system_error")

    def analyze_chapter_single_phase(self, chapter: Chapter, ai_integration, analysis_type: str, novel_context: Optional[str] = None, full_novel_content: Optional[str] = None) -> List[EditorialSuggestion]:
        """Tek faz analizi yap - sıralı editöryal süreç için (genel bağlam ile)"""
        if not chapter:
            print("HATA: Chapter objesi None")
            return []
            
        if not ai_integration:
            print("HATA: AI integration objesi None")
            return []
            
        if not chapter.content or len(chapter.content.strip()) == 0:
            print("HATA: Bölüm içeriği boş")
            return []
        
        print(f"TEK FAZ ANALİZ BAŞLATILDI: Bölüm {chapter.chapter_number}, Tür: {analysis_type}")
        print(f"İçerik uzunluğu: {len(chapter.content)} karakter")
        
        suggestions = []
        
        try:
            # Sadece belirtilen analiz türünü yap
            phase_name = {
                "grammar_check": "Dil Bilgisi",
                "style_analysis": "Üslup",
                "content_review": "İçerik"
            }.get(analysis_type, analysis_type)
            
            print(f"\n📝 === {phase_name.upper()} ANALİZİ BAŞLIYOR ===")
            
            # AI analizi yap
            ai_suggestions = ai_integration.analyze_chapter(
                chapter.content, 
                analysis_type, 
                novel_context, 
                full_novel_content if analysis_type in ["style_analysis", "content_review", "grammar_check"] else None
            )
            
            print(f"{phase_name} analizi tamamlandı: {len(ai_suggestions) if ai_suggestions else 0} öneri")
            
            if ai_suggestions:
                converted_suggestions = self.convert_to_editorial_suggestions(ai_suggestions)
                suggestions.extend(converted_suggestions)
                print(f"✅ {phase_name} önerileri eklendi: {len(converted_suggestions)} geçerli öneri")
            else:
                print(f"⚠️ {phase_name} analizinden hiç öneri gelmedi!")
        
        except AIAnalysisError:
            # AIAnalysisError'u yakala ve tekrar fırlat, böylece AnalysisManager işleyebilir
            raise
        except Exception as e:
            print(f"TEK FAZ ANALİZ HATASI (Genel): {str(e)}")
            import traceback
            print(f"Hata detayı: {traceback.format_exc()}")
            # Genel hatalar için de bir AIAnalysisError fırlatabiliriz
            raise AIAnalysisError(f"Analiz sırasında beklenmedik bir sistem hatası oluştu: {e}", error_type="system_error")
        
        print(f"TEK FAZ ANALİZ TAMAMLANDI: {len(suggestions)} öneri oluşturuldu")
        
        # Editör türüne göre öneri dağılımını göster
        editor_counts = {}
        for suggestion in suggestions:
            editor_type = getattr(suggestion, 'editor_type', 'Bilinmiyor')
            editor_counts[editor_type] = editor_counts.get(editor_type, 0) + 1
        
        for editor, count in editor_counts.items():
            print(f"  {editor}: {count} öneri")
        
        if not suggestions:
            print(f"  ⚠️ {phase_name} editöründen öneri gelmedi! AI prompt'larını veya ayarları kontrol edin.")
        
        # Loga kaydet
        self.log_action(f"Bölüm {chapter.chapter_number} - {phase_name} analizi", 
                       f"{len(suggestions)} öneri oluşturuldu")
        
        return suggestions
    
    def generate_novel_context(self, project, ai_integration) -> str:
        """
        Tüm projeden genel bir bağlam (roman kimliği) oluşturur.
        Bu, ana temaları, karakterleri, anlatıcı sesini vb. içerir.
        """
        print("📚 Roman kimliği oluşturuluyor...")
        
        # Projedeki tüm bölümlerin içeriğini birleştir
        full_text = ""
        if hasattr(project, 'chapters') and project.chapters:
            sorted_chapters = sorted(project.chapters, key=lambda c: c.chapter_number)
            for chapter in sorted_chapters:
                full_text += f"### Bölüm {chapter.chapter_number}\n\n{chapter.content}\n\n---\n\n"
        
        if not full_text.strip():
            print("⚠️ Roman kimliği oluşturulamadı: Proje içeriği boş.")
            self.novel_context = ""
            return ""
            
        # AI'dan özet oluşturmasını iste
        # Bu fonksiyonun ai_integration modülünde tanımlanması gerekecek
        context = ai_integration.generate_summary(full_text, "novel_context")
        
        self.novel_context = context
        print(f"✅ Roman kimliği oluşturuldu ve kaydedildi. Uzunluk: {len(context)} karakter.")
        self.log_action("Roman kimliği oluşturuldu", f"Uzunluk: {len(context)}")
        return context
    
    def convert_to_editorial_suggestions(self, ai_suggestions: List[Dict]) -> List[EditorialSuggestion]:
        """AI önerilerini (dict listesi) EditorialSuggestion nesnelerine çevirir ve geçersiz olanları filtreler."""
        editorial_suggestions = []
        
        for i, ai_suggestion_data in enumerate(ai_suggestions):
            # Gerekli temel alanların varlığını ve geçerliliğini kontrol et
            original_sentence = ai_suggestion_data.get('original_sentence')
            suggested_sentence = ai_suggestion_data.get('suggested_sentence')

            # 1. Alanların varlığını ve None olup olmadığını kontrol et
            if original_sentence is None or suggested_sentence is None:
                print(f"⚠️ Geçersiz öneri atlandı (NoneType cümle): Öneri #{i+1} - Veri: {ai_suggestion_data}")
                continue

            # 2. Alanların string olduğunu ve boş olmadığını kontrol et (strip sonrası)
            if not isinstance(original_sentence, str) or not isinstance(suggested_sentence, str) or \
               not original_sentence.strip() or not suggested_sentence.strip():
                print(f"⚠️ Geçersiz öneri atlandı (boş cümle): Öneri #{i+1} - Veri: {ai_suggestion_data}")
                continue
            
            original_sentence = original_sentence.strip()
            suggested_sentence = suggested_sentence.strip()

            # 3. Alanların anahtar kelimelerin kendisini içerip içermediğini kontrol et
            invalid_placeholders = ["original_sentence", "suggested_sentence"]
            if original_sentence in invalid_placeholders or suggested_sentence in invalid_placeholders:
                print(f"⚠️ Geçersiz öneri atlandı (placeholder içerik): Öneri #{i+1} - Veri: {ai_suggestion_data}")
                continue

            # 4. Orijinal ve önerilen metin aynı ise atla
            if original_sentence == suggested_sentence:
                print(f"⚠️ Geçersiz öneri atlandı (değişiklik yok): Öneri #{i+1}")
                continue

            # ID ve başlık gibi eksik olabilecek alanları doldur
            if 'id' not in ai_suggestion_data or not ai_suggestion_data['id']:
                ai_suggestion_data['id'] = f'sugg_{datetime.datetime.now().timestamp()}_{i}'
            
            if 'title' not in ai_suggestion_data or not ai_suggestion_data['title']:
                explanation_preview = ai_suggestion_data.get('explanation', '')[:40]
                title = explanation_preview if explanation_preview else original_sentence[:40]
                ai_suggestion_data['title'] = f"{i+1}. Öneri: {title}..."

            # from_dict metodunu kullanarak nesneyi oluştur
            try:
                suggestion_obj = EditorialSuggestion.from_dict(ai_suggestion_data)
                editorial_suggestions.append(suggestion_obj)
            except Exception as e:
                print(f"❌ Öneri nesnesi oluşturulurken hata: {e} - Veri: {ai_suggestion_data}")

        return editorial_suggestions
    
    def handle_suggestion(self, suggestion: EditorialSuggestion, action: str, chapter=None):
        """Öneri işleme - kabul/red/uygula"""
        # Eğer suggestion bir dict ise, onu EditorialSuggestion nesnesine dönüştür
        if isinstance(suggestion, dict):
            # Gerekli alanların eksik olup olmadığını kontrol et
            required_keys = ['id', 'type', 'title', 'description', 'severity', 'location', 'suggested_fix']
            if not all(key in suggestion for key in required_keys):
                # Eksik anahtarlar varsa, varsayılan değerlerle bir nesne oluştur
                suggestion_data = {key: suggestion.get(key, '') for key in required_keys}
                suggestion = EditorialSuggestion.from_dict(suggestion_data)
            else:
                suggestion = EditorialSuggestion.from_dict(suggestion)

        if action == "accept":
            suggestion.status = "accepted"
            self.log_action(f"Öneri kabul edildi", suggestion.title)
        
        elif action == "reject":
            suggestion.status = "rejected"
            self.log_action(f"Öneri reddedildi", suggestion.title)
        
        elif action == "apply":
            suggestion.status = "applied"
            self.log_action(f"Öneri uygulandı", suggestion.title)
            
            # Eğer chapter varsa ve orijinal/önerilen cümleler varsa değiştir
            if (chapter and hasattr(suggestion, 'original_sentence') and 
                hasattr(suggestion, 'suggested_sentence') and 
                suggestion.original_sentence and suggestion.suggested_sentence):
                
                self.apply_text_change(chapter, suggestion.original_sentence, 
                                      suggestion.suggested_sentence)
        
        return suggestion.status
    
    def apply_text_change(self, chapter, original_text: str, suggested_text: str):
        """Bölüm içeriğinde metin değişikliği yap - Biçimlendirme etiketlerini dikkate alarak."""
        try:
            import datetime
            import re
            
            print(f"METİN DEĞİŞTİRME GİRİŞİMİ (Format-Aware):")
            print(f"Orijinal: '{original_text}'")
            print(f"Önerilen: '{suggested_text}'")

            # 1. Tam eşleşme (en güvenli yöntem). Öneri metni, bölümdeki metinle birebir aynıysa çalışır.
            if original_text in chapter.content:
                chapter.content = chapter.content.replace(original_text, suggested_text, 1)
                chapter.last_modified = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"✅ TAM EŞLEŞME İLE DEĞİŞTİRİLDİ")
                return True

            # 2. Biçimlendirme etiketlerini yok sayan esnek Regex yöntemi.
            # Orijinal metindeki biçimlendirme etiketlerini temizle.
            clean_original_text = self._strip_formatting_markers(original_text)
            
            if not clean_original_text:
                print("❌ Orijinal metin biçimlendirme etiketleri dışında boş, değiştirme yapılamıyor.")
                return False

            # Orijinal metni, karakterler arasına herhangi bir biçimlendirme etiketinin gelebileceği
            # bir regex deseni oluştur.
            marker_pattern = r'(?:\*B\*|\*I\*|\*U\*)*'
            flexible_pattern = marker_pattern + marker_pattern.join(re.escape(c) for c in clean_original_text) + marker_pattern
            
            # Deseni kullanarak bölüm içeriğindeki ilk eşleşmeyi önerilen metinle değiştir.
            new_content, num_replacements = re.subn(flexible_pattern, suggested_text, chapter.content, count=1)
            
            if num_replacements > 0:
                chapter.content = new_content
                chapter.last_modified = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"✅ FORMAT-AWARE REGEX EŞLEŞMESİ İLE DEĞİŞTİRİLDİ")
                return True
            else:
                # Regex de başarısız olursa, logla ve işlemi sonlandır.
                print(f"❌ METİN BULUNAMADI (Regex denendi): '{original_text[:50]}...'")
                print(f"İçerik önizlemesi: '{chapter.content[:200]}...'")
                return False
                
        except Exception as e:
            print(f"METİN DEĞİŞTİRME HATASI: {e}")
            import traceback
            print(f"Hata detayı: {traceback.format_exc()}")
            return False
    
    def _strip_formatting_markers(self, text: str) -> str:
        """Metindeki biçimlendirme etiketlerini (*B*, *I*, *U*) temizler."""
        import re
        return re.sub(r'\*B\*|\*I\*|\*U\*', '', text)
    
    def get_chapter_suggestions(self, chapter_number: int) -> List[EditorialSuggestion]:
        """Belirli bir bölümün önerilerini getir"""
        return self.all_suggestions.get(chapter_number, [])
    
    def get_pending_suggestions(self, chapter_number: Optional[int] = None) -> List[EditorialSuggestion]:
        """Bekleyen önerileri getir"""
        pending = []
        
        if chapter_number:
            suggestions = self.all_suggestions.get(chapter_number, [])
            pending = [s for s in suggestions if s.status == "pending"]
        else:
            for chapter_suggestions in self.all_suggestions.values():
                pending.extend([s for s in chapter_suggestions if s.status == "pending"])
        
        return pending
    
    def get_statistics(self) -> Dict:
        """İstatistikler döndür"""
        total_suggestions = 0
        accepted = 0
        rejected = 0
        applied = 0
        pending = 0
        
        for chapter_suggestions in self.all_suggestions.values():
            total_suggestions += len(chapter_suggestions)
            for suggestion in chapter_suggestions:
                if suggestion.status == "accepted":
                    accepted += 1
                elif suggestion.status == "rejected":
                    rejected += 1
                elif suggestion.status == "applied":
                    applied += 1
                else:
                    pending += 1
        
        return {
            'total_suggestions': total_suggestions,
            'accepted': accepted,
            'rejected': rejected,
            'applied': applied,
            'pending': pending,
            'processed_chapters': len(self.processed_chapters),
            'completion_rate': applied / total_suggestions if total_suggestions > 0 else 0
        }
    
    def mark_chapter_processed(self, chapter_number: int):
        """Bölümü işlenmiş olarak işaretle"""
        self.processed_chapters.add(chapter_number)
        self.log_action(f"Bölüm {chapter_number} tamamlandı", "Editöryal süreç bitti")
    
    def get_workflow_progress(self) -> Dict:
        """İş akışı ilerlemesini döndür"""
        return {
            'current_chapter': self.current_chapter,
            'processed_chapters': list(self.processed_chapters),
            'total_chapters': len(self.all_suggestions),
            'progress_percentage': len(self.processed_chapters) / len(self.all_suggestions) * 100 
                                 if self.all_suggestions else 0
        }
    
    def log_action(self, action: str, details: str = ""):
        """Eylem logla"""
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'action': action,
            'details': details,
            'chapter': self.current_chapter
        }
        self.editorial_log.append(log_entry)
    
    def export_log(self, file_path: str):
        """Logları dışa aktar"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(self.editorial_log, file, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Log dışa aktarma hatası: {e}")
            return False
    
    def generate_report(self) -> Dict:
        """Editöryal rapor oluştur"""
        stats = self.get_statistics()
        progress = self.get_workflow_progress()
        
        # Bölüm bazında analiz
        chapter_analysis = {}
        for chapter_num, suggestions in self.all_suggestions.items():
            chapter_analysis[chapter_num] = {
                'total_suggestions': len(suggestions),
                'by_severity': {
                    'high': len([s for s in suggestions if s.severity == 'high']),
                    'medium': len([s for s in suggestions if s.severity == 'medium']),
                    'low': len([s for s in suggestions if s.severity == 'low'])
                },
                'by_type': {}
            }
            
            # Tip bazında sayım
            type_count = {}
            for suggestion in suggestions:
                type_count[suggestion.type] = type_count.get(suggestion.type, 0) + 1
            chapter_analysis[chapter_num]['by_type'] = type_count
        
        return {
            'statistics': stats,
            'progress': progress,
            'chapter_analysis': chapter_analysis,
            'generation_time': datetime.datetime.now().isoformat()
        }
    
    def get_state(self) -> Dict:
        """Mevcut durumu döndür"""
        return {
            'current_chapter': self.current_chapter,
            'processed_chapters': list(self.processed_chapters),
            'all_suggestions': {
                str(k): [s.to_dict() for s in v] 
                for k, v in self.all_suggestions.items()
            },
            'editorial_log': self.editorial_log,
            'workflow_settings': self.workflow_settings,
            'novel_context': self.novel_context
        }
    
    def load_state(self, state: Dict):
        """Durumu yükle"""
        self.current_chapter = state.get('current_chapter', 1)
        self.processed_chapters = set(state.get('processed_chapters', []))
        self.editorial_log = state.get('editorial_log', [])
        self.workflow_settings = state.get('workflow_settings', self.workflow_settings)
        self.novel_context = state.get('novel_context', '') # Kayıtlı roman kimliğini yükle
        
        # Önerileri yükle
        suggestions_data = state.get('all_suggestions', {})
        self.all_suggestions = {}
        
        for chapter_str, suggestions_list in suggestions_data.items():
            chapter_num = int(chapter_str)
            self.all_suggestions[chapter_num] = [
                EditorialSuggestion.from_dict(s_data) for s_data in suggestions_list
            ]
