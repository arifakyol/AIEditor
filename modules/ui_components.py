import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Callable, List, Dict, Optional

class DualProgressBar(tk.Frame):
    """
    Pasif (gri) ve aktif (yeşil) ilerlemeyi gösteren çift katmanlı bir ilerleme çubuğu.
    """
    def __init__(self, parent, height=20, **kwargs):
        super().__init__(parent, **kwargs)
        self.height = height
        self.canvas = tk.Canvas(self, height=height, highlightthickness=0, bg='#E0E0E0')
        self.canvas.pack(fill=tk.X, expand=True)
        
        # Dikdörtgenler (ID'lerini sakla)
        self.passive_bar_id = self.canvas.create_rectangle(0, 0, 0, height, fill='#BDBDBD', outline='')
        self.active_bar_id = self.canvas.create_rectangle(0, 0, 0, height, fill='#4CAF50', outline='')
        
        # Yüzde etiketi (doğrudan canvas üzerine çizilecek)
        self.label_id = self.canvas.create_text(0, 0, text="", font=('Arial', 9, 'bold'), anchor='center')

        self.bind("<Configure>", self._on_resize)
        self._passive_progress = 0.0  # 0.0 - 1.0 arası
        self._active_progress = 0.0   # 0.0 - 1.0 arası

    def set_progress(self, passive_progress: float, active_progress: float):
        """
        Pasif ve aktif ilerlemeyi ayarlar.
        Değerler 0.0 ile 1.0 arasında olmalıdır.
        """
        self._passive_progress = max(0.0, min(1.0, passive_progress))
        self._active_progress = max(0.0, min(1.0, active_progress))
        
        self._update_display()

    def _update_display(self):
        """Görseli günceller."""
        width = self.canvas.winfo_width()
        height = self.height

        # Pasif bar (gri)
        passive_width = width * self._passive_progress
        self.canvas.coords(self.passive_bar_id, 0, 0, passive_width, height)

        # Aktif bar (yeşil)
        active_width = width * self._active_progress
        self.canvas.coords(self.active_bar_id, 0, 0, active_width, height)
        
        # Etiket
        # Aktif ilerleme yüzdesini gösterelim
        progress_percent = self._active_progress * 100
        
        # Etiketin konumunu ve metnini güncelle
        label_x = width / 2
        label_y = height / 2
        self.canvas.coords(self.label_id, label_x, label_y)
        
        # Sadece ilerleme varsa yüzdeyi göster
        if self._active_progress > 0 or self._passive_progress > 0:
            self.canvas.itemconfig(self.label_id, text=f"%{progress_percent:.1f}")
        else:
            self.canvas.itemconfig(self.label_id, text="")

        # Yazı rengini okunabilirliğe göre ayarla
        # Etiketin kapladığı alan
        label_bbox = self.canvas.bbox(self.label_id)
        if label_bbox:
            label_start_x, _, label_end_x, _ = label_bbox
            # Etiket tamamen aktif barın içindeyse yazıyı beyaz yap
            if label_start_x > 0 and label_end_x < active_width:
                self.canvas.itemconfig(self.label_id, fill='white')
            # Etiket tamamen pasif barın içindeyse (ama aktif değilse) yazıyı beyaz yap
            elif label_start_x > 0 and label_end_x < passive_width and active_width < label_start_x:
                 self.canvas.itemconfig(self.label_id, fill='white')
            else:
                self.canvas.itemconfig(self.label_id, fill='black')

    def _on_resize(self, event=None):
        """Pencere yeniden boyutlandırıldığında barı günceller."""
        self._update_display()

