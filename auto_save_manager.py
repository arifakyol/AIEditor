import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import datetime
import threading
import time

# Import modules
from modules.file_manager import FileManager
from modules.ai_integration import AIIntegration
from modules.editorial_process import EditorialProcess
from modules.settings_manager import SettingsManager
from modules.ui_components import SuggestionCard, ProjectPanel

class AutoSaveManager:
    def __init__(self, app):
        self.app = app
        self.settings_manager = app.settings_manager
        self.file_manager = app.file_manager
        self.editorial_process = app.editorial_process
        # Don't access project_panel here, it's not created yet
        self.project_panel = None

    def set_project_panel(self, project_panel):
        """Set the project panel after it's created"""
        self.project_panel = project_panel

    def open_auto_save_settings(self):
        """Otomatik kaydetme ayarları penceresi"""
        auto_save_window = tk.Toplevel(self.app.root)
        auto_save_window.title("Otomatik Kaydetme Ayarları")
        auto_save_window.geometry("450x650")  # Yükseklik artırıldı
        auto_save_window.grab_set()
        
        # Ana çerçeve
        main_frame = ttk.Frame(auto_save_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Başlık
        ttk.Label(main_frame, text="Otomatik Kaydetme Ayarları", font=('Arial', 14, 'bold')).pack(pady=(0, 20))
        
        # Projeler dizini ayarı
        projects_dir_frame = ttk.LabelFrame(main_frame, text="Projeler Dizini", padding=10)
        projects_dir_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Mevcut projeler dizini
        current_dir = self.settings_manager.get_setting('projects_directory') or self.settings_manager.projects_dir
        ttk.Label(projects_dir_frame, text="Mevcut dizin:").pack(anchor=tk.W)
        
        dir_label = ttk.Label(projects_dir_frame, text=current_dir, font=('Arial', 9), foreground="blue")
        dir_label.pack(anchor=tk.W, pady=(0, 10))
        
        def change_projects_directory():
            """Projeler dizinini değiştir"""
            new_dir = filedialog.askdirectory(
                title="Projeler Dizinini Seçin",
                initialdir=current_dir
            )
            
            if new_dir and os.path.exists(new_dir):
                # Dizini doğrula
                if self.settings_manager.set_projects_directory(new_dir):
                    dir_label.config(text=new_dir)
                    messagebox.showinfo("Başarılı", "Projeler dizini başarıyla güncellendi!")
                else:
                    messagebox.showerror("Hata", "Projeler dizini güncellenemedi.")
            elif new_dir:  # Dizin mevcut değil
                messagebox.showerror("Hata", "Seçilen dizin mevcut değil.")
        
        ttk.Button(projects_dir_frame, text="Dizini Değiştir", command=change_projects_directory).pack(anchor=tk.W)
        
        # Genel ayarlar
        auto_save_frame = ttk.LabelFrame(main_frame, text="Genel Ayarlar", padding=10)
        auto_save_frame.pack(fill=tk.X, pady=(0, 15))
        
        auto_save_enabled = tk.BooleanVar(value=self.settings_manager.get_setting('auto_save', True))
        ttk.Checkbutton(auto_save_frame, text="Otomatik kaydetmeyi etkinleştir",
                       variable=auto_save_enabled).pack(anchor=tk.W)
        
        # Açıklama
        info_text = "Otomatik kaydetme, projenizi düzenli aralıklarla otomatik olarak kaydeder."
        ttk.Label(auto_save_frame, text=info_text, font=('Arial', 9),
                 foreground="gray", wraplength=400).pack(anchor=tk.W, pady=(5, 0))
        
        # Aralık ayarı - dakika cinsinden
        interval_frame = ttk.LabelFrame(main_frame, text="Kaydetme Aralığı", padding=10)
        interval_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(interval_frame, text="Her (dakika):").pack(anchor=tk.W)
        
        # Value in minutes (stored as minutes in settings)
        interval_var = tk.DoubleVar(value=self.settings_manager.get_setting('auto_save_interval', 5.0))
        interval_frame_inner = ttk.Frame(interval_frame)
        interval_frame_inner.pack(fill=tk.X, pady=(5, 0))
        
        interval_spin = ttk.Spinbox(interval_frame_inner, from_=0.5, to=60, width=10,
                                   textvariable=interval_var, increment=0.5, format="%.1f")
        interval_spin.pack(side=tk.LEFT)
        ttk.Label(interval_frame_inner, text="dakikada bir kaydet").pack(side=tk.LEFT, padx=(5, 0))
        
        # Bilgi etiketi
        info_label = ttk.Label(interval_frame, text="(0.5 dakika - 60 dakika, 0.5'lik artışlarla)",
                              font=('Arial', 8), foreground="gray")
        info_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Durum bilgisi
        status_frame = ttk.LabelFrame(main_frame, text="Mevcut Durum", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        def update_status_info():
            status_text = []
            if hasattr(self.app, 'last_auto_save_time') and self.app.last_auto_save_time:
                status_text.append(f"Son otomatik kaydetme: {self.app.last_auto_save_time.strftime('%H:%M:%S')}")
            else:
                status_text.append("Henüz otomatik kaydetme yapılmadı")
                
            if self.app.has_unsaved_changes:
                status_text.append("🟡 Kaydedilmemiş değişiklikler var")
            else:
                status_text.append("🟢 Tüm değişiklikler kaydedildi")
                
            return "\n".join(status_text)
        
        status_label = ttk.Label(status_frame, text=update_status_info(), font=('Arial', 9))
        status_label.pack(anchor=tk.W)
        
        # Test button
        test_frame = ttk.Frame(main_frame)
        test_frame.pack(fill=tk.X, pady=(0, 15))
        
        def test_auto_save():
            if self.app._check_for_unsaved_work():
                # Mümkünse proje panelini kullan
                project_panel_state = {}
                if self.project_panel:
                    project_panel_state = self.project_panel.get_state()
                elif hasattr(self.app, 'project_panel'):
                    project_panel_state = self.app.project_panel.get_state()
                    
                success = self.settings_manager.save_project_state(
                    self.file_manager.get_state(),
                    self.editorial_process.get_state(),
                    project_panel_state,
                    save_reason='manual_test'
                )
                if success:
                    messagebox.showinfo("Test Başarılı", "💾 Otomatik kaydetme testi başarılı!")
                    status_label.config(text=update_status_info())
                else:
                    messagebox.showerror("Test Başarısız", "⚠️ Otomatik kaydetme testi başarısız oldu!")
            else:
                messagebox.showinfo("Test", "Kaydedilecek değişiklik yok.")
        
        ttk.Button(test_frame, text="Otomatik Kaydetmeyi Test Et",
                  command=test_auto_save).pack(side=tk.LEFT)
        
        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def save_settings():
            # Validate minutes value
            interval_minutes = max(0.5, interval_var.get())  # Minimum 0.5 minutes
            
            # Update settings
            old_enabled = self.settings_manager.get_setting('auto_save', True)
            old_interval = self.settings_manager.get_setting('auto_save_interval', 5.0)
            
            self.settings_manager.set_setting('auto_save', auto_save_enabled.get())
            self.settings_manager.set_setting('auto_save_interval', interval_minutes)
            
            # Restart auto-save system if settings changed
            if (auto_save_enabled.get() != old_enabled or interval_minutes != old_interval):
                self.app._restart_auto_save_timer()
                status_msg = "hemen uygulandı"
            else:
                status_msg = "değişiklik yok"
            
            messagebox.showinfo("Ayarlar Kaydedildi",
                              f"Otomatik kaydetme ayarları güncellendi.\n\n"
                              f"Kaydetme aralığı: {interval_minutes} dakika\n"
                              f"Durum: {'Etkin' if auto_save_enabled.get() else 'Devre dışı'}\n\n"
                              f"Yeni ayarlar {status_msg}.")
            auto_save_window.destroy()

        ttk.Button(button_frame, text="Kaydet", command=save_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="İptal", command=auto_save_window.destroy).pack(side=tk.RIGHT)

    def setup_auto_save(self):
        """Set up auto-save system"""
        # Get auto-save interval from settings (in minutes)
        auto_save_interval = self.settings_manager.get_setting('auto_save_interval', 5)  # Default 5 minutes
        auto_save_enabled = self.settings_manager.get_setting('auto_save', True)
        
        if auto_save_enabled:
            # Dakikayı milisaniyeye çevir
            interval_ms = int(auto_save_interval * 60 * 1000)
            print(f"Otomatik kaydetme etkin: her {auto_save_interval} dakikada bir")
            
            # İlk otomatik kaydetmeyi zamanla ve kimliği sakla
            self.app._auto_save_timer_id = self.app.root.after(interval_ms, self._auto_save_timer)
        else:
            print("Otomatik kaydetme devre dışı")

    def _auto_save_timer(self):
        """Auto-save timer function"""
        try:
            # Only save if there are unsaved changes
            if self.app._check_for_unsaved_work():
                print("🔄 Auto-save triggered...")
                
                # Use the project_panel if it's available
                project_panel_state = {}
                if self.project_panel:
                    project_panel_state = self.project_panel.get_state()
                elif hasattr(self.app, 'project_panel') and self.app.project_panel:
                    project_panel_state = self.app.project_panel.get_state()
                
                success = self.settings_manager.save_project_state(
                    self.file_manager.get_state(),
                    self.editorial_process.get_state(),
                    project_panel_state,
                    save_reason='auto'
                )
                
                if success:
                    self.app.last_auto_save_time = datetime.datetime.now()
                    timestamp = self.app.last_auto_save_time.strftime('%H:%M:%S')
                    print(f"✅ Otomatik kaydetme başarılı: {timestamp}")
                    if hasattr(self.app, 'show_analysis_status'):
                        self.app.show_analysis_status(f"💾 Otomatik kaydetme yapıldı: {timestamp}", "green")
                else:
                    print("❌ Otomatik kaydetme başarısız oldu!")
            else:
                print("🔍 Otomatik kaydetme kontrolü: Kaydedilecek değişiklik yok")
            
            # Restart timer
            self._restart_auto_save_timer()
            
        except Exception as e:
            print(f"❌ Otomatik kaydetme hatası: {e}")
            # Yine de zamanlayıcıyı yeniden başlat
            self._restart_auto_save_timer()

    def _restart_auto_save_timer(self):
        """Restart auto-save timer"""
        try:
            # Mevcut zamanlayıcıyı iptal et (varsa)
            if hasattr(self.app, '_auto_save_timer_id'):
                self.app.root.after_cancel(self.app._auto_save_timer_id)
                print("Eski otomatik kaydetme zamanlayıcısı iptal edildi")
            
            # Get new settings
            auto_save_enabled = self.settings_manager.get_setting('auto_save', True)
            auto_save_interval = self.settings_manager.get_setting('auto_save_interval', 5.0)
            
            if auto_save_enabled:
                # Dakikayı milisaniyeye çevir
                interval_ms = int(auto_save_interval * 60 * 1000)
                print(f"Otomatik kaydetme yeniden başlatıldı: her {auto_save_interval} dakikada bir")
                
                # Yeni zamanlayıcıyı başlat
                self.app._auto_save_timer_id = self.app.root.after(interval_ms, self._auto_save_timer)
                
                # Durum mesajını gösterme, çünkü bu kafa karıştırıcı olabilir
                # if hasattr(self.app, 'show_analysis_status'):
                #     self.app.show_analysis_status(
                #         f"🔄 Otomatik kaydetme güncellendi: {auto_save_interval} dakika",
                #         "blue"
                #     )
            else:
                print("Otomatik kaydetme devre dışı")
        except Exception as e:
            print(f"❌ Otomatik kaydetme zamanlayıcısını yeniden başlatma hatası: {e}")
