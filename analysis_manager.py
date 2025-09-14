import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import datetime
import threading
import time

# Import modülleri
from modules.file_manager import FileManager
from modules.ai_integration import AIIntegration, AIAnalysisError
from modules.editorial_process import EditorialProcess, EditorialSuggestion
from modules.settings_manager import SettingsManager
from modules.ui_components import SuggestionCard, ProjectPanel

class AnalysisManager:
    def __init__(self, app):
        self.app = app
        self.ai_integration = app.ai_integration
        self.editorial_process = app.editorial_process
        self.file_manager = app.file_manager
        self.settings_manager = app.settings_manager

    def _get_phase_name(self, analysis_type: str) -> str:
        """Analiz türüne göre aşama adını döndürür"""
        phase_names = {
            "grammar_check": "Dil Bilgisi",
            "style_analysis": "Üslup",
            "content_review": "İçerik"
        }
        return phase_names.get(analysis_type, analysis_type.capitalize())

    def generate_full_novel_content(self) -> str:
        """Romanın tamamını içeren bir metin oluşturur"""
        full_text = ""
        if hasattr(self.file_manager, 'chapters') and self.file_manager.chapters:
            sorted_chapters = sorted(self.file_manager.chapters, key=lambda c: c.chapter_number)
            for chapter in sorted_chapters:
                full_text += f"### Bölüm {chapter.chapter_number}\n\n{chapter.content}\n\n---\n\n"
        return full_text

    def update_analysis_button(self, phase: str):
        """Analiz butonunun text'ini güncelle"""
        button_texts = {
            "none": "Dil Bilgisi Analizi",
            "grammar": "Üslup Analizi",
            "style": "İçerik Analizi",
            "content": "Analiz Tamamlandı",
            "completed": "Dil Bilgisi Analizi"  # Yeni bölüm için baştan başla
        }
        
        if self.app.analysis_button:
            text = button_texts.get(phase, "Analizi Başlat")
            self.app.analysis_button.config(text=text)
            
            # Analiz tamamlandıysa butonu devre dışı bırak
            if phase == "content":
                self.app.analysis_button.config(state="disabled")
            else:
                self.app.analysis_button.config(state="normal")

    def reset_analysis_phase(self):
        """Analiz fazlarını sıfırla (yeni bölüm seçildiğinde)"""
        self.app.current_analysis_phase = "none"
        self.app.current_analyzing_chapter = None
        self.update_analysis_button("none")

    def set_chapter_analysis_phase(self, chapter, phase: str, completed: bool = False):
        """Bölümün analiz fazını ayarla ve kaydet"""
        if not hasattr(chapter, 'analysis_phases'):
            chapter.analysis_phases = {
                "grammar_completed": False,
                "style_completed": False,
                "content_completed": False,
                "grammar_failed": False,
                "style_failed": False,
                "content_failed": False,
                "current_phase": "none"
            }
        
        # Mevcut fazı ayarla
        if phase in ["none", "grammar", "style", "content", "completed"]:
            chapter.analysis_phases["current_phase"] = phase
        
        # Tamamlanan fazları işaretle
        if completed:
            if phase == "grammar":
                chapter.analysis_phases["grammar_completed"] = True
            elif phase == "style":
                chapter.analysis_phases["style_completed"] = True
            elif phase == "content":
                chapter.analysis_phases["content_completed"] = True
                # Tüm fazlar tamamlandıysa bölümü işlenmiş olarak işaretle
                chapter.is_processed = True
        
        print(f"📊 Bölüm {chapter.chapter_number} analiz durumu güncellendi:")
        print(f"   Mevcut faz: {chapter.analysis_phases['current_phase']}")
        print(f"   Dil Bilgisi: {'✅' if chapter.analysis_phases['grammar_completed'] else '❌'}")
        print(f"   Üslup: {'✅' if chapter.analysis_phases['style_completed'] else '❌'}")
        print(f"   İçerik: {'✅' if chapter.analysis_phases['content_completed'] else '❌'}")
        
        # Değişikliği işaretle
        self.app.mark_as_modified()
        
        # Bölüm listesini güncelle - analiz durumlarını anlık yansıtmak için
        if hasattr(self.app, 'project_panel') and self.app.project_panel:
            self.app.project_panel.update_chapters(self.app.project_panel.chapters, preserve_selection=True)

    def get_chapter_analysis_phase(self, chapter):
        """Bölümün mevcut analiz fazını al"""
        if not hasattr(chapter, 'analysis_phases'):
            # İlk kez yüklenen bölüm için analiz fazlarını başlat
            chapter.analysis_phases = {
                "grammar_completed": False,
                "style_completed": False,
                "content_completed": False,
                "grammar_failed": False,
                "style_failed": False,
                "content_failed": False,
                "current_phase": "none"
            }
            print(f"🆕 Bölüm {chapter.chapter_number} için analiz fazları başlatıldı")
        return chapter.analysis_phases.get("current_phase", "none")

    def load_chapter_analysis_state(self, chapter):
        """Bölüm seçildiğinde analiz durumunu yükle"""
        if not chapter:
            self.reset_analysis_phase()
            return
        
        # Bölümün kaydedilmiş analiz durumunu yükle
        saved_phase = self.get_chapter_analysis_phase(chapter)
        
        # Ana uygulamanın analiz fazını güncelle
        self.app.current_analysis_phase = saved_phase
        self.app.current_analyzing_chapter = chapter
        
        # Buton metnini güncelle
        self.update_analysis_button(saved_phase)
        
        print(f"📂 Bölüm {chapter.chapter_number} analiz durumu yüklendi: {saved_phase}")

    def start_analysis(self, novel_context=None, full_novel_content=None):
        # Analizden önce projenin kaydedildiğinden emin ol
        if not self.settings_manager.get_setting('last_project'):
            print("Proje kaydedilmemiş, ilk analizden önce otomatik kaydediliyor...")
            # Proje adını romandan al veya varsayılan bir ad kullan
            project_name = self.file_manager.novel_title if self.file_manager.novel_title else f"Yeni Proje {datetime.datetime.now().strftime('%Y%m%d')}"
            
            # Projeyi kaydetmek için FileOperationsManager'daki metodu çağır
            if self.app.file_ops_manager:
                self.app.file_ops_manager.save_project(auto_save=True, new_project_name=project_name)
            else:
                messagebox.showerror("Hata", "Dosya operasyonları yöneticisi bulunamadı. Proje kaydedilemiyor.")
                return

        current_chapter = self.app.project_panel.get_current_chapter()
        
        if not current_chapter:
            messagebox.showwarning("Uyarı", "Lütfen analiz edilecek bir bölüm seçin.")
            return

        # API anahtarı kontrolü
        api_key = self.settings_manager.get_setting("api_key", "")
        if not api_key:
            response = messagebox.askyesno(
                "YZ Ayarları Gerekli",
                "Analiz için Gemini API anahtarı gerekli.\n\nYZ ayarlarını şimdi yapmak ister misiniz?"
            )
            if response:
                self.app.open_ai_settings()
            return
        
        # Yeni bölüm seçildiyse analiz sıfırla
        if self.app.current_analyzing_chapter != current_chapter:
            self.load_chapter_analysis_state(current_chapter)
            # Önceki önerileri temizle
            self.app.display_suggestions([])
        
        # Analiz fazlarına göre işlem yap
        if self.app.current_analysis_phase == "none":
            # Dil Bilgisi analizi başlat
            if self.app._has_pending_suggestions():
                messagebox.showinfo("Bekleyen Öneriler",
                    "Bu bölüm için zaten bekleyen öneriler var.\n\n"
                    "Lütfen önce mevcut önerileri uygulayın veya reddedin, sonra yeni bir analiz başlatın.")
                return
            self.app.current_analysis_phase = "grammar"
            self.set_chapter_analysis_phase(current_chapter, "grammar")
            self._start_phase_analysis(current_chapter, "grammar_check", "Dil Bilgisi", novel_context, full_novel_content)
            
        elif self.app.current_analysis_phase == "grammar":
            # Üslup analizi başlat (Dil Bilgisi önerileri uygulandı mı kontrol et)
            if self.app._has_pending_suggestions():
                messagebox.showinfo("Bekleyen Öneriler",
                    "Bu bölüm için zaten bekleyen öneriler var.\n\n"
                    "Lütfen önce mevcut önerileri uygulayın veya reddedin, sonra yeni bir analiz başlatın.")
                return
            
            # Dil Bilgisi fazını tamamlanmış olarak işaretle
            self.set_chapter_analysis_phase(current_chapter, "style", completed=False)
            # Önceki fazı da tamamlanmış olarak işaretle
            current_chapter.analysis_phases["grammar_completed"] = True
            
            self.app.current_analysis_phase = "style"
            self._start_phase_analysis(current_chapter, "style_analysis", "Üslup", novel_context, full_novel_content)
            
        elif self.app.current_analysis_phase == "style":
            # İçerik analizi başlat (üslup önerileri uygulandı mı kontrol et)
            if self.app._has_pending_suggestions():
                messagebox.showinfo("Bekleyen Öneriler",
                    "Bu bölüm için zaten bekleyen öneriler var.\n\n"
                    "Lütfen önce mevcut önerileri uygulayın veya reddedin, sonra yeni bir analiz başlatın.")
                return
                
            # Üslup fazını tamamlanmış olarak işaretle
            self.set_chapter_analysis_phase(current_chapter, "content", completed=False)
            # Önceki fazı da tamamlanmış olarak işaretle
            current_chapter.analysis_phases["style_completed"] = True
            
            self.app.current_analysis_phase = "content"
            self._start_phase_analysis(current_chapter, "content_review", "İçerik", novel_context, full_novel_content)
            
        elif self.app.current_analysis_phase == "content":
            # Tüm analiz tamamlandı
            if self.app._has_pending_suggestions():
                messagebox.showinfo("Bekleyen Öneriler", 
                    "Lütfen önce mevcut içerik önerilerini uygulayarak kaldırın.")
                return
            
            # İçerik fazını ve tüm analizi tamamlanmış olarak işaretle
            self.set_chapter_analysis_phase(current_chapter, "completed", completed=True)
            current_chapter.analysis_phases["content_completed"] = True
            
            # Bölümü tamamlanmış olarak işaretle
            self.app.project_panel.mark_chapter_processed()
            self.update_analysis_button("completed")
            messagebox.showinfo("Analiz Tamamlandı", 
                f"{current_chapter.title} bölümünün tüm analizi tamamlandı!\n\nSonraki bölüme geçebilirsiniz.")
            
            # Yeni bölüm için hazırla
            self.reset_analysis_phase()

    def start_analysis_on_selection(self, chapter, selected_text):
        """Starts a grammar analysis specifically on the selected text, respecting context settings."""
        # API key check
        api_key = self.settings_manager.get_setting("api_key", "")
        if not api_key:
            response = messagebox.askyesno(
                "YZ Ayarları Gerekli",
                "Analiz için Gemini API anahtarı gerekli.\n\nYZ ayarlarını şimdi yapmak ister misiniz?"
            )
            if response:
                self.app.open_ai_settings()
            return

        # Determine context based on settings for grammar_check
        novel_context_to_pass = None
        full_novel_content_to_pass = None
        context_source = self.settings_manager.get_setting("grammar_check_context_source", "none")

        if context_source == "novel_context":
            novel_context_to_pass = self.editorial_process.novel_context
            print("Seçim analizi için 'Roman Kimliği' bağlamı kullanılacak.")
        elif context_source == "full_text":
            full_novel_content_to_pass = self.generate_full_novel_content()
            print("Seçim analizi için 'Romanın Tam Metni' bağlamı kullanılacak.")
        else:
            print("Seçim analizi bağlam olmadan yapılacak.")

        self.app.show_analysis_status(f"🔍 Seçili metin için dil bilgisi analizi hazırlanıyor...", "blue")
        self.app.show_progress(f"Seçim analizi başlatılıyor...")

        # Use threading to run in the background
        analysis_thread = threading.Thread(
            target=self._threaded_selection_analysis,
            args=(chapter, selected_text, novel_context_to_pass, full_novel_content_to_pass)
        )
        analysis_thread.daemon = True
        analysis_thread.start()

    def _threaded_selection_analysis(self, chapter, selected_text, novel_context, full_novel_content):
        """Threading wrapper for selection-based analysis."""
        try:
            self._perform_selection_analysis(chapter, selected_text, novel_context, full_novel_content)
        except Exception as e:
            # Report error from thread to the main thread
            self.app.root.after(0, lambda: self._handle_thread_error(str(e)))

    def _perform_selection_analysis(self, chapter, selected_text, novel_context, full_novel_content):
        """Performs the actual analysis on the selected text snippet."""
        try:
            phase_name = "Dil Bilgisi (Seçim)"
            analysis_type = "grammar_check"

            self.app.root.after(0, lambda: self.app.show_progress(f"{phase_name} analizi yapılıyor..."))
            print(f"=== {phase_name.upper()} ANALİZİ BAŞLATILDI ===")
            print(f"Bölüm: {chapter.title}, Seçili Metin: {len(selected_text)} char")

            if not self.ai_integration or not self.ai_integration.model:
                raise AIAnalysisError("YZ modeli yapılandırılmamış - Lütfen YZ ayarlarını kontrol edin", "config_error")

            # Call the AI analysis with the selected text and context
            suggestions = self.editorial_process.analyze_text_snippet(
                selected_text, self.ai_integration, analysis_type,
                novel_context=novel_context,
                full_novel_content=full_novel_content
            )

            print(f"=== {phase_name.upper()} ANALİZ SONUÇLARI ===")
            print(f"Bulunan öneri sayısı: {len(suggestions) if suggestions else 0}")
            self.app.root.after(0, lambda: self.app.hide_progress())

            if suggestions:
                self.app.root.after(0, lambda: self.app.show_analysis_status(
                    f"✅ Seçim analizi tamamlandı: {len(suggestions)} yeni öneri bulundu", "green"
                ))
                # Add new suggestions to the existing ones
                if not hasattr(chapter, 'suggestions') or not chapter.suggestions:
                    chapter.suggestions = []
                
                # Mevcut öneri ID'lerini bir kümede topla
                existing_ids = {s.id for s in chapter.suggestions if hasattr(s, 'id')}
                
                newly_added_suggestions = []
                for s in suggestions:
                    if s.id not in existing_ids:
                        chapter.suggestions.append(s)
                        newly_added_suggestions.append(s)

                if newly_added_suggestions:
                    print(f"{len(newly_added_suggestions)} adet yeni öneri listeye eklendi.")
                    self.app.root.after(0, lambda: self.app.display_suggestions(chapter.suggestions))
                else:
                    print("Bulunan tüm öneriler zaten listede mevcuttu.")
                    self.app.root.after(0, lambda: messagebox.showinfo("Analiz Sonucu", "Bulunan öneriler zaten öneri listesinde mevcut."))

            else:
                self.app.root.after(0, lambda: self.app.show_analysis_status(
                    f"✅ Seçim analizi tamamlandı ancak öneri bulunamadı.", "green"
                ))
                self.app.root.after(0, lambda: messagebox.showinfo("Analiz Sonucu", "Seçilen metinde herhangi bir dil bilgisi sorunu bulunamadı."))


        except AIAnalysisError as e:
            print(f"=== {phase_name.upper()} ANALİZ HATASI (AI) ===")
            print(f"Hata mesajı: {str(e)}")
            error_msg = f"❌ {phase_name} analizi başarısız oldu: {str(e)}"
            self.app.root.after(0, lambda: self.app.hide_progress())
            self.app.root.after(0, lambda: self.app.show_analysis_status(error_msg, "red"))
            self.app.root.after(0, lambda msg=str(e): messagebox.showwarning(f"{phase_name} Analiz Uyarısı", f"Analiz tamamlanamadı:\n\n{msg}"))

        except Exception as e:
            print(f"=== {phase_name.upper()} ANALİZ HATASI (Genel) ===")
            import traceback
            print(f"Hata detayı: {traceback.format_exc()}")
            error_msg = f"❌ {phase_name} analiz hatası: {str(e)}"
            self.app.root.after(0, lambda: self.app.hide_progress())
            self.app.root.after(0, lambda: self.app.show_analysis_status(error_msg, "red"))
            self.app.root.after(0, lambda msg=str(e): messagebox.showwarning("Analiz Uyarısı", f"Beklenmedik bir sistem hatası oluştu:\n{msg}"))

    def _start_phase_analysis(self, chapter, analysis_type: str, phase_name: str, novel_context, full_novel_content):
        """Belirli bir faz için analiz başlat"""
        self.app.show_analysis_status(f"🔍 {chapter.title} - {phase_name} analizi hazırlanıyor...", "blue")
        self.app.show_progress(f"{phase_name} analizi başlatılıyor...")
        
        # Threading ile arka planda çalıştır
        analysis_thread = threading.Thread(target=self._threaded_phase_analysis, 
                                         args=(chapter, analysis_type, phase_name, novel_context, full_novel_content))
        analysis_thread.daemon = True
        analysis_thread.start()

    def _threaded_phase_analysis(self, chapter, analysis_type: str, phase_name: str, novel_context, full_novel_content):
        """Faz bazlı analiz için threading wrapper"""
        try:
            self._perform_phase_analysis(chapter, analysis_type, phase_name, novel_context, full_novel_content)
        except Exception as e:
            # Thread'den ana thread'e hata bildirimi
            self.app.root.after(0, lambda: self._handle_thread_error(str(e)))

    def _perform_phase_analysis(self, chapter, analysis_type: str, phase_name: str, novel_context, full_novel_content):
        """Belirli bir faz için gerçek analiz işlemini yap"""
        try:
            # Eğer harici olarak bir bağlam sağlanmadıysa, ayarlardan belirle
            if novel_context is None and full_novel_content is None:
                context_setting_key = f"{analysis_type}_context_source"
                context_source = self.settings_manager.get_setting(context_setting_key, "none")

                if context_source == "novel_context":
                    # Roman kimliği oluştur veya mevcut olanı kullan
                    if not self.editorial_process.novel_context:
                        self.app.root.after(0, lambda: self.app.show_progress("Roman kimliği oluşturuluyor..."))
                        self.editorial_process.generate_novel_context(self.file_manager, self.ai_integration)
                    novel_context = self.editorial_process.novel_context
                    print(f"Analiz ({phase_name}) için 'Roman Kimliği' bağlamı kullanılacak.")
                
                elif context_source == "full_text":
                    # Romanın tam metnini oluştur
                    self.app.root.after(0, lambda: self.app.show_progress("Romanın tam metni hazırlanıyor..."))
                    full_novel_content = self.generate_full_novel_content()
                    print(f"Analiz ({phase_name}) için 'Romanın Tam Metni' bağlamı kullanılacak.")
                
                else:
                    print(f"Analiz ({phase_name}) bağlam olmadan yapılacak.")

            # Analiz aşaması
            self.app.root.after(0, lambda: self.app.show_progress(f"{phase_name} analizi yapılıyor..."))
            print(f"=== {phase_name.upper()} ANALİZİ BAŞLATILDI ===")
            print(f"Bölüm: {chapter.title}, İçerik: {len(chapter.content)} char")

            if not self.ai_integration or not self.ai_integration.model:
                raise AIAnalysisError("YZ modeli yapılandırılmamış - Lütfen YZ ayarlarını kontrol edin", "config_error")

            # AI analizini çağır ve AIAnalysisError'u yakala
            suggestions = self.editorial_process.analyze_chapter_single_phase(
                chapter, self.ai_integration, analysis_type, novel_context, full_novel_content
            )

            print(f"=== {phase_name.upper()} ANALİZ SONUÇLARI ===")
            print(f"Bulunan öneri sayısı: {len(suggestions) if suggestions else 0}")
            self.app.root.after(0, lambda: self.app.hide_progress())

            # BAŞARILI ANALİZ DURUMU
            # Başarılı analizde hata bayraklarını temizle
            if analysis_type == "grammar_check":
                chapter.analysis_phases["grammar_failed"] = False
            elif analysis_type == "style_analysis":
                chapter.analysis_phases["style_failed"] = False
            elif analysis_type == "content_review":
                chapter.analysis_phases["content_failed"] = False

            if suggestions:
                self.app.root.after(0, lambda: self.app.show_analysis_status(
                    f"✅ {phase_name} analizi tamamlandı: {len(suggestions)} öneri bulundu", "green"
                ))
            else:
                self.app.root.after(0, lambda: self.app.show_analysis_status(
                    f"✅ {phase_name} analizi tamamlandı ancak öneri bulunamadı.", "green"
                ))
            
            self.app.root.after(0, lambda: self.app.display_suggestions(suggestions or []))
            chapter.suggestions = suggestions or []

            # Fazı tamamlanmış olarak işaretle ve sonraki faza geç
            if analysis_type == "grammar_check":
                self.app.root.after(0, lambda: self.set_chapter_analysis_phase(chapter, "grammar", completed=True))
            elif analysis_type == "style_analysis":
                self.app.root.after(0, lambda: self.set_chapter_analysis_phase(chapter, "style", completed=True))
            elif analysis_type == "content_review":
                self.app.root.after(0, lambda: self.set_chapter_analysis_phase(chapter, "content", completed=True))

            next_phase = {"grammar_check": "grammar", "style_analysis": "style", "content_review": "content"}.get(analysis_type)
            self.app.root.after(0, lambda: self.update_analysis_button(next_phase))
            
            # UI güncellemeleri
            self.app.root.after(0, lambda: self.app.project_panel.update_preview(chapter))
            self.app.root.after(0, lambda: self.app.project_panel.update_status())
            self.app.root.after(0, lambda: self.app.project_panel.update_chapters(self.app.project_panel.chapters, preserve_selection=True))
            self.app.root.after(0, lambda: self.app.mark_as_modified())

        except AIAnalysisError as e:
            print(f"=== {phase_name.upper()} ANALİZ HATASI (AI) ===")
            print(f"Hata mesajı: {str(e)}")
            
            error_msg = f"❌ {phase_name} analizi başarısız oldu: {str(e)}"
            self.app.root.after(0, lambda: self.app.hide_progress())
            self.app.root.after(0, lambda: self.app.show_analysis_status(error_msg, "red"))
            self.app.root.after(0, lambda msg=str(e): messagebox.showwarning(f"{phase_name} Analiz Uyarısı", f"Analiz tamamlanamadı:\n\n{msg}"))

            # Analiz fazını başarısız olarak işaretle ve UI'ı güncelle
            if analysis_type == "grammar_check":
                chapter.analysis_phases["grammar_completed"] = False
                chapter.analysis_phases["grammar_failed"] = True  # Hata bayrağı
                self.app.current_analysis_phase = "none"
                self.app.root.after(0, lambda: self.set_chapter_analysis_phase(chapter, "none", completed=False))
                self.app.root.after(0, lambda: self.update_analysis_button("none"))
            elif analysis_type == "style_analysis":
                chapter.analysis_phases["style_completed"] = False
                chapter.analysis_phases["style_failed"] = True  # Hata bayrağı
                self.app.current_analysis_phase = "grammar"
                self.app.root.after(0, lambda: self.set_chapter_analysis_phase(chapter, "grammar", completed=False))
                self.app.root.after(0, lambda: self.update_analysis_button("grammar"))
            elif analysis_type == "content_review":
                chapter.analysis_phases["content_completed"] = False
                chapter.analysis_phases["content_failed"] = True  # Hata bayrağı
                self.app.current_analysis_phase = "style"
                self.app.root.after(0, lambda: self.set_chapter_analysis_phase(chapter, "style", completed=False))
                self.app.root.after(0, lambda: self.update_analysis_button("style"))
            
            # Proje panelini (bölüm listesi ve önizleme) güncelle
            self.app.root.after(0, lambda: self.app.project_panel.update_chapters(self.app.project_panel.chapters, preserve_selection=True))

        except Exception as e:
            print(f"=== {phase_name.upper()} ANALİZ HATASI (Genel) ===")
            import traceback
            print(f"Hata detayı: {traceback.format_exc()}")
            
            error_msg = f"❌ {phase_name} analiz hatası: {str(e)}"
            self.app.root.after(0, lambda: self.app.hide_progress())
            self.app.root.after(0, lambda: self.app.show_analysis_status(error_msg, "red"))
            self.app.root.after(0, lambda msg=str(e): messagebox.showwarning("Analiz Uyarısı", f"Beklenmedik bir sistem hatası oluştu:\n{msg}"))

    def _has_pending_suggestions(self) -> bool:
        """Bekleyen öneri var mı kontrol et - doğrudan veri modelinden"""
        current_chapter = self.app.project_panel.get_current_chapter()
        if not current_chapter:
            return False
        
        # 'suggestions' listesi, UI'da gösterilen aktif/bekleyen önerileri tutar.
        # Bu liste boş değilse, bekleyen öneri var demektir.
        has_suggestions = hasattr(current_chapter, 'suggestions') and current_chapter.suggestions
        
        print(f"DEBUG - Pending suggestion kontrolü (veri modeli): {len(current_chapter.suggestions) if has_suggestions else 0} öneri bulundu")
        return bool(has_suggestions)

    def check_phase_completion(self):
        """Mevcut faz tamamlandı mı kontrol et ve gerekirse buton durumunu güncelle"""
        # Eğer hiç bekleyen öneri yoksa ve bir analiz fazındayız, buton metnini güncelle
        if not self.app._has_pending_suggestions() and self.app.current_analysis_phase != "none":
            
            # Hangi fazda olduğumuza göre buton metnini ayarla
            if self.app.current_analysis_phase == "grammar":
                self.update_analysis_button("grammar")  # "Üslup Analizi" olacak
                self.app.show_analysis_status(
                    "✅ Dil Bilgisi önerileri tamamlandı. 'Üslup Analizi' butonuna tıklayarak devam edebilirsiniz.",
                    "green"
                )
            elif self.app.current_analysis_phase == "style":
                self.update_analysis_button("style")  # "İçerik Analizi" olacak
                self.app.show_analysis_status(
                    "✅ Üslup önerileri tamamlandı. 'İçerik Analizi' butonuna tıklayarak devam edebilirsiniz.",
                    "green"
                )
            elif self.app.current_analysis_phase == "content":
                # İçerik analizi tamamen tamamlandı - durumu güncelle
                current_chapter = self.app.project_panel.get_current_chapter()
                if current_chapter:
                    # Fazları tamamlanmış olarak işaretle
                    self.set_chapter_analysis_phase(current_chapter, "completed", completed=True)
                    current_chapter.analysis_phases["content_completed"] = True
                    
                    # Analiz fazlarını sıfırla
                    self.app.current_analysis_phase = "completed"
                    
                    # UI güncellemelerini yap
                    self.update_analysis_button("content")  # "Analiz Tamamlandı" olacak
                    self.app.show_analysis_status(
                        "✅ İçerik önerileri tamamlandı. Bölüm analizi tamamen bitti!", 
                        "green"
                    )
                    
                    # Proje panelini güncelle - önemli!
                    self.app.project_panel.update_chapters(self.app.project_panel.chapters, preserve_selection=True)
                    self.app.project_panel.update_status()
                    
                    # Bölüm içeriğini güncelle - önizleme paneli için
                    self.app.display_chapter_content(current_chapter)
                    
                    # Proje değiştirildi olarak işaretle
                    self.app.mark_as_modified()
                    
                    print(f"🎉 Bölüm {current_chapter.chapter_number} tamamen tamamlandı!")
                    print(f"    Durum: {current_chapter.analysis_phases['current_phase']}")
                    print(f"    Dil Bilgisi: {'✅' if current_chapter.analysis_phases['grammar_completed'] else '❌'}")
                    print(f"    Üslup: {'✅' if current_chapter.analysis_phases['style_completed'] else '❌'}")
                    print(f"    İçerik: {'✅' if current_chapter.analysis_phases['content_completed'] else '❌'}")


    def _handle_thread_error(self, error_message):
        """Thread hatalarını ana thread'de işle"""
        print(f"Thread hatası: {error_message}")
        self.app.hide_progress()
        self.app.show_analysis_status(f"❌ Analiz hatası: {error_message}", "red")
        messagebox.showerror("Analiz Hatası", f"Analiz sırasında bir hata oluştu:\n{error_message}")

    def start_full_analysis(self):
        """Tüm bölümler için tam analiz sürecini başlatır."""
        # Analizden önce projenin kaydedildiğinden emin ol
        if not self.settings_manager.get_setting('last_project'):
            print("Proje kaydedilmemiş, ilk analizden önce otomatik kaydediliyor...")
            project_name = self.file_manager.novel_title if self.file_manager.novel_title else f"Yeni Proje {datetime.datetime.now().strftime('%Y%m%d')}"
            if self.app.file_ops_manager:
                self.app.file_ops_manager.save_project(auto_save=True, new_project_name=project_name)
            else:
                messagebox.showerror("Hata", "Dosya operasyonları yöneticisi bulunamadı. Proje kaydedilemiyor.")
                return

        # API anahtarı kontrolü
        api_key = self.settings_manager.get_setting("api_key", "")
        if not api_key:
            response = messagebox.askyesno(
                "YZ Ayarları Gerekli",
                "Analiz için Gemini API anahtarı gerekli.\n\nYZ ayarlarını şimdi yapmak ister misiniz?"
            )
            if response:
                self.app.open_ai_settings()
            return

        # Başlamadan önce tüm hata bayraklarını sıfırla
        if self.file_manager.chapters:
            print("🔄 Tüm bölümler için hata bayrakları sıfırlanıyor...")
            for chapter in self.file_manager.chapters:
                if hasattr(chapter, 'analysis_phases'):
                    chapter.analysis_phases['grammar_failed'] = False
                    chapter.analysis_phases['style_failed'] = False
                    chapter.analysis_phases['content_failed'] = False
            # UI'ı güncellemek için
            self.app.project_panel.update_chapters(self.app.project_panel.chapters, preserve_selection=True)


        # Analizi bir thread içinde başlat
        full_analysis_thread = threading.Thread(target=self._threaded_full_analysis)
        full_analysis_thread.daemon = True
        full_analysis_thread.start()

    def _threaded_full_analysis(self):
        """Tüm bölümlerin analizini arka planda yürüten asıl metot."""
        try:
            # Sadece sıradaki bir görevi al
            task = self._get_next_analysis_task()
            
            if not task:
                self.app.root.after(0, lambda: messagebox.showinfo("Analiz Tamamlandı", "Tüm bölümlerin analizi başarıyla tamamlandı."))
                self.app.root.after(0, lambda: self.app.show_analysis_status("✅ Tüm analizler tamamlandı!", "green"))
                return

            analysis_type, chapters_to_analyze, phase_name = task
            total_chapters = len(chapters_to_analyze)
            
            self.app.root.after(0, lambda: self.app.show_analysis_status(f"🚀 {phase_name} analizi başlıyor ({total_chapters} bölüm)...", "blue"))

            for i, chapter in enumerate(chapters_to_analyze):
                # Arayüzü güncelle: Analiz edilen bölümü seç ve içeriğini göster
                try:
                    chapter_index = self.file_manager.chapters.index(chapter)
                    self.app.root.after(0, lambda idx=chapter_index: self.app.project_panel.select_chapter(idx))
                except ValueError:
                    print(f"Hata: Bölüm '{chapter.title}' proje listesinde bulunamadı. Atlanıyor.")
                    continue

                progress_text = f"{phase_name} analizi: Bölüm {i+1}/{total_chapters} ({chapter.title})"
                self.app.root.after(0, lambda p=progress_text: self.app.show_progress(p))
                
                try:
                    # Bağlam parametrelerini None olarak göndererek _perform_phase_analysis'in
                    # ayarlara göre doğru bağlamı seçmesini sağlıyoruz.
                    self._perform_phase_analysis(chapter, analysis_type, phase_name, None, None)
                    time.sleep(2)  # API limitleri için bekleme

                except Exception as e:
                    error_msg = f"Bölüm {chapter.chapter_number} analizi başarısız: {e}"
                    print(error_msg)
                    self.app.root.after(0, lambda msg=error_msg: self.app.show_analysis_status(f"❌ {msg}", "red"))
                    continue
            
            # Faz tamamlandıktan sonra kullanıcıyı bilgilendir ve paneli güncelle
            self.app.root.after(0, lambda: self.app.project_panel.update_chapters(self.app.project_panel.chapters, preserve_selection=True))
            
            # Bir sonraki görevi kontrol et ve ona göre mesaj göster
            next_task = self._get_next_analysis_task()
            if not next_task:
                final_message = f"✅ {phase_name} analizi ve tüm analiz süreci tamamlandı!"
                self.app.root.after(0, lambda: messagebox.showinfo("Analiz Tamamlandı", "Tüm bölümlerin analizi başarıyla tamamlandı."))
                self.app.root.after(0, lambda: self.app.show_analysis_status(final_message, "green"))
            else:
                next_phase_name = self._get_phase_name(next_task[0])
                phase_complete_message = f"✅ {phase_name} analizi tamamlandı. Sonraki aşama ({next_phase_name}) için tekrar 'Tümünü Analiz Et'e tıklayın."
                self.app.root.after(0, lambda: self.app.show_analysis_status(phase_complete_message, "green"))

        except Exception as e:
            self.app.root.after(0, lambda: self._handle_thread_error(str(e)))
        finally:
            self.app.root.after(0, self.app.hide_progress)

    def _get_next_analysis_task(self):
        """Sıradaki analiz görevini (tür ve bölümler) belirler."""
        all_chapters = sorted(self.file_manager.chapters, key=lambda c: c.chapter_number)
        
        # 1. Dil Bilgisi Analizi
        grammar_chapters = [
            c for c in all_chapters 
            if not c.analysis_phases.get("grammar_completed") and not c.analysis_phases.get("grammar_failed")
        ]
        if grammar_chapters:
            return "grammar_check", grammar_chapters, "Dil Bilgisi"

        # 2. Üslup Analizi
        if self._has_pending_suggestions_for_any_chapter("grammar_check"):
            self.app.root.after(0, lambda: messagebox.showwarning("Bekleyen Öneriler", "Üslup analizine başlamadan önce tüm bölümlerdeki bekleyen 'Dil Bilgisi' önerilerini tamamlamanız gerekmektedir."))
            return None
        
        style_chapters = [
            c for c in all_chapters 
            if c.analysis_phases.get("grammar_completed") and \
               not c.analysis_phases.get("style_completed") and \
               not c.analysis_phases.get("style_failed")
        ]
        if style_chapters:
            return "style_analysis", style_chapters, "Üslup"

        # 3. İçerik Analizi
        if self._has_pending_suggestions_for_any_chapter("style_analysis"):
            self.app.root.after(0, lambda: messagebox.showwarning("Bekleyen Öneriler", "İçerik analizine başlamadan önce tüm bölümlerdeki bekleyen 'Üslup' önerilerini tamamlamanız gerekmektedir."))
            return None
            
        content_chapters = [
            c for c in all_chapters 
            if c.analysis_phases.get("style_completed") and \
               not c.analysis_phases.get("content_completed") and \
               not c.analysis_phases.get("content_failed")
        ]
        if content_chapters:
            return "content_review", content_chapters, "İçerik"

        return None

    def _has_pending_suggestions_for_any_chapter(self, analysis_type: str) -> bool:
        """Belirli bir analiz türü için herhangi bir bölümde bekleyen öneri olup olmadığını kontrol eder."""
        # Bu harita, AI'dan gelen 'editor_type' alanını hedefler.
        # EditorialSuggestion.type alanı daha genel olabilir.
        editor_type_map = {
            "grammar_check": "Dil Bilgisi Editörü",
            "style_analysis": "Üslup Editörü",
            "content_review": "İçerik Editörü"
        }
        target_editor_type = editor_type_map.get(analysis_type)
        if not target_editor_type:
            return False

        for chapter in self.file_manager.chapters:
            if hasattr(chapter, 'suggestions') and chapter.suggestions:
                for suggestion in chapter.suggestions:
                    # Öneri nesnesinin 'editor_type' özelliğine göre kontrol et
                    if hasattr(suggestion, 'editor_type') and suggestion.editor_type == target_editor_type:
                        print(f"Bekleyen '{target_editor_type}' önerisi bulundu: Bölüm {chapter.chapter_number}")
                        return True
        return False



    def display_suggestions(self, suggestions=None):
        # Mevcut öneri kartlarını temizle
        for widget in self.app.suggestions_frame.winfo_children():
            widget.destroy()
        
        # Yeni önerileri göster
        if suggestions is not None:
            # Gelen önerilerin dict mi yoksa nesne mi olduğunu kontrol et ve gerekirse dönüştür
            suggestion_objects = []
            for s in suggestions:
                if isinstance(s, dict):
                    # Eğer suggestion bir sözlük ise, onu EditorialSuggestion nesnesine dönüştür
                    suggestion_objects.append(EditorialSuggestion.from_dict(s))
                else:
                    # Zaten bir nesne ise, doğrudan ekle
                    suggestion_objects.append(s)
            
            # Artık suggestion_objects listesini kullanacağız
            suggestions = suggestion_objects
            
            # Mesaj etiketini gizle ve canvas/scrollbar'ı göster
            self.app.no_suggestions_label.place_forget()
            self.app.suggestions_canvas.pack(side="left", fill="both", expand=True)
            self.app.suggestions_scrollbar.pack(side="right", fill="y")

            successful_cards = 0
            failed_cards = 0
            print(f"📝 {len(suggestions)} öneri için SuggestionCard oluşturuluyor...")
            
            # Yatay düzen için container frame oluştur
            cards_container = ttk.Frame(self.app.suggestions_frame)
            cards_container.pack(fill=tk.BOTH, expand=True)
            
            # Özelleştirilebilir değerler
            cards_per_row = 3
            max_width = 350
            max_height = 400
            
            # Kartları satırlara dağıt
            current_row = None
            current_col = 0
            
            for i, suggestion in enumerate(suggestions):
                try:
                    if i % cards_per_row == 0:
                        current_row = ttk.Frame(cards_container)
                        current_row.pack(fill=tk.X, pady=5)
                        current_col = 0
                    
                    card_container = ttk.Frame(current_row, width=max_width, height=max_height)
                    card_container.pack(side=tk.LEFT, padx=5, fill=tk.BOTH, expand=True)
                    card_container.pack_propagate(False)
                    
                    print(f"📋 Öneri {i+1} kartı oluşturuluyor...")
                    card = SuggestionCard(card_container, suggestion, self.app.handle_suggestion)
                    card.pack(fill=tk.BOTH, expand=True, padx=3, pady=3)
                    
                    successful_cards += 1
                    current_col += 1
                    print(f"✅ Öneri {i+1} kartı başarıyla oluşturuldu")
                except Exception as card_error:
                    failed_cards += 1
                    print(f"❌ Öneri {i+1} kart oluşturma hatası: {card_error}")
                    import traceback
                    print(f"❌ Traceback: {traceback.format_exc()}")
                    
                    try:
                        if current_row is None:
                            current_row = ttk.Frame(cards_container)
                            current_row.pack(fill=tk.X, pady=5)
                        
                        error_container = ttk.Frame(current_row, width=max_width, height=100)
                        error_container.pack(side=tk.LEFT, padx=5, fill=tk.BOTH)
                        
                        error_label = ttk.Label(
                            error_container,
                            text=f"❌ Hatalı öneri {i+1}: {str(card_error)[:100]}...",
                            foreground="red",
                            wraplength=max_width-20
                        )
                        error_label.pack(fill=tk.X, pady=2)
                        current_col += 1
                        
                        if current_col >= cards_per_row:
                            current_row = None
                            current_col = 0
                    except Exception as label_error:
                        print(f"❌ Hata label'ı bile oluşturulamadı: {label_error}")
            
            print(f"📋 Sonuç: {successful_cards} başarılı, {failed_cards} başarısız kart")
            
            if successful_cards == 0 and failed_cards > 0:
                # If all cards failed, show a summary error in the scrollable frame
                error_summary_label = ttk.Label(
                    self.app.suggestions_frame,
                    text=f"❌ Tüm öneriler ({failed_cards}) gösterilemedi!\n\nLütfen Hata Ayıklama Konsolu'nu açarak hata detaylarını inceleyin.",
                    font=('Arial', 11),
                    foreground="red",
                    justify=tk.CENTER,
                    wraplength=500
                )
                error_summary_label.pack(expand=True, pady=20)
        else:
            # Hide the canvas/scrollbar and show the message label
            self.app.suggestions_canvas.pack_forget()
            self.app.suggestions_scrollbar.pack_forget()

            # Determine the message text and color
            current_chapter = self.app.project_panel.get_current_chapter()
            is_analyzed_at_all = False
            if current_chapter and hasattr(current_chapter, 'analysis_phases'):
                phases = current_chapter.analysis_phases
                if phases.get('grammar_completed') or phases.get('style_completed') or phases.get('content_completed'):
                    is_analyzed_at_all = True

            if is_analyzed_at_all:
                if current_chapter and hasattr(current_chapter, 'suggestion_history') and current_chapter.suggestion_history:
                     message_text = ("✅ Tüm öneriler işlendi!\n\n"
                                     "Sonraki analiz aşamasına geçebilir veya başka bir bölüm seçebilirsiniz.")
                else:
                    message_text = ("🎉 Bu bölüm için editöryal öneri bulunamadı!\n\n"
                                    "✨ Bu bölüm aşağıdaki durumlardan biri olabilir:\n"
                                    "• Çok iyi yazılmış ve düzeltmeye ihtiyaç duymuyor\n"
                                    "• YZ analizi herhangi bir sorun tespit edemedi\n"
                                    "• Bölüm içeriği çok kısa\n\n"
                                    "🔄 Sonraki analiz aşamasına geçebilir veya başka bir bölüm seçebilirsiniz.")
                message_color = "green"
            else:
                message_text = ("📋 Bu bölüm henüz analiz edilmedi.\n\n"
                                "Analizi başlatmak için aşağıdaki 'Dil Bilgisi Analizi' butonuna tıklayın.")
                message_color = "blue"

            # Configure and place the label
            self.app.no_suggestions_label.config(
                text=message_text,
                foreground=message_color
            )
            self.app.no_suggestions_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def handle_suggestion(self, suggestion=None, action=None, update_display=True):
        """Öneri kabul/red işlemleri - Kapsamlı geçmiş ve vurgulama bilgisi kaydetme ile"""
        # Handle None cases
        if suggestion is None or action is None:
            return None
            
        current_chapter = self.app.project_panel.get_current_chapter()
        
        # Güvenlik kontrolü - current_chapter None olabilir
        if not current_chapter:
            print("HATA: current_chapter None - öneri işlenemiyor")
            return None
            
        # suggestion'ın dict mi yoksa nesne mi olduğunu kontrol et
        is_dict = isinstance(suggestion, dict)

        suggestion_title = suggestion['title'] if is_dict else suggestion.title
        suggestion_id = suggestion.get('id', 'Bilinmiyor') if is_dict else getattr(suggestion, 'id', 'Bilinmiyor')
        editor_type = suggestion.get('editor_type', 'Bilinmiyor') if is_dict else getattr(suggestion, 'editor_type', 'Bilinmiyor')

        print(f"ÖNERİ İŞLENİYOR: {suggestion_title} ({action})")
        print(f"Bölüm: {current_chapter.title}")
        print(f"Öneri ID: {suggestion_id}")
        print(f"Editör: {editor_type}")
        
        # Öneriye işlem uygulanmış olarak işaretle
        if not is_dict:
            suggestion.action_taken = action
        else:
            suggestion['action_taken'] = action
        
        # Değişiklik öncesi durumu kaydet
        content_before = current_chapter.content if current_chapter else ""
        
        # Editorial process'e gönder
        result = self.editorial_process.handle_suggestion(suggestion, action, current_chapter)
        
        # Değişiklik sonrası durumu kontrol et
        content_after = current_chapter.content if current_chapter else ""
        content_changed = content_before != content_after
        
        # Eğer metin değiştirilemediyse kullanıcıyı bilgilendir ve kartı kaldırma
        if action == "apply" and not content_changed:
            messagebox.showinfo(
                "Bilgi",
                "Öneri uygulanamadı.\n\n"
                "Orijinal metin, muhtemelen daha önce uygulanan başka bir öneri tarafından değiştirilmiş."
            )
            return None  # Kartı kaldırmadan fonksiyondan çık
        
        # Kapsamlı öneri geçmişi oluştur
        history_entry = {
            'suggestion': {
                'id': suggestion.get('id', '') if is_dict else getattr(suggestion, 'id', ''),
                'type': suggestion.get('type', '') if is_dict else getattr(suggestion, 'type', ''),
                'title': suggestion.get('title', '') if is_dict else getattr(suggestion, 'title', ''),
                'editor_type': suggestion.get('editor_type', '') if is_dict else getattr(suggestion, 'editor_type', ''),
                'severity': suggestion.get('severity', '') if is_dict else getattr(suggestion, 'severity', ''),
                'model_name': suggestion.get('model_name', '') if is_dict else getattr(suggestion, 'model_name', '')
            },
            'action': action,
            'timestamp': datetime.datetime.now().isoformat(),
            'original_text': suggestion.get('original_sentence', '') if is_dict else getattr(suggestion, 'original_sentence', ''),
            'suggested_text': suggestion.get('suggested_sentence', '') if is_dict else getattr(suggestion, 'suggested_sentence', ''),
            'explanation': suggestion.get('explanation', '') if is_dict else getattr(suggestion, 'explanation', ''),
            'content_changed': content_changed,
            'content_length_before': len(content_before),
            'content_length_after': len(content_after)
        }
        
        # Eğer içerik değiştiyse, değişiklik detaylarını kaydet
        if content_changed and action == "apply" and current_chapter:
            original_sentence = suggestion.get('original_sentence', '') if is_dict else getattr(suggestion, 'original_sentence', '')
            suggested_sentence = suggestion.get('suggested_sentence', '') if is_dict else getattr(suggestion, 'suggested_sentence', '')
            editor_type_val = suggestion.get('editor_type', '') if is_dict else getattr(suggestion, 'editor_type', '')
            suggestion_id_val = suggestion.get('id', '') if is_dict else getattr(suggestion, 'id', '')

            change_entry = {
                'timestamp': datetime.datetime.now().isoformat(),
                'change_type': 'suggestion_applied',
                'editor_type': editor_type_val,
                'original_text': original_sentence,
                'new_text': suggested_sentence,
                'position_info': self._calculate_text_position(content_before, original_sentence),
                'suggestion_id': suggestion_id_val
            }
            if hasattr(current_chapter, 'content_changes'):
                current_chapter.content_changes.append(change_entry)
            else:
                current_chapter.content_changes = [change_entry]
            
            # Vurgulama bilgisi kaydet
            if hasattr(current_chapter, 'content_changes'):
                highlight_id = f"change_{len(current_chapter.content_changes)}"
            else:
                highlight_id = "change_1"
                
            if not hasattr(current_chapter, 'highlighting_info'):
                current_chapter.highlighting_info = {}
                
            severity_val = suggestion.get('severity', 'medium') if is_dict else getattr(suggestion, 'severity', 'medium')

            current_chapter.highlighting_info[highlight_id] = {
                'text': suggested_sentence,
                'original_text': original_sentence,
                'editor_type': editor_type_val,
                'severity': severity_val,
                'explanation': suggestion.get('explanation', '') if is_dict else getattr(suggestion, 'explanation', ''),
                'timestamp': datetime.datetime.now().isoformat(),
                'position': change_entry['position_info']
            }
        
        # Öneri geçmişine ekle
        if current_chapter:
            if not hasattr(current_chapter, 'suggestion_history'):
                current_chapter.suggestion_history = []
            current_chapter.suggestion_history.append(history_entry)
        
        # Proje değiştirildi olarak işaretle
        self.app.mark_as_modified()
        
        # Eğer metin değiştirildi ise önizlemeyi güncelle
        if action == "apply" and current_chapter:
            print(f"DEBUG - Önce bölüm uzunluğu: {len(content_before)} karakter")
            print(f"DEBUG - Öneri uygulama durumu: {result}")
            print(f"DEBUG - Son değişiklik zamanı: {getattr(current_chapter, 'last_modified', 'YOK')}")
            if hasattr(current_chapter, 'content_changes'):
                print(f"DEBUG - Toplam değişiklik sayısı: {len(current_chapter.content_changes)}")
            self.app.display_chapter_content(current_chapter)
            print(f"DEBUG - Sonra bölüm uzunluğu: {len(content_after)} karakter")
            
        # Durum mesajı göster
        if action == "apply":
            self.app.show_analysis_status(f"✅ Öneri uygulandı ve kaldırıldı: {suggestion_title}", "green")
        elif action == "reject":
            self.app.show_analysis_status(f"❌ Öneri reddedildi ve kaldırıldı: {suggestion_title}", "orange")
            
        # Öneriyi aktif listeden kaldır
        self.remove_suggestion_from_display(suggestion, update_display=update_display)
        
        # Faz tamamlanma kontrolünü yap
        self.check_phase_completion()
        
        # İstatistikleri ve önizlemeyi güncelle
        if current_chapter:
            self.app.project_panel.update_statistics()
            self.app.project_panel.update_preview(current_chapter)
        
        return None

    def _calculate_text_position(self, content: str, target_text: str) -> dict:
        """Metindeki değişikliğin pozisyonunu hesapla"""
        try:
            position = content.find(target_text)
            if position == -1:
                return {'found': False, 'position': -1, 'line': -1, 'column': -1}
            
            # Satır ve sütun hesapla
            lines_before = content[:position].count('\n')
            line_start = content.rfind('\n', 0, position) + 1
            column = position - line_start
            
            return {
                'found': True,
                'position': position,
                'line': lines_before + 1,
                'column': column + 1,
                'length': len(target_text)
            }
        except Exception as e:
            print(f"Pozisyon hesaplama hatası: {e}")
            return {'found': False, 'error': str(e)}

    def remove_suggestion_from_display(self, processed_suggestion, update_display=True):
        """İşlenmiş öneriyi görünümden kaldır"""
        current_chapter = self.app.project_panel.get_current_chapter()
        if not (current_chapter and hasattr(current_chapter, 'suggestions')):
            return

        # İşlenmiş öneriyi listeden çıkar
        processed_id = processed_suggestion['id'] if isinstance(processed_suggestion, dict) else processed_suggestion.id
        remaining_suggestions = [
            s for s in current_chapter.suggestions
            if (s['id'] if isinstance(s, dict) else s.id) != processed_id
        ]
        current_chapter.suggestions = remaining_suggestions
        
        # YENİ: Pending listesinden de çıkar - GÜÇLENDİRİLMİŞ VERSİYON
        if current_chapter and hasattr(current_chapter, 'pending_suggestions'):
            original_count = len(current_chapter.pending_suggestions)
            processed_id = processed_suggestion['id'] if isinstance(processed_suggestion, dict) else processed_suggestion.id
            current_chapter.pending_suggestions = [
                s for s in current_chapter.pending_suggestions
                if (s.get('id', '') if isinstance(s, dict) else getattr(s, 'id', '')) != processed_id
            ]
            new_count = len(current_chapter.pending_suggestions)
            print(f"📋 Öneri pending listesinden de çıkarıldı. Önceki: {original_count}, Sonra: {new_count}")
            
            # Kalıcı kayıt için mark as modified
            self.app.mark_as_modified()
            
            # Eğer hiç pending öneri kalmadıysa durum mesajını güncelle
            if new_count == 0:
                self.app.show_analysis_status(
                    f"✅ {current_chapter.title} - Tüm öneriler işlendi!", 
                    "green"
                )
        
        if update_display:
            # Görünümü güncelle
            self.app.display_suggestions(remaining_suggestions)

    def show_suggestion_history(self):
        """Öneri geçmişini göster"""
        current_chapter = self.app.project_panel.get_current_chapter()
        
        # Güvenlik kontrolü - current_chapter None olabilir
        if not current_chapter:
            messagebox.showinfo("Geçmiş", "Bölüm seçilmedi.")
            return
            
        if not hasattr(current_chapter, 'suggestion_history') or not current_chapter.suggestion_history:
            messagebox.showinfo("Geçmiş", "Bu bölümde henüz işlenmiş bir öneri bulunmuyor.")
            return
            
        history_window = tk.Toplevel(self.app.root)
        history_window.title(f"Öneri Geçmişi - {current_chapter.title}")
        history_window.geometry("800x600")
        
        # Metin alanı
        text_frame = ttk.Frame(history_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        history_text = tk.Text(text_frame, wrap=tk.WORD, font=('Arial', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=history_text.yview)
        history_text.configure(yscrollcommand=scrollbar.set)
        
        history_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Geçmiş içeriğini yaz
        history_content = f"=== {current_chapter.title} - Öneri Geçmişi ===\n\n"
        
        if hasattr(current_chapter, 'suggestion_history') and current_chapter.suggestion_history:
            for i, entry in enumerate(current_chapter.suggestion_history, 1):
                action_text = "✅ UYGULANDI" if entry['action'] == 'apply' else "❌ REDDEDİLDİ"
                history_content += f"{i}. {action_text} - {entry['timestamp']}\n"
                history_content += f"Orijinal: {entry['original_text'][:100]}...\n"
                history_content += f"Önerilen: {entry['suggested_text'][:100]}...\n"
                history_content += f"Açıklama: {entry['explanation'][:150]}...\n"
                history_content += "-" * 60 + "\n\n"
        
        if not (hasattr(current_chapter, 'suggestion_history') and current_chapter.suggestion_history):
            history_content += "Henüz işlenmiş öneri bulunmuyor."
            
        history_text.insert('1.0', history_content)
        history_text.config(state='disabled')
        
        # Kapat butonu
        ttk.Button(history_window, text="Kapat", command=history_window.destroy).pack(pady=10)

    def next_chapter(self):
        self.app.project_panel.next_chapter()

    def prev_chapter(self):
        self.app.project_panel.prev_chapter()

    def apply_all_suggestions(self):
        """Mevcut bölümdeki tüm bekleyen önerileri uygular (donmayı önlemek için aşamalı)."""
        current_chapter = self.app.project_panel.get_current_chapter()
        if not current_chapter or not hasattr(current_chapter, 'suggestions') or not current_chapter.suggestions:
            messagebox.showinfo("Bilgi", "Uygulanacak bir öneri bulunmuyor.")
            return

        suggestions_to_apply = current_chapter.suggestions[:]
        total_count = len(suggestions_to_apply)

        response = messagebox.askyesno(
            "Tümünü Uygula",
            f"Bu bölümdeki {total_count} önerinin tümünü uygulamak istediğinizden emin misiniz?\n\n"
            "Bu işlem geri alınamaz."
        )

        if not response:
            return

        # Progress bar'ı göster ve işlemi başlat
        self.app.show_progress(f"Öneriler uygulanıyor... (0/{total_count})")
        self.app.root.after(100, self._apply_suggestion_step, suggestions_to_apply, 0, current_chapter)

    def _apply_suggestion_step(self, suggestions_copy, index, chapter):
        """Tümünü uygulama işleminin bir adımını gerçekleştirir."""
        if index >= len(suggestions_copy):
            # İşlem tamamlandı
            self.app.hide_progress()
            self.app.show_analysis_status(f"✅ {len(suggestions_copy)} önerinin tümü uygulandı.", "green")
            # Son bir kez UI'yı yenile
            self.app.display_chapter_content(chapter)
            self.app.project_panel.update_preview(chapter)
            self.app.display_suggestions(chapter.suggestions) # Should be empty now
            return

        # Bir öneriyi işle
        suggestion = suggestions_copy[index]
        self.app.handle_suggestion(suggestion, "apply", update_display=False)

        # Progress bar'ı güncelle
        progress_message = f"Öneriler uygulanıyor... ({index + 1}/{len(suggestions_copy)})"
        self.app.progress_label.config(text=progress_message)

        # Bir sonraki adımı zamanla
        self.app.root.after(5, self._apply_suggestion_step, suggestions_copy, index + 1, chapter)

    def chapter_split_callback(self, content=None):
        # Handle None case
        if content is None:
            return
            
        # Bölümlere ayırma penceresi
        split_window = tk.Toplevel(self.app.root)
        split_window.title("Bölümlere Ayırma")
        split_window.geometry("500x400")
        split_window.grab_set()
        
        ttk.Label(split_window, text="Bölümlere nasıl ayırmak istiyorsunuz?", font=('Arial', 12)).pack(pady=10)
        
        split_method = tk.StringVar(value="number_only")
        
        ttk.Radiobutton(split_window, text="Sadece sayı olan satırlar", variable=split_method, value="number_only").pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(split_window, text="Belirli kelimeler", variable=split_method, value="keywords").pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(split_window, text="Özel kelime gir", variable=split_method, value="custom").pack(anchor=tk.W, padx=20)
        
        # Özel kelime girişi
        custom_frame = ttk.Frame(split_window)
        custom_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(custom_frame, text="Özel kelime:").pack(anchor=tk.W)
        custom_entry = ttk.Entry(custom_frame)
        custom_entry.pack(fill=tk.X, pady=5)
        
        def apply_split():
            method = split_method.get()
            custom_word = custom_entry.get() if method == "custom" else None
            
            chapters = self.file_manager.split_into_chapters(content, method, custom_word)
            if chapters:
                self.app.project_panel.update_chapters(chapters)
                split_window.destroy()
                
                # Durum mesajını güncelle
                self.app.show_analysis_status(
                    f"✅ {len(chapters)} bölüm başarıyla yüklendi! 📋 Sol panelden bir bölüm seçin ve analiz başlatın.", 
                    "green"
                )
                
                messagebox.showinfo("Başarı", f"{len(chapters)} bölüm oluşturuldu.")
            else:
                messagebox.showerror("Hata", "Bölüm oluşturulamadı.")
        
        ttk.Button(split_window, text="Uygula", command=apply_split).pack(pady=20)

    def on_chapter_selection_changed(self):
        """Bölüm seçimi değiştiğinde çağrılır"""
        current_chapter = self.app.project_panel.get_current_chapter()
        
        # Yeni bölüm seçildiyse analiz durumunu yükle
        if current_chapter and current_chapter != self.app.current_analyzing_chapter:
            self.load_chapter_analysis_state(current_chapter)
        
        self.app.display_chapter_content(current_chapter)
        
        # Önizleme panelini de güncelle - çok önemli!
        if current_chapter:
            # İlk önizleme güncellemesi
            self.app.project_panel.update_preview(current_chapter)
            # Gecikmeli ikinci güncelleme - UI senkronizasyon sorunu için
            self.app.root.after(50, lambda: self.app.project_panel.update_preview(current_chapter))
        
        # Bekleyen önerileri bölümün 'suggestions' listesinden yükle
        if current_chapter and hasattr(current_chapter, 'suggestions'):
            suggestions = current_chapter.suggestions
            if suggestions:
                print(f"📝 Bölüm {current_chapter.chapter_number} için {len(suggestions)} bekleyen öneri görüntüleniyor")
                self.app.display_suggestions(suggestions)
                self.app.show_analysis_status(
                    f"📋 {current_chapter.title} seçildi - {len(suggestions)} bekleyen öneri mevcut", 
                    "green"
                )
            else:
                # 'suggestions' listesi var ama boş
                print(f"📂 Bölüm {current_chapter.chapter_number} - Bekleyen öneri yok (boş liste)")
                self.app.display_suggestions([])
        else:
            # 'suggestions' özelliği yok veya bölüm seçilmemiş
            if current_chapter:
                print(f"📂 Bölüm {current_chapter.chapter_number} - Henüz analiz edilmemiş veya öneri bulunmuyor")
            else:
                print(f"📂 Hiç bölüm seçilmemiş")
            self.app.display_suggestions([])
            
            # Durum mesajını güncelle
            if current_chapter:
                self.app.show_analysis_status(
                    f"📚 {current_chapter.title} seçildi - 'Analiz Başlat' butonuna tıklayarak analiz edebilirsiniz", 
                    "blue"
                )

    def open_debug_console(self):
        """Debug konsolunu açar"""
        debug_window = tk.Toplevel(self.app.root)
        debug_window.title("Hata Ayıklama Konsolu")
        debug_window.geometry("800x600")
        
        # Text area with scrollbar
        text_frame = ttk.Frame(debug_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        debug_text = tk.Text(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=debug_text.yview)
        debug_text.configure(yscrollcommand=scrollbar.set)
        
        debug_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add console output
        if hasattr(self.app, 'console_output') and self.app.console_output:
            for line in self.app.console_output:
                debug_text.insert(tk.END, line + '\n')
        else:
            debug_text.insert(tk.END, "Konsol çıktısı bulunamadı.\n")
        
        debug_text.config(state='disabled')
        
        # Button frame
        button_frame = ttk.Frame(debug_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def clear_console():
            self.app.console_output = []
            debug_text.config(state='normal')
            debug_text.delete('1.0', tk.END)
            debug_text.config(state='disabled')
        
        ttk.Button(button_frame, text="Konsolu Temizle", command=clear_console).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Kapat", command=debug_window.destroy).pack(side=tk.RIGHT)

    def check_project_status(self):
        """Proje durumunu kontrol eder"""
        try:
            # Toplam bölüm sayısı
            total_chapters = len(self.file_manager.chapters) if self.file_manager.chapters else 0
            
            # İşlenmiş bölüm sayısı
            processed_chapters = len(self.editorial_process.processed_chapters) if hasattr(self.editorial_process, 'processed_chapters') else 0
            
            # Bekleyen öneriler
            pending_suggestions = 0
            if self.file_manager.chapters:
                for chapter in self.file_manager.chapters:
                    if hasattr(chapter, 'suggestions') and chapter.suggestions:
                        pending_suggestions += len(chapter.suggestions)
            
            # Konsol çıktısı satır sayısı
            console_lines = len(self.app.console_output) if hasattr(self.app, 'console_output') else 0
            
            # Durum mesajı
            status_message = f"📊 Proje Durumu:\n"
            status_message += f"  📚 Toplam Bölüm: {total_chapters}\n"
            status_message += f"  ✅ İşlenmiş Bölüm: {processed_chapters}\n"
            status_message += f"  📋 Bekleyen Öneri: {pending_suggestions}\n"
            status_message += f"  🖥️  Konsol Çıktısı: {console_lines} satır\n"
            
            # AI durumu
            api_key = self.settings_manager.get_setting("api_key", "")
            model = self.settings_manager.get_setting("model", "gemini-1.5-flash")
            status_message += f"\n🤖 YZ Durumu:\n"
            status_message += f"  🔑 API Anahtarı: {'✅ Ayarlanmış' if api_key else '❌ Ayarlanmamış'}\n"
            status_message += f"  🧠 Model: {model}\n"
            
            # Otomatik kaydetme durumu
            auto_save_enabled = self.settings_manager.get_setting('auto_save', True)
            auto_save_interval = self.settings_manager.get_setting('auto_save_interval', 5.0)
            status_message += f"\n💾 Otomatik Kaydetme:\n"
            status_message += f"  ⚙️  Durum: {'✅ Etkin' if auto_save_enabled else '❌ Devre dışı'}\n"
            status_message += f"  ⏱️  Aralık: {auto_save_interval} dakika\n"
            
            if hasattr(self.app, 'last_auto_save_time') and self.app.last_auto_save_time:
                status_message += f"  🕒 Son Kayıt: {self.app.last_auto_save_time.strftime('%H:%M:%S')}\n"
            
            messagebox.showinfo("Proje Durumu", status_message)
            
        except Exception as e:
            messagebox.showerror("Hata", f"Proje durumu kontrol edilirken bir hata oluştu:\n{str(e)}")