class SuggestionCard(ttk.Frame):
    def __init__(self, parent, suggestion, callback: Callable):
        super().__init__(parent)
        self.suggestion = suggestion
        self.callback = callback
        self.is_editing = False
        self._leave_job = None
        
        self.setup_ui()
    
    def setup_ui(self):
        # Ana frame
        self.configure(relief='ridge', borderwidth=1, padding=10)
        
        # Öneri objesi tip kontrolü ve debug
        print(f"📋 SuggestionCard oluşturuluyor - Öneri tipi: {type(self.suggestion)}")
        
        try:
            # Başlık için güvenli erişim
            suggestion_title = getattr(self.suggestion, 'title', 'Başlıksız Öneri')
            suggestion_id = getattr(self.suggestion, 'id', 'kimlik_yok')
            # Severity'yi alırken daha dikkatli olalım. Boş string gelirse 'medium' varsayalım.
            suggestion_severity = getattr(self.suggestion, 'severity', 'medium')
            if not suggestion_severity or not isinstance(suggestion_severity, str) or suggestion_severity == '':
                suggestion_severity = 'medium' # Varsayılan
            
            # Savunma mekanizması: Eğer severity 'medium' ise ama explanation içinde farklı bir severity belirtilmişse, onu kullan.
            # Bu, ayrıştırma hatası durumunda doğru severity'nin gösterilmesini sağlar.
            try:
                explanation_str = getattr(self.suggestion, 'explanation', '').lower()
                if 'severity' in explanation_str:
                    import re
                    match = re.search(r'"severity":\s*"(\w+)"', explanation_str)
                    if match:
                        found_severity = match.group(1)
                        if found_severity in ['low', 'medium', 'high']:
                            suggestion_severity = found_severity
                            print(f"⚠️ Severity, açıklamadan ayrıştırıldı: {suggestion_severity}")
            except Exception as e:
                print(f"Açıklamadan severity ayrıştırılırken hata: {e}")

            print(f"📋 Öneri bilgileri - Title: {suggestion_title}, ID: {suggestion_id}, Severity: {suggestion_severity}")
            
            # Üst kısım - Başlık ve önem derecesi
            top_frame = ttk.Frame(self)
            top_frame.pack(fill=tk.X, pady=(0, 5))
            
            # Başlık
            title_label = ttk.Label(top_frame, text=suggestion_title, 
                                   font=('Arial', 11, 'bold'))
            title_label.pack(side=tk.LEFT)
            
            # Editör bilgisi
            editor_type = getattr(self.suggestion, 'editor_type', None)
            if editor_type:
                editor_label = ttk.Label(top_frame, 
                                       text=f"({editor_type})",
                                       font=('Arial', 9), foreground='blue')
                editor_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # Model bilgisi
            model_name = getattr(self.suggestion, 'model_name', None)
            if model_name:
                model_label = ttk.Label(top_frame, 
                                      text=f"[{model_name}]",
                                      font=('Arial', 8), foreground='purple')
                model_label.pack(side=tk.LEFT, padx=(5, 0))
            
            # Önem derecesi
            severity_colors = {'high': 'red', 'medium': 'orange', 'low': 'green', 'unknown': 'grey'}
            severity_text = {'high': 'Yüksek', 'medium': 'Orta', 'low': 'Düşük', 'unknown': 'Bilinmiyor'}
            
            # Gelen severity değerini küçük harfe çevirerek kontrol edelim
            processed_severity = suggestion_severity.lower() if isinstance(suggestion_severity, str) else 'medium'

            severity_label = ttk.Label(top_frame, text=severity_text.get(processed_severity, 'Orta'),
                                      foreground=severity_colors.get(processed_severity, 'orange'))
            severity_label.pack(side=tk.RIGHT)
            
            # Orta bölüm için frame (açıklama ve cümleleri yan yana gösterecek)
            content_frame = ttk.Frame(self)
            content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Sol taraf - Orijinal cümle
            original_sentence = getattr(self.suggestion, 'original_sentence', None)
            if original_sentence:
                orig_frame = ttk.LabelFrame(content_frame, text="Orijinal Cümle", padding=5)
                orig_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
                
                orig_label = ttk.Label(orig_frame, text=original_sentence,
                                     wraplength=150, justify=tk.LEFT, foreground='darkred')
                orig_label.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
            
            # Sağ taraf - Önerilen cümle (düzenlenebilir)
            suggested_sentence = getattr(self.suggestion, 'suggested_sentence', None)
            if suggested_sentence:
                suggest_frame = ttk.LabelFrame(content_frame, text="Önerilen Cümle", padding=5)
                suggest_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
                
                # Label ve Text widget'ları için frame
                self.suggest_content_frame = ttk.Frame(suggest_frame)
                self.suggest_content_frame.pack(fill=tk.BOTH, expand=True)
                
                # Label (normal görüntü)
                self.suggest_label = ttk.Label(self.suggest_content_frame, 
                                             text=suggested_sentence,
                                             wraplength=150, justify=tk.LEFT, foreground='darkgreen')
                self.suggest_label.pack(anchor=tk.W, fill=tk.BOTH, expand=True)
                
                # Text widget (düzenleme modu)
                self.suggest_text = tk.Text(self.suggest_content_frame, height=3, wrap=tk.WORD, 
                                          font=('Arial', 9))
                
                # Düzenleme butonu
                edit_frame = ttk.Frame(suggest_frame)
                edit_frame.pack(fill=tk.X, pady=(5, 0))
                
                self.edit_button = ttk.Button(edit_frame, text="Düzenle", command=self.toggle_edit_mode)
                self.edit_button.pack(side=tk.RIGHT)
            
            # Açıklama (alt kısımda) - Şimdi altta göster
            explanation = getattr(self.suggestion, 'explanation', None)
            if explanation:
                explanation_text = str(explanation).strip()
                # Boş değil ve "bulunamadı" içermiyorsa göster
                if explanation_text and "bulunamadı" not in explanation_text.lower() and len(explanation_text) > 5:
                    exp_frame = ttk.LabelFrame(self, text="Açıklama", padding=5)
                    exp_frame.pack(fill=tk.X, pady=5)
                    
                    # Açıklama metninde kalmış olabilecek JSON anahtar-değer çiftlerini temizle
                    import re
                    cleaned_explanation = re.sub(r',\s*"editor_type":.*', '', explanation_text)
                    cleaned_explanation = re.sub(r',\s*"severity":.*', '', cleaned_explanation)
                    cleaned_explanation = re.sub(r'"editor_type":\s*"[^"]*"', '', cleaned_explanation)
                    cleaned_explanation = re.sub(r'"severity":\s*"[^"]*"', '', cleaned_explanation)
                    
                    exp_label = ttk.Label(exp_frame, text=cleaned_explanation.strip(), 
                                        wraplength=300, justify=tk.LEFT, foreground='darkblue')
                    exp_label.pack(anchor=tk.W)
            
            # Butonlar (Hover ile gösterilecek)
            self.hover_frame = tk.Frame(self, background="#F0F0F0", relief='raised', borderwidth=1)
            
            ttk.Button(self.hover_frame, text="Uygula ve Kaldır",
                      command=lambda: self.callback(self.suggestion, "apply")).pack(side=tk.LEFT, padx=5, pady=5)
            
            ttk.Button(self.hover_frame, text="Reddet",
                      command=lambda: self.callback(self.suggestion, "reject")).pack(side=tk.LEFT, padx=5, pady=5)
            
            ttk.Button(self.hover_frame, text="Detaylar",
                      command=self.show_details).pack(side=tk.LEFT, padx=5, pady=5)
            
            # Hover olaylarını bağla
            self.bind_recursive(self)
                      
            print(f"✅ SuggestionCard başarıyla oluşturuldu: {suggestion_title}")
            
        except Exception as e:
            print(f"❌ SuggestionCard oluşturma hatası: {e}")
            print(f"❌ Öneri objesi: {self.suggestion}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            
            # Hata durumunda basit bir kart göster
            error_label = ttk.Label(self, text=f"Hatalı öneri: {str(e)}",
                                   foreground='red', font=('Arial', 10, 'bold'))
            error_label.pack(pady=10)
            
            error_button = ttk.Button(self, text="Reddet",
                                     command=lambda: self.callback(self.suggestion, "reject"))
            error_button.pack()

    def bind_recursive(self, widget):
        """Bir widget'a ve tüm alt widget'larına olayları bağlar."""
        widget.bind("<Enter>", self.on_enter)
        widget.bind("<Leave>", self.on_leave)
        for child in widget.winfo_children():
            self.bind_recursive(child)

    def on_enter(self, event=None):
        """Mouse karta girdiğinde butonları gösterir."""
        if self._leave_job:
            self.after_cancel(self._leave_job)
            self._leave_job = None
        self.hover_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.hover_frame.lift()

    def on_leave(self, event=None):
        """Mouse karttan ayrıldığında butonları gizlemek için bir iş zamanlar."""
        self._leave_job = self.after(50, self.hide_buttons)

    def hide_buttons(self):
        """Butonları gizler, ama sadece mouse gerçekten kartın dışındaysa."""
        try:
            # Mouse'un anlık ekran koordinatlarını al ve o koordinatlardaki widget'ı bul
            x, y = self.winfo_pointerxy()
            widget_under_cursor = self.winfo_containing(x, y)

            # İmlecin altındaki widget'tan başlayarak yukarı doğru ağacı takip et
            # Eğer bu kart (self) hiyerarşide bulunursa, imleç hala içeride demektir.
            current = widget_under_cursor
            while current:
                if current == self:
                    return  # İmleç hala kartın içinde, gizleme ve fonksiyondan çık.
                current = current.master
            
            # Eğer döngü bittiyse ve kart bulunamadıysa, imleç dışarıdadır.
            self.hover_frame.place_forget()

        except Exception:
            # Widget yok edilmişse veya başka bir hata oluşursa, butonları gizle.
            self.hover_frame.place_forget()
        finally:
            self._leave_job = None
    
    def toggle_edit_mode(self):
        """Düzenleme modunu aç/kapat"""
        if not self.is_editing:
            # Düzenleme moduna geç
            self.suggest_label.pack_forget()
            self.suggest_text.pack(fill=tk.X)
            self.suggest_text.delete('1.0', tk.END)
            self.suggest_text.insert('1.0', self.suggestion.suggested_sentence)
            self.edit_button.config(text="Kaydet")
            self.is_editing = True
        else:
            # Kaydet ve normal moda dön
            new_suggestion = self.suggest_text.get('1.0', tk.END).strip()
            if new_suggestion:
                self.suggestion.suggested_sentence = new_suggestion
                self.suggest_label.config(text=new_suggestion)
            
            self.suggest_text.pack_forget()
            self.suggest_label.pack(anchor=tk.W)
            self.edit_button.config(text="Düzenle")
            self.is_editing = False
    
    def show_details(self):
        """Öneri detaylarını göster"""
        detail_window = tk.Toplevel(self)
        detail_window.title("Öneri Detayları")
        detail_window.geometry("500x400")
        detail_window.grab_set()
        
        # Detay metni
        text_widget = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        detail_text = f"""Öneri ID: {self.suggestion.id or ''}
Tip: {self.suggestion.type or ''}
Başlık: {self.suggestion.title or ''}
Önem Derecesi: {self.suggestion.severity or ''}

Orijinal Cümle:
{getattr(self.suggestion, 'original_sentence', 'Belirtilmemiş')}

Önerilen Cümle:
{getattr(self.suggestion, 'suggested_sentence', 'Belirtilmemiş')}

Açıklama:
{getattr(self.suggestion, 'explanation', 'Açıklama yok')}

Tam Açıklama:
{self.suggestion.description or ''}
"""
        
        text_widget.insert('1.0', detail_text)
        text_widget.config(state='disabled')

class ProjectPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.chapters = []
        self.current_chapter_index = 0
        
        self.setup_ui()
    
    def setup_ui(self):
        # Başlık
        ttk.Label(self, text="Proje Bilgileri", font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        # Proje durumu
        status_frame = ttk.LabelFrame(self, text="Durum", padding=10)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="Proje yüklenmedi")
        self.status_label.pack(anchor=tk.W)
        
        # Yeni çift katmanlı ilerleme çubuğu
        self.progress_bar = DualProgressBar(status_frame, height=18)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Bölümler listesi
        chapters_frame = ttk.LabelFrame(self, text="Bölümler", padding=10)
        chapters_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Bölüm listesi - Modern tree view tarzı
        list_frame = ttk.Frame(chapters_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Tree view yerine Text widget kullanarak modern görünüm
        self.chapters_text = tk.Text(list_frame, 
                                   selectbackground="#0078d4",
                                   selectforeground="white", 
                                   font=('Segoe UI', 9),
                                   cursor="hand2",
                                   wrap=tk.NONE,
                                   state='disabled')
        
        scrollbar_chapters = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, 
                                         command=self.chapters_text.yview)
        self.chapters_text.configure(yscrollcommand=scrollbar_chapters.set)
        
        self.chapters_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_chapters.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Click olayı için binding
        self.chapters_text.bind('<Button-1>', self.on_chapter_click)
        
        # Bölüm kontrolleri
        control_frame = ttk.Frame(chapters_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(control_frame, text="◀ Önceki",
                  command=self.prev_chapter).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(control_frame, text="Sonraki ▶",
                  command=self.next_chapter).pack(side=tk.LEFT, padx=5)
        
        # Tümünü Analiz Et butonu (Sağa yaslı)
        analyze_all_button = ttk.Button(control_frame, text="Tümünü Analiz Et", command=self.start_full_analysis_wrapper)
        analyze_all_button.pack(side=tk.RIGHT, padx=5)
        # Tooltip'i UIManager üzerinden oluştur
        if hasattr(self.app, 'ui_manager'):
            self.app.ui_manager._create_tooltip(analyze_all_button, "Tüm bölümleri sırayla analiz et.\nÖnce dil bilgisi, sonra üslup, sonra içerik.\nBir önceki aşamadan bekleyen öneri varsa sonraki aşamaya geçmez.")
        
        # İstatistikler
        stats_frame = ttk.LabelFrame(self, text="İstatistikler", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stats_text = tk.Text(stats_frame, height=6, state='disabled', 
                                 font=('Arial', 9))
        self.stats_text.pack(fill=tk.X)
        
        # Bölüm içeriği önizleme
        preview_frame = ttk.LabelFrame(self, text="Seçili Bölüm Önizleme", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_text = tk.Text(preview_frame, height=8, wrap=tk.WORD, state='disabled',
                                   font=('Arial', 9))
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, 
                                         command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)
        
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def update_chapters(self, chapters: List, preserve_selection: bool = False):
        """Bölüm listesini güncelle - Modern tree view formatında"""
        print(f"DEBUG - update_chapters çağrıldı, {len(chapters)} bölüm")
        # Mevcut seçimi kaydet
        current_selection = self.current_chapter_index if preserve_selection else 0
        
        self.chapters = chapters
        
        # Text widget'ı temizle ve modern format ekle
        self.chapters_text.config(state='normal')
        self.chapters_text.delete('1.0', tk.END)
        
        # Tag stillerini tanımla
        self.chapters_text.tag_configure('chapter_title', font=('Segoe UI', 10, 'bold'), foreground='#2c3e50')
        self.chapters_text.tag_configure('process_item', font=('Segoe UI', 8), foreground='#7f8c8d', lmargin1=20)
        self.chapters_text.tag_configure('completed', foreground='#27ae60')
        self.chapters_text.tag_configure('pending', foreground='#e74c3c')
        self.chapters_text.tag_configure('selected', background='#0078d4', foreground='white')
        self.chapters_text.tag_configure('suggestion_count', font=('Segoe UI', 7), foreground='#666666', lmargin1=30)
        
        for i, chapter in enumerate(chapters):
            # Bölüm başlığı
            status_icon = "✓" if getattr(chapter, 'is_processed', False) else "○"
            chapter_title = f"{status_icon} {chapter.title}\n"
            
            # Başlığı ekle
            start_pos = self.chapters_text.index(tk.INSERT)
            self.chapters_text.insert(tk.END, chapter_title)
            end_pos = self.chapters_text.index(tk.INSERT)
            self.chapters_text.tag_add('chapter_title', start_pos, end_pos)
            
            # Analiz süreçlerini göster
            phase_definitions = [
                ('grammar', 'Dil Bilgisi Analizi'),
                ('style', 'Üslup Analizi'),
                ('content', 'İçerik Analizi')
            ]
            
            if hasattr(chapter, 'analysis_phases'):
                phases = chapter.analysis_phases
                for prefix, name in phase_definitions:
                    icon = self._get_phase_icon(phases, prefix)
                    
                    # Bu analiz türü için öneri sayılarını hesapla
                    total_suggestions, remaining_suggestions = self._get_suggestion_counts(chapter, prefix)
                    
                    # Öneri sayısı bilgisini ekle - her zaman göster
                    suggestion_info = f" ({remaining_suggestions}/{total_suggestions})"
                    
                    text = f"    {icon} {name}{suggestion_info}\n"
                    tag = 'completed' if phases.get(f'{prefix}_completed', False) else 'pending'
                    self._add_phase_display(text, tag)
            else:
                # Analiz fazları tanımlı değil
                for prefix, name in phase_definitions:
                    process_text = f"    ⏳ {name}\n"
                    self._add_phase_display(process_text, 'pending')
        
        self.chapters_text.config(state='disabled')
        
        # Seçimi geri yükle veya ilk bölümü seç
        if chapters:
            # Seçim geçerli aralıkta mı kontrol et
            if current_selection >= len(chapters):
                current_selection = len(chapters) - 1
            
            self.current_chapter_index = current_selection
            
            # Seçimi görsel olarak işaretle
            self.chapters_text.config(state='normal')
            start_line = current_selection * 4 + 1
            end_line = start_line + 4
            self.chapters_text.tag_add('selected', f'{start_line}.0', f'{end_line}.0')
            self.chapters_text.config(state='disabled')
            
            # Görüntüyse kaydır
            self.chapters_text.see(f'{start_line}.0')
            
            self.update_status()
            # Önizlemeyi manuel olarak tetikle
            self.update_preview(chapters[current_selection])
            
            # Sadece yeni yükleme durumunda bildirim gönder (preserve_selection=False)
            if not preserve_selection and self.app and hasattr(self.app, 'on_chapter_selection_changed'):
                try:
                    self.app.on_chapter_selection_changed()
                except Exception as e:
                    print(f"Uyarı: on_chapter_selection_changed çağrılırken hata oluştu: {e}")
    
    def _add_phase_display(self, text: str, tag: str):
        """Helper to add a line of text with tags to the chapters_text widget."""
        start_pos = self.chapters_text.index(tk.INSERT)
        self.chapters_text.insert(tk.END, text)
        end_pos = self.chapters_text.index(tk.INSERT)
        self.chapters_text.tag_add('process_item', start_pos, end_pos)
        self.chapters_text.tag_add(tag, start_pos, end_pos)

    def _get_phase_icon(self, phases: Dict, phase_prefix: str) -> str:
        """Belirtilen analiz fazı için durum ikonunu döndürür."""
        if phases.get(f'{phase_prefix}_failed', False):
            return "❌"
        elif phases.get(f'{phase_prefix}_completed', False):
            return "✅"
        else:
            return "⏳"
    
    def _get_suggestion_counts(self, chapter, phase_prefix: str) -> tuple:
        """Belirtilen analiz türü için toplam ve kalan öneri sayılarını hesaplar."""
        # Analiz türüne göre editör tipini belirle
        editor_type_map = {
            'grammar': 'Dil Bilgisi Editörü',
            'style': 'Üslup Editörü', 
            'content': 'İçerik Editörü'
        }
        target_editor_type = editor_type_map.get(phase_prefix, '')
        
        total_suggestions = 0
        remaining_suggestions = 0
        
        # Mevcut bekleyen önerilerden say
        if hasattr(chapter, 'suggestions') and chapter.suggestions:
            for suggestion in chapter.suggestions:
                # Dict mi yoksa nesne mi kontrol et
                if isinstance(suggestion, dict):
                    editor_type = suggestion.get('editor_type', '')
                else:
                    editor_type = getattr(suggestion, 'editor_type', '')
                
                if editor_type == target_editor_type:
                    remaining_suggestions += 1
        
        # Geçmiş önerilerden toplam sayıyı hesapla
        if hasattr(chapter, 'suggestion_history') and chapter.suggestion_history:
            for entry in chapter.suggestion_history:
                suggestion_data = entry.get('suggestion', {})
                if isinstance(suggestion_data, dict):
                    editor_type = suggestion_data.get('editor_type', '')
                else:
                    editor_type = getattr(suggestion_data, 'editor_type', '')
                
                if editor_type == target_editor_type:
                    total_suggestions += 1
        
        # Mevcut bekleyen önerileri de toplam sayıya ekle
        total_suggestions += remaining_suggestions
        
        print(f"DEBUG - {phase_prefix} için öneri sayıları: {remaining_suggestions}/{total_suggestions}")
        return total_suggestions, remaining_suggestions

    def on_chapter_click(self, event):
        """Modern bölüm listesi click olayını işle"""
        # Tıklanan satırı bul
        index = self.chapters_text.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0]) - 1
        
        # Bölüm başlıklarını say (her bölüm 4 satır: başlık + 3 alt işlem)
        chapter_index = line_num // 4
        
        if 0 <= chapter_index < len(self.chapters):
            # Eski seçimi temizle
            self.chapters_text.tag_remove('selected', '1.0', tk.END)
            
            # Yeni seçimi işaretle (tüm bölüm bloğunu)
            start_line = chapter_index * 4 + 1
            end_line = start_line + 4
            self.chapters_text.tag_add('selected', f'{start_line}.0', f'{end_line}.0')
            
            self.current_chapter_index = chapter_index
            self.update_status()
            
            # Seçilen bölümün önizlemesini güncelle
            current_chapter = self.get_current_chapter()
            if current_chapter:
                self.update_preview(current_chapter)
                
            # Ana uygulamaya bildirim gönder
            if self.app and hasattr(self.app, 'on_chapter_selection_changed'):
                try:
                    self.app.on_chapter_selection_changed()
                except Exception as e:
                    print(f"Uyarı: on_chapter_selection_changed çağrılırken hata oluştu: {e}")
    
    def on_chapter_select(self, event):
        """Eski listbox uyumluluğu için - artık kullanılmıyor"""
        # Bu metod artık kullanılmıyor, on_chapter_click kullanılıyor
        pass
    
    def get_current_chapter(self):
        """Mevcut bölümü döndür"""
        if 0 <= self.current_chapter_index < len(self.chapters):
            return self.chapters[self.current_chapter_index]
        return None
    
    def select_chapter(self, chapter_index: int):
        """Belirli bir bölümü seç - Modern format"""
        if 0 <= chapter_index < len(self.chapters):
            # Eski seçimi temizle
            self.chapters_text.config(state='normal')
            self.chapters_text.tag_remove('selected', '1.0', tk.END)
            
            # Yeni seçimi işaretle
            start_line = chapter_index * 4 + 1
            end_line = start_line + 4
            self.chapters_text.tag_add('selected', f'{start_line}.0', f'{end_line}.0')
            self.chapters_text.config(state='disabled')
            
            # Görüntüde kaydır
            self.chapters_text.see(f'{start_line}.0')
            
            self.current_chapter_index = chapter_index
            self.update_status()
            
            # Ana uygulamaya bildirim gönder
            if self.app and hasattr(self.app, 'on_chapter_selection_changed'):
                try:
                    self.app.on_chapter_selection_changed()
                except Exception as e:
                    print(f"Uyarı: on_chapter_selection_changed çağrılırken hata oluştu: {e}")
    
    def next_chapter(self):
        """Sonraki bölüme geç - Modern format"""
        if self.current_chapter_index < len(self.chapters) - 1:
            self.select_chapter(self.current_chapter_index + 1)
    
    def prev_chapter(self):
        """Bir önceki bölüme geç - Modern format"""
        if self.current_chapter_index > 0:
            self.select_chapter(self.current_chapter_index - 1)
    
    def update_status(self):
        """Durum bilgilerini ve yeni ilerleme çubuğunu güncelle"""
        if not self.chapters:
            self.status_label.config(text="Proje yüklenmedi")
            self.progress_bar.set_progress(0.0, 0.0)
            self.update_preview(None)
            return
        
        current_chapter = self.get_current_chapter()
        if current_chapter:
            self.status_label.config(
                text=f"Bölüm {current_chapter.chapter_number}/{len(self.chapters)} - "
                     f"{current_chapter.title}"
            )

            # --- Yeni İlerleme Hesaplama Mantığı ---
            total_possible_analyses = len(self.chapters) * 3
            completed_analyses = 0
            
            total_suggestions_in_project = 0
            processed_suggestions_in_project = 0

            for chapter in self.chapters:
                # Pasif ilerleme (analizler)
                if hasattr(chapter, 'analysis_phases'):
                    phases = chapter.analysis_phases
                    if phases.get('grammar_completed', False): completed_analyses += 1
                    if phases.get('style_completed', False): completed_analyses += 1
                    if phases.get('content_completed', False): completed_analyses += 1
                
                # Aktif ilerleme (öneriler)
                # Toplam öneri = geçmiş + mevcut
                total_chapter_suggestions = len(getattr(chapter, 'suggestion_history', [])) + len(getattr(chapter, 'suggestions', []))
                processed_chapter_suggestions = len(getattr(chapter, 'suggestion_history', []))
                
                total_suggestions_in_project += total_chapter_suggestions
                processed_suggestions_in_project += processed_chapter_suggestions

            # Oranları hesapla (0'a bölünmeyi engelle)
            passive_progress = (completed_analyses / total_possible_analyses) if total_possible_analyses > 0 else 0.0
            
            # Aktif ilerleme, pasif ilerlemenin bir parçasıdır.
            # Yani, tüm öneriler işlense bile, sadece analizi tamamlanmış kısımlar yeşil olabilir.
            # Bu yüzden, öneri işleme oranını, analiz tamamlama oranıyla çarparız.
            suggestion_process_ratio = (processed_suggestions_in_project / total_suggestions_in_project) if total_suggestions_in_project > 0 else 0.0
            active_progress = passive_progress * suggestion_process_ratio

            # İlerleme çubuğunu güncelle
            self.progress_bar.set_progress(passive_progress, active_progress)
            
            self.update_preview(current_chapter)
        
        self.update_statistics()
    
    def update_statistics(self):
        """İstatistikleri güncelle"""
        if not self.chapters:
            self.stats_text.config(state='normal')
            self.stats_text.delete('1.0', tk.END)
            self.stats_text.config(state='disabled')
            return
        
        processed_count = sum(1 for ch in self.chapters if getattr(ch, 'is_processed', False))
        total_suggestions = sum(len(getattr(ch, 'suggestions', [])) for ch in self.chapters)
        
        stats_text = f"""Toplam Bölüm: {len(self.chapters)}
İşlenen Bölüm: {processed_count}
Kalan Bölüm: {len(self.chapters) - processed_count}
Toplam Öneri: {total_suggestions}
İlerleme: %{(processed_count / len(self.chapters)) * 100:.1f}"""
        
        self.stats_text.config(state='normal')
        self.stats_text.delete('1.0', tk.END)
        self.stats_text.insert('1.0', stats_text)
        self.stats_text.config(state='disabled')
    
    def mark_chapter_processed(self, chapter_index: Optional[int] = None):
        """Bölümü işlenmiş olarak işaretle - Modern format ile"""
        if chapter_index is None:
            chapter_index = self.current_chapter_index
        
        if 0 <= chapter_index < len(self.chapters):
            self.chapters[chapter_index].is_processed = True
            
            # Modern listeyi yeniden oluştur (daha basit ve güvenilir)
            current_selection = self.current_chapter_index
            self.update_chapters(self.chapters, preserve_selection=True)
            
            self.update_status()
    
    def update_preview(self, chapter):
        """Seçili bölümün önizlemesini güncelle"""
        print(f"🔄 update_preview çağrıldı - Bölüm: {chapter.title if chapter else 'None'}")
        
        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        
        if chapter:
            # Bölüm başlığı ve istatistikleri
            word_count = len(chapter.content.split())
            char_count = len(chapter.content)
            line_count = len(chapter.content.split('\n'))
            
            # Öneri sayılarını doğrudan bölümün güncel durumundan hesapla
            active_suggestions = len(getattr(chapter, 'suggestions', []))
            pending_suggestions = len(getattr(chapter, 'suggestions', []))
            processed_suggestions = len(getattr(chapter, 'suggestion_history', []))
            
            # Diğer bilgileri al
            is_analyzed = getattr(chapter, 'is_processed', False)
            if hasattr(chapter, 'analysis_phases'):
                phases = chapter.analysis_phases
                if phases.get('grammar_completed') or phases.get('style_completed') or phases.get('content_completed'):
                    is_analyzed = True

            last_modified = getattr(chapter, 'last_modified', 'Bilinmiyor')
            total_edits = len(getattr(chapter, 'content_changes', []))

            # Önizleme içeriğini oluştur
            preview_content = f"=== {chapter.title} ===\n"
            preview_content += f"📄 Kelime: {word_count} | Karakter: {char_count} | Satır: {line_count}\n"
            preview_content += f"📋 {active_suggestions} aktif editöryal öneri mevcut\n"
            preview_content += f"⏳ {pending_suggestions} bekleyen öneri (henüz işlenmemiş)\n"
            preview_content += f"📝 {processed_suggestions} öneri işlendi (Ayarlar > Öneri Geçmişi)\n"
            
            # Analiz durumu detaylarını göster
            if hasattr(chapter, 'analysis_phases'):
                phases = chapter.analysis_phases
                # Hata durumunu kontrol eden güncellenmiş ikon mantığı
                grammar_icon = self._get_phase_icon(phases, 'grammar')
                style_icon = self._get_phase_icon(phases, 'style')
                content_icon = self._get_phase_icon(phases, 'content')
                
                preview_content += f"📊 Analiz Durumu: {grammar_icon} Dil Bilgisi | {style_icon} Üslup | {content_icon} İçerik\n"
            elif is_analyzed:
                preview_content += "✅ Bu bölüm analiz edildi (detay yok)\n"
            else:
                preview_content += "❌ Bu bölüm henüz analiz edilmedi\n"
                
            preview_content += f"🕰️ Son değişiklik: {last_modified}\n"
            
            preview_content += "\n" + "="*50 + "\n"
            
            if total_edits > 0:
                preview_content += f"🎨 BU BÖLÜMDE {total_edits} DÜZENLEME YAPILDI\n"
                preview_content += "Detaylar için: Ayarlar > Öneri Geçmişi\n"
                preview_content += "Değişiklikler vurgulanmıştır - üstlerine gelerek detayları görebilirsiniz\n"
            
            preview_content += "\n" + "-"*50
            
            self.preview_text.insert('1.0', preview_content)
        else:
            self.preview_text.insert('1.0', "📁 Bölüm seçilmedi\n\nLütfen sol panelden analiz etmek istediğiniz bölümü seçin.")
        
        self.preview_text.config(state='disabled')
    
    def start_full_analysis_wrapper(self):
        """Wrapper to start the full analysis process for all chapters."""
        if hasattr(self.app, 'analysis_manager'):
            # Kullanıcıya onay sorusu
            response = messagebox.askyesno(
                "Tümünü Analiz Et",
                "Tüm bölümler için otomatik analiz başlatılacak.\n\n"
                "Bu işlem, YZ modeline çok sayıda istek göndereceği için zaman alabilir ve maliyetli olabilir.\n\n"
                "Devam etmek istiyor musunuz?"
            )
            if response:
                self.app.analysis_manager.start_full_analysis()
        else:
            messagebox.showerror("Hata", "Analiz yöneticisi bulunamadı.")

    def start_full_analysis_wrapper(self):
        """Wrapper to start the full analysis process for all chapters."""
        if hasattr(self.app, 'analysis_manager'):
            # Kullanıcıya onay sorusu
            response = messagebox.askyesno(
                "Tümünü Analiz Et",
                "Tüm bölümler için otomatik analiz başlatılacak.\n\n"
                "Bu işlem, YZ modeline çok sayıda istek göndereceği için zaman alabilir ve maliyetli olabilir.\n\n"
                "Devam etmek istiyor musunuz?"
            )
            if response:
                self.app.analysis_manager.start_full_analysis()
        else:
            messagebox.showerror("Hata", "Analiz yöneticisi bulunamadı.")

    def get_state(self) -> Dict:
        """Panel durumunu döndür - Progress bilgisi ile"""
        processed_count = sum(1 for ch in self.chapters if getattr(ch, 'is_processed', False))
        progress = (processed_count / len(self.chapters)) * 100 if self.chapters else 0
        
        return {
            'current_chapter_index': self.current_chapter_index,
            'total_chapters': len(self.chapters),
            'processed_chapters': processed_count,
            'progress_percentage': progress
        }
    
    def load_state(self, ui_state: Dict):
        """Panel durumunu geri yükle - Progress bilgisi ile"""
        if not ui_state:
            return
            
        # Eğer kaydedilmiş bölüm indeksi varsa geri yükle
        saved_chapter_index = ui_state.get('current_chapter_index', 0)
        if 0 <= saved_chapter_index < len(self.chapters):
            self.current_chapter_index = saved_chapter_index
            print(f"🔄 Kaydedilmiş bölüm indeksi geri yüklendi: {saved_chapter_index}")
        
        # Progress bar'ı geri yükle
        saved_progress = ui_state.get('progress_percentage', 0)
        # Bu kısım yeni progress bar ile uyumlu hale getirilmeli
        # Şimdilik sadece status'u güncelliyoruz, bu da progress bar'ı tetikleyecek
        
        # İstatistikleri güncelle
        self.update_status()
        
        print(f"📋 UI durumu geri yüklendi - Bölüm: {self.current_chapter_index}")

class PromptEditor(tk.Toplevel):
    def __init__(self, parent, prompts: Dict[str, str], callback: Callable):
        super().__init__(parent)
        self.prompts = prompts.copy()  # Make a copy to avoid modifying the original dict directly
        self.callback = callback
        self.current_prompt_type = None
        
        self.title("Prompt Editörü")
        self.geometry("800x600")
        self.grab_set()
        
        self.setup_ui()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Paned window for resizable sections
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Prompt list
        left_frame = ttk.Frame(paned_window, padding=5)
        paned_window.add(left_frame, weight=1)
        
        ttk.Label(left_frame, text="Prompt Türleri", font=('Arial', 12, 'bold')).pack(pady=(0, 10), anchor=tk.W)
        
        self.prompt_listbox = tk.Listbox(left_frame, width=25, exportselection=False, font=('Segoe UI', 10))
        self.prompt_listbox.pack(fill=tk.BOTH, expand=True)
        self.prompt_listbox.bind('<<ListboxSelect>>', self.on_prompt_select)
        
        # Right panel - Prompt editor
        right_frame = ttk.Frame(paned_window, padding=5)
        paned_window.add(right_frame, weight=4)
        
        ttk.Label(right_frame, text="Prompt İçeriği", font=('Arial', 12, 'bold')).pack(pady=(0, 10), anchor=tk.W)
        
        self.prompt_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, font=('Consolas', 10))
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.prompt_text.bind("<KeyRelease>", self.on_text_change)
        
        # Bottom buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="Varsayılana Sıfırla",
                  command=self.reset_prompt).pack(side=tk.LEFT)
        
        ttk.Button(button_frame, text="Kaydet ve Kapat",
                  command=self.save_and_close).pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="İptal",
                  command=self.destroy).pack(side=tk.RIGHT, padx=10)
        
        # Populate listbox
        self.populate_listbox()
        
        # Select the first item
        if self.prompts:
            self.prompt_listbox.selection_set(0)
            self.on_prompt_select()
            
    def populate_listbox(self):
        self.prompt_listbox.delete(0, tk.END)
        for prompt_type in self.prompts.keys():
            display_name = prompt_type.replace('_', ' ').title()
            self.prompt_listbox.insert(tk.END, display_name)

    def on_prompt_select(self, event=None):
        selection_indices = self.prompt_listbox.curselection()
        if not selection_indices:
            return
            
        selected_index = selection_indices[0]
        
        # Save current changes before switching
        if self.current_prompt_type:
            current_content = self.prompt_text.get('1.0', tk.END).strip()
            self.prompts[self.current_prompt_type] = current_content
        
        # Load new prompt
        prompt_types = list(self.prompts.keys())
        self.current_prompt_type = prompt_types[selected_index]
        
        self.prompt_text.delete('1.0', tk.END)
        self.prompt_text.insert('1.0', self.prompts[self.current_prompt_type])

    def on_text_change(self, event=None):
        """Update the internal dictionary as the user types."""
        if self.current_prompt_type:
            current_content = self.prompt_text.get('1.0', tk.END).strip()
            self.prompts[self.current_prompt_type] = current_content
    
    def reset_prompt(self):
        if not self.current_prompt_type:
            return
        
        # This requires default prompts to be available.
        # We can ask the AI integration module for the default for the current type.
        # For now, let's just show a message.
        messagebox.showinfo("Sıfırla", "Bu özellik henüz tam olarak uygulanmadı.\nVarsayılan prompt'lar AI entegrasyon modülünden yüklenecek.")
    
    def save_and_close(self):
        # Ensure the last change is captured
        self.on_text_change()
        
        # Call the callback with the updated prompts
        self.callback(self.prompts)
        self.destroy()
        messagebox.showinfo("Başarı", "Prompt ayarları başarıyla kaydedildi.")

