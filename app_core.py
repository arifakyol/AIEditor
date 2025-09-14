import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import datetime
import threading
import time
from typing import Optional, Any, Callable, Union

# Import modules
from modules.file_manager import FileManager
from modules.ai_integration import AIIntegration
from modules.editorial_process import EditorialProcess
from modules.settings_manager import SettingsManager
from modules.ui_components import SuggestionCard, ProjectPanel

# Manager classes
from ui_manager import UIManager
from ai_manager import AIManager
from file_operations import FileOperationsManager
from auto_save_manager import AutoSaveManager
from analysis_manager import AnalysisManager

class EditorialApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Editöryal Süreç Yöneticisi")
        self.root.geometry("1200x800")
        
        # Capture console output
        self.console_output = []
        self.original_print = print
        
        # Track unsaved changes
        self.has_unsaved_changes = False
        self.last_auto_save_time = None
        
        # Sequential analysis state tracking
        self.current_analysis_phase = "yok"  # yok, dilbilgisi, üslup, içerik
        self.analysis_button = None
        self.current_analyzing_chapter = None
        
        # UI components
        self.project_panel: Optional[ProjectPanel] = None
        self.status_message_label: Optional[ttk.Label] = None
        self.progress_frame: Optional[ttk.Frame] = None
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.progress_label: Optional[ttk.Label] = None
        self.chapter_content_text: Optional[tk.Text] = None
        self.suggestions_canvas: Optional[tk.Canvas] = None
        self.suggestions_scrollbar: Optional[ttk.Scrollbar] = None
        self.suggestions_scrollable_frame: Optional[ttk.Frame] = None
        self.suggestions_frame: Optional[ttk.Frame] = None
        self.no_suggestions_label: Optional[ttk.Label] = None
        self.tooltip_label: Optional[tk.Toplevel] = None
        
        # Managers
        self.settings_manager = SettingsManager()
        self.file_manager = FileManager()
        self.ai_integration = AIIntegration(self.settings_manager)
        self.editorial_process = EditorialProcess()
        
        # Manager references (will be set in main.py)
        self.ui_manager: Optional[UIManager] = None
        self.ai_manager: Optional[AIManager] = None
        self.file_ops_manager: Optional[FileOperationsManager] = None
        self.auto_save_manager: Optional[AutoSaveManager] = None
        self.analysis_manager: Optional[AnalysisManager] = None
        
        # Initialize AI with individual models
        self.initialize_ai_integration()
        
        # Console capture
        self.setup_console_capture()
        
        # Capture application closing event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_current_chapter(self):
        """Returns the currently selected chapter from the project panel."""
        if self.project_panel:
            return self.project_panel.get_current_chapter()
        return None

    def initialize_ai_integration(self):
        """Initialize AI integration with settings"""
        api_key = self.settings_manager.get_setting("api_key", "")
        default_model = self.settings_manager.get_setting("model", "gemini-1.5-flash")
        
        # Define default model settings
        default_individual_models = {
            "style_analysis": "gemini-1.5-flash",
            "grammar_check": "gemini-1.5-flash",
            "content_review": "gemini-1.5-flash",
            "novel_context": "gemini-1.5-pro"
        }
        # Load saved settings
        saved_individual_models = self.settings_manager.get_setting("individual_models", {})
        
        # Merge defaults with saved (saved take precedence)
        # This allows new models to be added to old settings files.
        individual_models = {**default_individual_models, **saved_individual_models}
        
        if api_key:
            print(f"Yapay zeka entegrasyonu başlatılıyor: Varsayılan model={default_model}")
            print(f"Bireysel modeller: {individual_models}")
            self.ai_integration.update_settings(api_key, default_model, individual_models)

    def load_project_state(self):
        # Load last state when application starts
        
        # Check project status and offer selection
        self.root.after(500, self._check_and_offer_project_selection)

    def _check_and_offer_project_selection(self):
        """Offer project selection when application opens"""
        try:
            # Check existing projects
            projects = self.settings_manager.get_project_list()
            
            if not projects:
                # No projects, leave empty
                # Status message will be shown in UI manager
                return
            
            # Check last used project
            last_project = self.settings_manager.get_setting('last_project')
            
            # If last project exists, load automatically
            if last_project and os.path.exists(last_project):
                try:
                    self._load_project_file(last_project)
                    return
                except Exception as e:
                    print(f"Son proje otomatik yüklenemedi: {e}")
            
            # Show project selection window
            # This will be handled by UI manager
            
        except Exception as e:
            print(f"Başlangıç proje kontrol hatası: {e}")

    def on_closing(self):
        """Uygulama kapatılırken çağrılır - Otomatik kaydetme ve onay sistemi"""
        try:
            # Kaydedilmemiş değişiklikleri kontrol et
            if self.has_unsaved_changes or self._check_for_unsaved_work():
                # Kullanıcıya seçenekler sun
                response = messagebox.askyesnocancel(
                    "Uygulamayı Kapat",
                    "💾 Kaydedilmemiş değişiklikleriniz var!\n\n"
                    "📝 Projenizi kaydetmek istiyor musunuz?\n\n"
                    "• EVET: Kaydet ve çık\n"
                    "• HAYIR: Kaydetmeden çık (değişiklikler kaybolacak!)\n"
                    "• İPTAL: Uygulamaya geri dön"
                )
                
                if response is True:  # EVET - Kaydet ve çık
                    print("Kullanıcı kaydetmeyi ve çıkmayı seçti")
                    success = self._perform_final_save()
                    if success:
                        print("Son kaydetme başarılı - Uygulama kapatılıyor")
                        self.root.destroy()
                    else:
                        messagebox.showerror("Kaydetme Hatası",
                                           "Proje kaydedilemedi! Lütfen manuel olarak kaydetmeyi deneyin.")
                        return
                        
                elif response is False:  # HAYIR - Kaydetmeden çık
                    # Son onay
                    final_confirm = messagebox.askyesno(
                        "Son Onay",
                        "⚠️ TÜM DEĞİŞİKLİKLERİNİZ KAYBOLACAK!\n\n"
                        "Kaydetmeden çıkmak istediğinizden emin misiniz?"
                    )
                    if final_confirm:
                        print("Kullanıcı kaydetmeden çıkmayı onayladı")
                        self.root.destroy()
                    else:
                        return  # Uygulamaya geri dön
                        
                else:  # İPTAL veya pencere kapatıldı
                    print("Kullanıcı çıkışı iptal etti")
                    return  # Hiçbir şey yapma
                    
            else:
                # Kaydedilmemiş değişiklik yok - doğrudan çık
                print("Kaydedilmemiş değişiklik yok - temiz çıkış")
                self.root.destroy()
                
        except Exception as e:
            print(f"Uygulama kapatılırken hata: {e}")
            # Hata durumunda seçenek sun
            emergency_response = messagebox.askyesno(
                "Hata Oluştu",
                f"Uygulama kapatılırken hata oluştu:\n{e}\n\n"
                "Yine de uygulamayı kapatmak istiyor musunuz?"
            )
            if emergency_response:
                self.root.destroy()

    def _check_for_unsaved_work(self) -> bool:
        """Check if there's unsaved work"""
        # Bu fonksiyonun asıl amacı, `has_unsaved_changes` bayrağını desteklemektir.
        # Bir proje yüklendiğinde, geçmiş verileri (suggestion_history vb.) olabilir
        # ama bu, kaydedilmemiş yeni bir değişiklik olduğu anlamına gelmez.
        # Bu nedenle, kontrolü doğrudan `has_unsaved_changes` bayrağına dayandırmak en güvenlisidir.
        return self.has_unsaved_changes

    def _perform_final_save(self) -> bool:
        """Uygulamayı kapatırken son kaydetme işlemini gerçekleştir"""
        try:
            print("Son kaydetme başlatılıyor...")
            
            # Proje yoksa, otomatik olarak bir tane oluştur
            last_project = self.settings_manager.get_setting('last_project')
            if not last_project:
                import datetime
                auto_project_name = f"Otomatik_Kayit_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                project_file = self.settings_manager.create_project(auto_project_name)
                if project_file:
                    self.settings_manager.set_setting('last_project', project_file)
                    print(f"Acil durum projesi oluşturuldu: {project_file}")
                else:
                    print("Acil durum projesi oluşturulamadı")
                    return False
            
            # Projeyi kaydet
            success = self.settings_manager.save_project_state(
                self.file_manager.get_state(),
                self.editorial_process.get_state(),
                self.project_panel.get_state() if self.project_panel else {}
            )
            
            if success:
                print("Son kaydetme başarılı")
                self.has_unsaved_changes = False
                return True
            else:
                print("Son kaydetme başarısız oldu")
                return False
                
        except Exception as e:
            print(f"Son kaydetme hatası: {e}")
            return False

    def mark_as_modified(self):
        """Mark project as modified"""
        self.has_unsaved_changes = True
        
        # Add * to window title
        current_title = self.root.title()
        if not current_title.endswith('*'):
            self.root.title(current_title + ' *')

    def mark_as_saved(self):
        """Mark project as saved"""
        self.has_unsaved_changes = False
        
        # Remove * from window title
        current_title = self.root.title()
        if current_title.endswith(' *'):
            self.root.title(current_title[:-2])

    def run(self):
        """Uygulamayı çalıştır - Klavye kesintisi yönetimi ile"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n🚫Klavye Kesintisi algılandı - Uygulama güvenli bir şekilde kapatılıyor...")
            self.on_closing()
        except Exception as e:
            print(f"\n❌ Beklenmedik hata: {e}")
            import traceback
            print(f"Hata detayları: {traceback.format_exc()}")
            self.on_closing()

    def setup_console_capture(self):
        """Set up console output capture"""
        def custom_print(*args, **kwargs):
            # Call original print
            self.original_print(*args, **kwargs)
            
            # Add to console output list
            output = ' '.join(str(arg) for arg in args)
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            self.console_output.append(f"[{timestamp}] {output}")
            
            # Keep maximum 1000 lines
            if len(self.console_output) > 1000:
                self.console_output = self.console_output[-1000:]
        
        # Replace print function
        import builtins
        builtins.print = custom_print
        
    # These methods will be dynamically assigned in main.py
    def _load_project_file(self, project_file: str = "") -> bool:
        """Load project file"""
        # This method will be redirected to FileOperationsManager in main.py
        if self.file_ops_manager is not None and hasattr(self.file_ops_manager, '_load_project_file'):
            return self.file_ops_manager._load_project_file(project_file)
        return False
        
    def setup_auto_save(self):
        """Set up auto-save system"""
        # This method will be redirected to AutoSaveManager in main.py
        if self.auto_save_manager is not None and hasattr(self.auto_save_manager, 'setup_auto_save'):
            self.auto_save_manager.setup_auto_save()

    # Placeholder methods for dynamically assigned functions
    def load_novel(self):
        if self.file_ops_manager is not None and hasattr(self.file_ops_manager, 'load_novel'):
            self.file_ops_manager.load_novel()
    
    def save_project(self, save_reason: str = 'manual'):
        if self.file_ops_manager is not None and hasattr(self.file_ops_manager, 'save_project'):
            self.file_ops_manager.save_project(save_reason=save_reason)
    
    def load_project(self):
        if self.file_ops_manager is not None and hasattr(self.file_ops_manager, 'load_project'):
            self.file_ops_manager.load_project()
    
    def load_project_history(self):
        if self.file_ops_manager is not None and hasattr(self.file_ops_manager, 'load_project_history'):
            self.file_ops_manager.load_project_history()

    def export_as_txt(self):
        if self.file_ops_manager is not None and hasattr(self.file_ops_manager, 'export_as_txt'):
            self.file_ops_manager.export_as_txt()
    
    def export_as_docx(self):
        if self.file_ops_manager is not None and hasattr(self.file_ops_manager, 'export_as_docx'):
            self.file_ops_manager.export_as_docx()
    
    def open_ai_settings(self):
        if self.ai_manager is not None and hasattr(self.ai_manager, 'open_ai_settings'):
            self.ai_manager.open_ai_settings()
    
    def open_prompt_settings(self):
        if self.ai_manager is not None and hasattr(self.ai_manager, 'open_prompt_settings'):
            self.ai_manager.open_prompt_settings()
    
    def update_prompts(self, new_prompts: dict):
        """Prompt'ları hem AI entegrasyonunda hem de ayarlarda günceller."""
        if self.ai_integration:
            self.ai_integration.update_prompts(new_prompts)
            print("Çalışma zamanı prompt'ları güncellendi.")
        
        if self.settings_manager:
            self.settings_manager.set_setting('prompts', new_prompts)
            print("Prompt ayarları kalıcı olarak kaydedildi.")
        
        self.mark_as_modified()
    
    def show_novel_context(self):
        if self.ai_manager is not None and hasattr(self.ai_manager, 'show_novel_context'):
            self.ai_manager.show_novel_context()
    
    def open_auto_save_settings(self):
        if self.auto_save_manager is not None and hasattr(self.auto_save_manager, 'open_auto_save_settings'):
            self.auto_save_manager.open_auto_save_settings()
    
    def start_analysis(self, novel_context: Optional[str] = None, full_novel_content: Optional[str] = None):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'start_analysis'):
            # Pass the context arguments to the analysis manager
            self.analysis_manager.start_analysis(novel_context=novel_context, full_novel_content=full_novel_content)
    
    def next_chapter(self):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'next_chapter'):
            self.analysis_manager.next_chapter()
    
    def prev_chapter(self):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'prev_chapter'):
            self.analysis_manager.prev_chapter()
    
    def apply_all_suggestions(self):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'apply_all_suggestions'):
            self.analysis_manager.apply_all_suggestions()
    
    def show_suggestion_history(self):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'show_suggestion_history'):
            self.analysis_manager.show_suggestion_history()
    
    def display_suggestions(self, suggestions=None):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'display_suggestions'):
            self.analysis_manager.display_suggestions(suggestions or [])
    
    def handle_suggestion(self, suggestion=None, action=None, update_display=True):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'handle_suggestion'):
            self.analysis_manager.handle_suggestion(suggestion, action, update_display)
        return None
    
    def check_project_status(self):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'check_project_status'):
            self.analysis_manager.check_project_status()
    
    def open_debug_console(self):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'open_debug_console'):
            self.analysis_manager.open_debug_console()
    
    def display_chapter_content(self, chapter=None):
        if self.ui_manager is not None and hasattr(self.ui_manager, 'display_chapter_content'):
            self.ui_manager.display_chapter_content(chapter)
    
    def show_analysis_status(self, message: str = "", color: str = "black"):
        if self.ui_manager is not None and hasattr(self.ui_manager, 'show_analysis_status'):
            self.ui_manager.show_analysis_status(message, color)
    
    def show_progress(self, message: str = ""):
        if self.ui_manager is not None and hasattr(self.ui_manager, 'show_progress'):
            self.ui_manager.show_progress(message)
    
    def hide_progress(self):
        if self.ui_manager is not None and hasattr(self.ui_manager, 'hide_progress'):
            self.ui_manager.hide_progress()
    
    def _auto_save_timer(self):
        # This will be implemented in auto_save_manager
        pass
    
    def _restart_auto_save_timer(self):
        # This will be implemented in auto_save_manager
        pass
    
    def on_chapter_selection_changed(self):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'on_chapter_selection_changed'):
            self.analysis_manager.on_chapter_selection_changed()
    
    def chapter_split_callback(self, content=None):
        if self.analysis_manager is not None and hasattr(self.analysis_manager, 'chapter_split_callback'):
            self.analysis_manager.chapter_split_callback(content)
    
    def _has_pending_suggestions(self) -> bool:
        # This will be implemented in analysis_manager
        if self.analysis_manager is not None and hasattr(self.analysis_manager, '_has_pending_suggestions'):
            return self.analysis_manager._has_pending_suggestions()
        return False

    def reset_project_state(self):
        """Resets the current project state to start fresh."""
        print("Project state is being reset.")
        # Clear last project setting
        self.settings_manager.set_setting('last_project', None)
        
        # Clear data managers
        self.file_manager.chapters = []
        self.file_manager.novel_title = ""
        self.editorial_process.reset_state()
        
        # Reset UI components
        if self.project_panel:
            self.project_panel.update_chapters([])
        if self.chapter_content_text:
            self.chapter_content_text.config(state='normal')
            self.chapter_content_text.delete('1.0', tk.END)
            self.chapter_content_text.config(state='disabled')
        if self.analysis_manager:
            self.analysis_manager.display_suggestions([]) # Clear suggestions
        
        # Reset analysis phase
        self.current_analysis_phase = "none"
        if self.analysis_manager:
            self.analysis_manager.update_analysis_button(self.current_analysis_phase)

        # Mark as saved to remove '*' from title
        self.mark_as_saved()
        print("Project state has been successfully reset.")
