import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import datetime
import threading
import time

# Import modülleri
from modules.file_manager import FileManager
from modules.ai_integration import AIIntegration
from modules.editorial_process import EditorialProcess
from modules.settings_manager import SettingsManager
from modules.ui_components import SuggestionCard, ProjectPanel

class AIManager:
    def __init__(self, app):
        self.app = app
        self.ai_integration = app.ai_integration
        self.settings_manager = app.settings_manager
        self.editorial_process = app.editorial_process
        self.file_manager = app.file_manager

    def open_ai_settings(self):
        settings_window = tk.Toplevel(self.app.root)
        settings_window.title("Yapay Zeka Ayarları")
        settings_window.geometry("500x920")
        settings_window.resizable(True, True)
        settings_window.grab_set()
        
        # Ana frame
        main_frame = ttk.Frame(settings_window, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Style ayarları
        style = ttk.Style()
        style.configure("Title.TLabel", font=('Segoe UI', 16, 'bold'))
        style.configure("Subtitle.TLabel", font=('Segoe UI', 12, 'bold'))
        style.configure("Info.TLabel", font=('Segoe UI', 9), foreground="#666666")
        
        # Özel kart stilini tanımla
        style.configure("Card.TLabelframe", borderwidth=1, relief="solid")
        style.configure("Card.TLabelframe.Label", font=('Segoe UI', 10, 'bold'), background=settings_window.cget('background'))
        
        style.configure("Header.TFrame", padding="10 5 10 5", background="#f0f0f0")
        style.configure("Content.TFrame", padding="10 10 10 10")
        style.configure("Primary.TButton", font=('Segoe UI', 10))
        
        # Notebook (sekmeli görünüm) oluştur
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=(0, 15))
        
        # Genel Ayarlar sekmesi
        general_tab = ttk.Frame(notebook, padding=10)
        notebook.add(general_tab, text="Genel Ayarlar")
        
        # Model Seçimleri sekmesi
        models_tab = ttk.Frame(notebook, padding=10)
        notebook.add(models_tab, text="Model Seçimleri")
        
        # Timeout Ayarları sekmesi
        timeout_tab = ttk.Frame(notebook, padding=10)
        notebook.add(timeout_tab, text="Timeout Ayarları")
        
        #---------- GENEL AYARLAR SEKMESİ ----------#
        ttk.Label(general_tab, text="Gemini API Ayarları", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 15))
        
        # API Key
        api_frame = ttk.LabelFrame(general_tab, text="Gemini API Key", style="Card.TLabelframe", padding="10 15 10 10")
        api_frame.pack(fill=tk.X, pady=(0, 15))
        
        api_key_entry = ttk.Entry(api_frame, show="*", width=50)
        api_key_entry.pack(fill=tk.X, pady=(0, 5))
        api_key_entry.insert(0, self.settings_manager.get_setting("api_key", ""))
        
        # API Key bilgi metni
        ttk.Label(api_frame, text="API anahtarınızı güvenli bir şekilde saklayın. Bu anahtar, AI özelliklerinin çalışması için gereklidir.", 
                 style="Info.TLabel").pack(anchor=tk.W, pady=(0, 5))
        
        # Varsayılan Model
        model_frame = ttk.LabelFrame(general_tab, text="Varsayılan Model", style="Card.TLabelframe", padding="10 15 10 10")
        model_frame.pack(fill=tk.X, pady=(0, 15))
        
        default_model_var = tk.StringVar(value=self.settings_manager.get_setting("model", "gemini-1.5-flash"))
        
        # Expanded list of all available Gemini models
        models = [
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
        
        default_model_combo = ttk.Combobox(model_frame, textvariable=default_model_var, values=models, state="readonly")
        default_model_combo.pack(fill=tk.X, pady=(0, 5))
        
        # Varsayılan model bilgi metni
        ttk.Label(model_frame, text="Varsayılan model, özel model belirlenmediğinde kullanılır.", 
                 style="Info.TLabel").pack(anchor=tk.W, pady=(0, 5))
        
        # Bağlantı Durumu
        status_frame = ttk.LabelFrame(general_tab, text="Bağlantı Durumu", style="Card.TLabelframe", padding="10 15 10 10")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.app.connection_status_label = ttk.Label(status_frame, text="Bağlantı test edilmedi", foreground="gray")
        self.app.connection_status_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Test butonu
        def test_connection():
            api_key = api_key_entry.get().strip()
            model = default_model_var.get()
            
            if not api_key:
                self.app.connection_status_label.config(text="⚠️ API anahtarı boş olamaz", foreground="orange")
                return
            
            self.app.connection_status_label.config(text="🔄 Test ediliyor...", foreground="blue")
            settings_window.update()
            
            # Test için geçici AI entegrasyonu
            test_success = self.ai_integration.update_settings(api_key, model)
            
            if test_success:
                # Gerçek bağlantı testi
                connection_test = self.ai_integration.test_connection()
                if connection_test:
                    self.app.connection_status_label.config(text="✅ Bağlantı başarılı!", foreground="green")
                else:
                    self.app.connection_status_label.config(text="❌ Bağlantı başarısız", foreground="red")
            else:
                self.app.connection_status_label.config(text="❌ API anahtarı geçersiz", foreground="red")
        
        test_button = ttk.Button(status_frame, text="Bağlantıyı Test Et", command=test_connection, style="Primary.TButton")
        test_button.pack(anchor=tk.W)
        
        #---------- MODEL SEÇİMLERİ SEKMESİ ----------#
        ttk.Label(models_tab, text="Analiz Türlerine Özel Modeller", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 15))
        
        # Get current individual models from settings
        individual_models = self.settings_manager.get_setting("individual_models", {
            "style_analysis": "gemini-1.5-flash",
            "grammar_check": "gemini-1.5-flash",
            "content_review": "gemini-1.5-pro",
            "novel_context": "gemini-1.5-pro"
        })
        
        # Üslup Analizi Model
        style_model_frame = ttk.LabelFrame(models_tab, text="Üslup Analizi Ayarları", style="Card.TLabelframe", padding="10 15 10 10")
        style_model_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(style_model_frame, text="Model Seçimi").pack(anchor=tk.W)
        style_model_var = tk.StringVar(value=individual_models.get("style_analysis", "gemini-1.5-flash"))
        ttk.Combobox(style_model_frame, textvariable=style_model_var, values=models, state="readonly").pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(style_model_frame, text="Kullanılacak Bağlam").pack(anchor=tk.W, pady=(5, 0))
        style_context_var = tk.StringVar(value=self.settings_manager.get_setting("style_analysis_context_source", "full_text"))
        
        style_context_frame = ttk.Frame(style_model_frame)
        style_context_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Radiobutton(style_context_frame, text="Romanın Tam Metni", variable=style_context_var, value="full_text").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(style_context_frame, text="Roman Kimliği", variable=style_context_var, value="novel_context").pack(side=tk.LEFT)

        ttk.Label(style_model_frame, text="Cümle yapısı, kelime seçimi ve üslup analizi için önerilen model", 
                 style="Info.TLabel").pack(anchor=tk.W)
        
        # Dil Bilgisi Model
        grammar_model_frame = ttk.LabelFrame(models_tab, text="Dil Bilgisi Kontrolü Modeli", style="Card.TLabelframe", padding="10 15 10 10")
        grammar_model_frame.pack(fill=tk.X, pady=(0, 15))
        
        grammar_model_var = tk.StringVar(value=individual_models.get("grammar_check", "gemini-1.5-flash"))
        ttk.Combobox(grammar_model_frame, textvariable=grammar_model_var, values=models, state="readonly").pack(fill=tk.X, pady=(0, 10))

        ttk.Label(grammar_model_frame, text="Kullanılacak Bağlam").pack(anchor=tk.W, pady=(5, 0))
        grammar_context_var = tk.StringVar(value=self.settings_manager.get_setting("grammar_check_context_source", "novel_context")) # Varsayılan: Roman Kimliği
        
        grammar_context_frame = ttk.Frame(grammar_model_frame)
        grammar_context_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Radiobutton(grammar_context_frame, text="Romanın Tam Metni", variable=grammar_context_var, value="full_text").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(grammar_context_frame, text="Roman Kimliği", variable=grammar_context_var, value="novel_context").pack(side=tk.LEFT)
        
        ttk.Label(grammar_model_frame, text="Dil Bilgisi, yazım ve noktalama hataları için önerilen model", 
                 style="Info.TLabel").pack(anchor=tk.W)
        
        # İçerik Model
        content_model_frame = ttk.LabelFrame(models_tab, text="İçerik İnceleme Ayarları", style="Card.TLabelframe", padding="10 15 10 10")
        content_model_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(content_model_frame, text="Model Seçimi").pack(anchor=tk.W)
        content_model_var = tk.StringVar(value=individual_models.get("content_review", "gemini-1.5-pro"))
        ttk.Combobox(content_model_frame, textvariable=content_model_var, values=models, state="readonly").pack(fill=tk.X, pady=(0, 10))

        ttk.Label(content_model_frame, text="Kullanılacak Bağlam").pack(anchor=tk.W, pady=(5, 0))
        content_context_var = tk.StringVar(value=self.settings_manager.get_setting("content_review_context_source", "full_text"))
        
        content_context_frame = ttk.Frame(content_model_frame)
        content_context_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Radiobutton(content_context_frame, text="Romanın Tam Metni", variable=content_context_var, value="full_text").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(content_context_frame, text="Roman Kimliği", variable=content_context_var, value="novel_context").pack(side=tk.LEFT)

        ttk.Label(content_model_frame, text="Olay örgüsü, karakter gelişimi ve yapısal bütünlük analizi için güçlü bir model (örn: Pro) önerilir.", 
                 style="Info.TLabel").pack(anchor=tk.W)

        # Roman Kimliği Model
        context_model_frame = ttk.LabelFrame(models_tab, text="Roman Kimliği Oluşturma Modeli", style="Card.TLabelframe", padding="10 15 10 10")
        context_model_frame.pack(fill=tk.X, pady=(0, 15))
        
        context_model_var = tk.StringVar(value=individual_models.get("novel_context", "gemini-1.5-pro"))
        ttk.Combobox(context_model_frame, textvariable=context_model_var, values=models, state="readonly").pack(fill=tk.X, pady=(0, 5))
        ttk.Label(context_model_frame, text="Tüm romandan genel bir özet çıkarır. Güçlü bir model (örn: Pro) önerilir.", 
                 style="Info.TLabel").pack(anchor=tk.W)
        
        # Modeller hakkında bilgi metni
        info_frame = ttk.LabelFrame(models_tab, text="Model Önerileri", style="Card.TLabelframe", padding="10 15 10 10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        model_info_text = """• gemini-1.5-flash: Hızlı yanıtlar için ideal, temel analizler için yeterli
• gemini-1.5-pro: Daha detaylı ve kapsamlı analizler için önerilir
• gemini-2.5-pro: En gelişmiş model, karmaşık metin analizi için idealdir"""
        
        ttk.Label(info_frame, text=model_info_text, style="Info.TLabel", justify=tk.LEFT).pack(anchor=tk.W)
        
        #---------- TIMEOUT AYARLARI SEKMESİ ----------#
        ttk.Label(timeout_tab, text="Timeout Ayarları", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 15))
        
        # Dinamik Timeout
        dynamic_frame = ttk.LabelFrame(timeout_tab, text="Dinamik Timeout", style="Card.TLabelframe", padding="10 15 10 10")
        dynamic_frame.pack(fill=tk.X, pady=(0, 15))
        
        use_dynamic_timeout = tk.BooleanVar(value=self.settings_manager.get_setting("use_dynamic_timeout", True))
        ttk.Checkbutton(dynamic_frame, variable=use_dynamic_timeout, 
                       text="Metin uzunluğuna göre otomatik timeout").pack(anchor=tk.W, pady=(0, 5))
        
        ttk.Label(dynamic_frame, text="Metin uzunluğuna göre otomatik olarak timeout süresini ayarlar. Uzun metinler için daha uzun süre tanır.", 
                 style="Info.TLabel").pack(anchor=tk.W)
        
        # Sabit timeout ayarı
        fixed_frame = ttk.LabelFrame(timeout_tab, text="Sabit Timeout (Saniye)", style="Card.TLabelframe", padding="10 15 10 10")
        fixed_frame.pack(fill=tk.X, pady=(0, 15))
        
        timeout_entry_frame = ttk.Frame(fixed_frame)
        timeout_entry_frame.pack(fill=tk.X, pady=(0, 5))
        
        fixed_timeout_var = tk.StringVar(value=str(self.settings_manager.get_setting("fixed_timeout", 120)))
        ttk.Entry(timeout_entry_frame, textvariable=fixed_timeout_var, width=10).pack(side=tk.LEFT)
        ttk.Label(timeout_entry_frame, text="saniye").pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(fixed_frame, text="Dinamik timeout kapalıysa bu sabit değer kullanılır. En az 30 saniye önerilir.", 
                 style="Info.TLabel").pack(anchor=tk.W)
        
        # Timeout bilgi metni
        info_frame = ttk.LabelFrame(timeout_tab, text="Nasıl Çalışır?", style="Card.TLabelframe", padding="10 15 10 10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = """📊 Dinamik Timeout Sistemi:
• Dil Bilgisi: 60s + (her 1K karakter için +5s)
• Üslup: 90s + (her 1K karakter için +8s)
• İçerik: 120s + (her 1K karakter için +12s)
• Minimum: 45s, Maksimum: 10dk"""
        
        ttk.Label(info_frame, text=info_text, style="Info.TLabel", justify=tk.LEFT).pack(anchor=tk.W)
        
        # Alt butonlar frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def save_ai_settings():
            api_key = api_key_entry.get().strip()
            default_model = default_model_var.get()
            
            # Get individual models
            individual_models_config = {
                "style_analysis": style_model_var.get(),
                "grammar_check": grammar_model_var.get(),
                "content_review": content_model_var.get(),
                "novel_context": context_model_var.get()
            }

            # Bağlam kaynağı ayarlarını kaydet
            self.settings_manager.set_setting("style_analysis_context_source", style_context_var.get())
            self.settings_manager.set_setting("content_review_context_source", content_context_var.get())
            self.settings_manager.set_setting("grammar_check_context_source", grammar_context_var.get())
            
            # Timeout ayarlarını kaydet
            self.settings_manager.set_setting("use_dynamic_timeout", use_dynamic_timeout.get())
            try:
                fixed_timeout = max(30, int(fixed_timeout_var.get()))  # En az 30 saniye
                self.settings_manager.set_setting("fixed_timeout", fixed_timeout)
            except ValueError:
                self.settings_manager.set_setting("fixed_timeout", 120)  # Varsayılan
            
            self.settings_manager.set_setting("api_key", api_key)
            self.settings_manager.set_setting("model", default_model)
            self.settings_manager.set_setting("individual_models", individual_models_config)
            
            if api_key:
                print(f"AI AYARLARI KAYDEDILIYOR: Model={default_model}, API Key={len(api_key)} karakter")
                print(f"Timeout ayarları: Dinamik={use_dynamic_timeout.get()}, Sabit={fixed_timeout_var.get()}s")
                print(f"Individual models: {individual_models_config}")
                success = self.ai_integration.update_settings(api_key, default_model, individual_models_config)
                if success:
                    print("AI model başarıyla yapılandırıldı")
                    messagebox.showinfo("Başarı", "AI ayarları kaydedildi ve bağlantı kuruldu.")
                else:
                    print("AI model yapılandırma başarısız")
                    messagebox.showwarning("Uyarı", "Ayarlar kaydedildi ancak AI bağlantısı kurulamadı.")
            else:
                print("API anahtarı boş - AI devre dışı")
                messagebox.showinfo("Bilgi", "Ayarlar kaydedildi. AI özellikleri devre dışı.")
            
            settings_window.destroy()

        def cancel_settings():
            settings_window.destroy()
        
        ttk.Button(button_frame, text="Kaydet", command=save_ai_settings, style="Primary.TButton").pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="İptal", command=cancel_settings).pack(side=tk.RIGHT)

    def open_prompt_settings(self):
        """Prompt ayarları penceresi"""
        from modules.ui_components import PromptEditor
        
        current_prompts = self.ai_integration.get_prompts()
        PromptEditor(self.app.root, current_prompts, self.app.update_prompts)

    def show_novel_context(self):
        """Oluşturulan Roman Kimliği'ni bir pencerede gösterir."""
        context = self.editorial_process.novel_context
        
        if not context or not context.strip():
            messagebox.showinfo("Roman Kimliği", "Henüz bir Roman Kimliği oluşturulmadı.\n\nKimlik, ilk bölüm analizi başlatıldığında otomatik olarak oluşturulur.")
            return
            
        context_window = tk.Toplevel(self.app.root)
        context_window.title("Roman Kimliği Özeti")
        context_window.geometry("700x600")
        context_window.grab_set()
        
        main_frame = ttk.Frame(context_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Oluşturulan Roman Kimliği", font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        context_text = tk.Text(text_frame, wrap=tk.WORD, font=('Arial', 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=context_text.yview)
        context_text.configure(yscrollcommand=scrollbar.set)
        
        context_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        context_text.insert('1.0', context)
        context_text.config(state='disabled')
        
        ttk.Button(main_frame, text="Kapat", command=context_window.destroy).pack(pady=5)