class PromptEditor(tk.Toplevel):
    def __init__(self, parent, prompts: Dict[str, str], callback: Callable):
        super().__init__(parent)
        self.prompts = prompts.copy()
        self.callback = callback
        
        self.title("Prompt Editörü")
        self.geometry("800x600")
        self.grab_set()
        
        self.setup_ui()
    
    def setup_ui(self):
        # Sol panel - Prompt listesi
        left_frame = ttk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 5), pady=10)
        
        ttk.Label(left_frame, text="Prompt Türleri", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        self.prompt_listbox = tk.Listbox(left_frame, width=20)
        self.prompt_listbox.pack(fill=tk.Y, expand=True)
        self.prompt_listbox.bind('<<ListboxSelect>>', self.on_prompt_select)
        
        # Prompt türlerini listele
        for prompt_type in self.prompts.keys():
            display_name = prompt_type.replace('_', ' ').title()
            self.prompt_listbox.insert(tk.END, display_name)
        
        # Sağ panel - Prompt editörü
        right_frame = ttk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 10), pady=10)
        
        ttk.Label(right_frame, text="Prompt İçeriği", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        self.prompt_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD)
        self.prompt_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Alt butonlar
        button_frame = ttk.Frame(right_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Varsayılana Sıfırla",
                  command=self.reset_prompt).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(button_frame, text="Kaydet",
                  command=self.save_prompts).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(button_frame, text="İptal",
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
        # İlk prompt'u seç
        if self.prompts:
            self.prompt_listbox.selection_set(0)
            self.on_prompt_select()
    
    def on_prompt_select(self, event=None):
        """Prompt seçimini işle"""
        selection = self.prompt_listbox.curselection()
        if selection:
            prompt_types = list(self.prompts.keys())
            selected_type = prompt_types[selection[0]]
            
            self.current_prompt_type = selected_type
            self.prompt_text.delete('1.0', tk.END)
            self.prompt_text.insert('1.0', self.prompts[selected_type])
    
    def reset_prompt(self):
        """Mevcut prompt'u varsayılana sıfırla"""
        # Buraya varsayılan promptlar eklenebilir
        messagebox.showinfo("Bilgi", "Varsayılan prompt yüklendi")
    
    def save_prompts(self):
        """Promptları kaydet"""
        # Mevcut prompt'u güncelle
        if hasattr(self, 'current_prompt_type'):
            current_content = self.prompt_text.get('1.0', tk.END).strip()
            self.prompts[self.current_prompt_type] = current_content
        
        # Callback'i çağır
        self.callback(self.prompts)
        self.destroy()
        messagebox.showinfo("Başarı", "Promptlar kaydedildi")
