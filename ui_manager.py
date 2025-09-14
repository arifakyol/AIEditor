import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
import sys
import datetime
import threading
import time
import re
import uuid
import webbrowser

# Import modules
from modules.file_manager import FileManager
from modules.ai_integration import AIIntegration
from modules.editorial_process import EditorialProcess
from modules.settings_manager import SettingsManager
from modules.ui_components import SuggestionCard, ProjectPanel
from modules.formatting_manager import FormattingManager

class UIManager:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.icons = {}  # To prevent garbage collection
        self.formatting_manager = FormattingManager()
        # Don't call setup_ui here anymore, it will be called from main.py

    def _create_icon(self, align_type, width=22, height=22):
        """Creates an alignment icon image programmatically."""
        image = tk.PhotoImage(width=width, height=height)
        line_color = "#333333"  # Dark gray

        # Define line patterns (lengths and positions)
        lines = [18, 14, 18, 12, 16]
        y_start = 5  # Start drawing from y=5

        for i, line_length in enumerate(lines):
            y = y_start + i * 3  # 3 pixels per line (1 for line, 2 for gap)
            
            if align_type == "left":
                x_start = 2
            elif align_type == "center":
                x_start = (width - line_length) // 2
            elif align_type == "right":
                x_start = width - line_length - 2
            
            for x in range(x_start, x_start + line_length):
                image.put(line_color, (x, y))
        
        return image

    def _create_tooltip(self, widget, text):
        """Creates a tooltip for a given widget."""
        def on_enter(event):
            self._show_widget_tooltip(event, text)
        
        def on_leave(event):
            self._hide_tooltip()

        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    def _show_widget_tooltip(self, event, text):
        """Shows a simple tooltip for a widget."""
        if hasattr(self.app, 'tooltip_label') and self.app.tooltip_label:
            self.app.tooltip_label.destroy()
        
        self.app.tooltip_label = tk.Toplevel(self.root)
        self.app.tooltip_label.wm_overrideredirect(True)
        self.app.tooltip_label.configure(bg="#ffffe0", relief="solid", borderwidth=1)
        
        label = tk.Label(self.app.tooltip_label, text=text, 
                        background="#ffffe0", foreground="black", 
                        font=('Arial', 9), justify=tk.LEFT,
                        padx=8, pady=5)
        label.pack()
        
        widget = event.widget
        x = widget.winfo_rootx()
        y = widget.winfo_rooty() + widget.winfo_height() + 5
        
        self.app.tooltip_label.geometry(f"+{x}+{y}")

    def setup_ui(self):
        # Main menu
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        self.file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Dosya", menu=self.file_menu)
        self.file_menu.add_command(label="Romanı Yükle", command=self.app.load_novel)
        self.file_menu.add_command(label="Projeyi Kaydet", command=self.app.save_project)
        self.file_menu.add_command(label="Proje Aç", command=self.app.load_project)
        self.file_menu.add_command(label="Proje Geçmişi", command=self.app.load_project_history, state=tk.DISABLED)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Dışa Aktar (TXT)", command=self.app.export_as_txt)
        self.file_menu.add_command(label="Dışa Aktar (DOCX)", command=self.app.export_as_docx)

        # Set postcommand to update menu states dynamically
        self.file_menu.config(postcommand=self.update_file_menu_state)
        
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayarlar", menu=settings_menu)
        settings_menu.add_command(label="Yapay Zeka Ayarları", command=self.app.open_ai_settings)
        settings_menu.add_command(label="Prompt Ayarları", command=self.app.open_prompt_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Otomatik Kaydetme", command=self.app.open_auto_save_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Öneri Geçmişi", command=self.app.show_suggestion_history)
        settings_menu.add_separator()
        settings_menu.add_command(label="Hata Ayıklama Konsolu", command=self.app.open_debug_console)
        settings_menu.add_separator()
        settings_menu.add_command(label="Roman Bağlamını Görüntüle", command=self.app.show_novel_context)
        settings_menu.add_separator()
        settings_menu.add_command(label="Proje Durumunu Kontrol Et", command=self.app.check_project_status)
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Project information and chapters
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        
        self.app.project_panel = ProjectPanel(left_frame, self.app)
        self.app.project_panel.pack(fill=tk.BOTH, expand=True)

        # --- GitHub Link ---
        github_label = tk.Label(left_frame, text="Developed by @arifakyol", fg="blue", cursor="hand2", font=('Arial', 8))
        github_label.pack(side=tk.BOTTOM, anchor='w', padx=5, pady=5)
        github_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/arifakyol"))
        self._create_tooltip(github_label, "GitHub profilini aç")
        
        # Right panel - Editorial process
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Right panel title
        ttk.Label(right_frame, text="Editöryal Süreç", font=('Arial', 14, 'bold')).pack(pady=(0, 10))
        
        # Status message area
        status_frame = ttk.Frame(right_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.app.status_message_label = ttk.Label(status_frame, 
                                             text="📚 Bir roman yükleyin ve bir bölüm seçin. Ardından sırasıyla Dil Bilgisi → Üslup → İçerik analizini başlatın.", 
                                             font=('Arial', 10), wraplength=400)
        self.app.status_message_label.pack()
        
        # Progress bar (hidden by default)
        self.app.progress_frame = ttk.Frame(status_frame)
        self.app.progress_bar = ttk.Progressbar(self.app.progress_frame, mode='indeterminate')
        self.app.progress_bar.pack(fill=tk.X, pady=5)
        self.app.progress_label = ttk.Label(self.app.progress_frame, text="", font=('Arial', 9))
        self.app.progress_label.pack()
        
        # Chapter content display area
        content_frame = ttk.LabelFrame(right_frame, text="Seçili Bölüm İçeriği", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Formatting Toolbar
        toolbar_frame = ttk.Frame(content_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))

        # Use standard tk.Button for reliable relief styling
        self.format_buttons = {}

        # Generate icons
        self.icons["left"] = self._create_icon("left")
        self.icons["center"] = self._create_icon("center")
        self.icons["right"] = self._create_icon("right")
        
        # Blank image for sizing text buttons in pixels
        blank_image = tk.PhotoImage()

        button_defs = [
            ("bold", "B", "Kalın", lambda: self.toggle_format("bold")),
            ("italic", "I", "İtalik", lambda: self.toggle_format("italic")),
            ("underline", "U", "Altı Çizili", lambda: self.toggle_format("underline")),
            ("separator",),
            ("left", self.icons["left"], "Sola Hizala", lambda: self.apply_paragraph_format("left")),
            ("centered", self.icons["center"], "Ortala", lambda: self.apply_paragraph_format("centered")),
            ("right_aligned", self.icons["right"], "Sağa Hizala", lambda: self.apply_paragraph_format("right_aligned")),
            ("separator",),
            ("heading", "¶", "Başlık", lambda: self.apply_paragraph_format("heading")),
        ]

        for b_def in button_defs:
            if b_def[0] == "separator":
                separator = ttk.Separator(toolbar_frame, orient='vertical')
                separator.pack(side=tk.LEFT, padx=5, fill='y')
                continue

            key, icon_or_image, tooltip, command = b_def
            
            if isinstance(icon_or_image, str): # It's a text-based icon
                font_style = ('Arial', 10)
                if key == "bold": font_style = ('Arial', 10, 'bold')
                elif key == "italic": font_style = ('Arial', 10, 'italic')
                elif key == "underline": font_style = ('Arial', 10, 'underline')
                
                button = tk.Button(toolbar_frame, 
                                   text=icon_or_image, 
                                   font=font_style, 
                                   command=command, 
                                   relief=tk.RAISED, 
                                   width=3, 
                                   height=1)
            else: # It's a PhotoImage
                button = tk.Button(toolbar_frame, 
                                   image=icon_or_image, 
                                   command=command, 
                                   relief=tk.RAISED, 
                                   width=28, 
                                   height=28)

            button.pack(side=tk.LEFT, padx=1)
            
            self.format_buttons[key] = button
            self._create_tooltip(button, tooltip)
        
        self.app.chapter_content_text = tk.Text(content_frame, height=15, wrap=tk.WORD, 
                                           font=('Arial', 10), state='normal')
        content_scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, 
                                         command=self.app.chapter_content_text.yview)
        self.app.chapter_content_text.configure(yscrollcommand=content_scrollbar.set)
        
        self.app.chapter_content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Suggestions frame
        suggestions_label_frame = ttk.LabelFrame(right_frame, text="Editöryal Öneriler", padding=10)
        suggestions_label_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrollable suggestions area
        self.app.suggestions_canvas = tk.Canvas(suggestions_label_frame)
        self.app.suggestions_scrollbar = ttk.Scrollbar(suggestions_label_frame, orient="vertical", command=self.app.suggestions_canvas.yview)
        self.app.suggestions_scrollable_frame = ttk.Frame(self.app.suggestions_canvas)
        
        self.app.suggestions_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.app.suggestions_canvas.configure(scrollregion=self.app.suggestions_canvas.bbox("all"))
        )
        
        self.app.suggestions_canvas.create_window((0, 0), window=self.app.suggestions_scrollable_frame, anchor="nw")
        self.app.suggestions_canvas.configure(yscrollcommand=self.app.suggestions_scrollbar.set)
        
        self.app.suggestions_canvas.pack(side="left", fill="both", expand=True)
        self.app.suggestions_scrollbar.pack(side="right", fill="y")
        
        # Binding for mouse wheel
        def _on_mousewheel(event):
            self.app.suggestions_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.app.suggestions_canvas.bind("<MouseWheel>", _on_mousewheel)
        
        self.app.suggestions_frame = self.app.suggestions_scrollable_frame
        
        # "No suggestions" message label, centered in the main frame
        self.app.no_suggestions_label = ttk.Label(
            suggestions_label_frame, # Parent is the LabelFrame
            text="",
            font=('Arial', 11),
            justify=tk.CENTER,
            wraplength=500
        )
        
        # Bottom control panel
        control_frame = ttk.Frame(right_frame)
        control_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Store reference to analysis button
        self.app.analysis_button = ttk.Button(control_frame, text="Dil Bilgisi Analizi", command=self.start_analysis_wrapper)
        self.app.analysis_button.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(control_frame, text="Sonraki Bölüm", command=self.app.next_chapter).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Önceki Bölüm", command=self.app.prev_chapter).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Tümünü Uygula", command=self.app.apply_all_suggestions).pack(side=tk.RIGHT, padx=5)

        # --- Kullanıcı Vurgulama Özelliği için Sağ Tıklama Menüsü ---
        self._setup_right_click_menu()

    def update_file_menu_state(self):
        """Updates the state of items in the File menu."""
        last_project = self.app.settings_manager.get_setting('last_project')
        is_project_open = last_project is not None

        # Enable/disable "Proje Geçmişi"
        if is_project_open:
            self.file_menu.entryconfig("Proje Geçmişi", state=tk.NORMAL)
        else:
            self.file_menu.entryconfig("Proje Geçmişi", state=tk.DISABLED)

    def _setup_right_click_menu(self):
        """Metin alanı için sağ tıklama menüsünü oluşturur ve olayı bağlar."""
        self.right_click_menu = tk.Menu(self.app.chapter_content_text, tearoff=0)
        self.app.chapter_content_text.bind("<Button-3>", self._on_right_click)

    def _on_right_click(self, event):
        """Sağ tıklama olayını yönetir ve bağlama göre dinamik menü gösterir."""
        # Menüyü her seferinde temizle ve yeniden oluştur
        self.right_click_menu.delete(0, tk.END)
        
        # Tıklanan pozisyondaki etiketleri al
        click_index = self.app.chapter_content_text.index(f"@{event.x},{event.y}")
        tags_at_click = self.app.chapter_content_text.tag_names(click_index)
        
        # Kullanıcı tarafından eklenmiş bir vurgu var mı kontrol et
        user_highlight_tag = None
        for tag in tags_at_click:
            if tag.startswith("highlight_Kullanıcı_Notu_note_"):
                user_highlight_tag = tag
                break
        
        # Metin seçiliyse "Ekle" seçeneğini göster
        selection_exists = self.app.chapter_content_text.tag_ranges("sel")
        
        action_taken = False
        if user_highlight_tag:
            # Vurgu varsa "Kaldır" seçeneğini ekle
            self.right_click_menu.add_command(
                label="Vurgulamayı Kaldır", 
                command=lambda t=user_highlight_tag: self._remove_user_highlight(t)
            )
            action_taken = True
        
        if selection_exists:
            self.right_click_menu.add_command(
                label="Vurgula ve Açıklama Ekle", 
                command=self._add_user_highlight
            )
            self.right_click_menu.add_separator()
            self.right_click_menu.add_command(
                label="Seçimde Dil Bilgisi Analizi Yap",
                command=self.start_selection_analysis_wrapper
            )
            action_taken = True

        # Eğer menüde en az bir seçenek varsa göster
        if action_taken:
            self.right_click_menu.tk_popup(event.x_root, event.y_root)

    def _map_clean_to_raw_offset(self, raw_text, clean_offset):
        """Maps a clean text offset to a raw text offset, correctly handling markers."""
        clean_chars_seen = 0
        raw_pos = 0
        markers = ['###', '>>>', '<<<', '*B*', '*I*', '*U*', '{', '}']

        # Special case for the start of the selection (offset 0)
        # We need to find the position of the very first content character.
        if clean_offset == 0:
            while raw_pos < len(raw_text):
                is_marker = False
                for marker in markers:
                    if raw_text.startswith(marker, raw_pos):
                        raw_pos += len(marker)
                        is_marker = True
                        break
                if not is_marker:
                    return raw_pos  # Found the start of the first character
            return raw_pos  # Reached end of string

        # For other offsets, we need to find the position *after* the Nth character.
        while raw_pos < len(raw_text):
            is_marker = False
            for marker in markers:
                if raw_text.startswith(marker, raw_pos):
                    raw_pos += len(marker)
                    is_marker = True
                    break
            
            if not is_marker:
                # It's a content character
                raw_pos += 1
                clean_chars_seen += 1
                if clean_chars_seen == clean_offset:
                    return raw_pos # Found the position right after the target character
        
        return raw_pos # Fallback for offsets beyond the text length

    def toggle_format(self, format_type):
        """Toggles formatting by modifying the data model directly and then re-rendering."""
        current_chapter = self.app.get_current_chapter()
        if not current_chapter:
            return

        try:
            text_widget = self.app.chapter_content_text
            if not text_widget.tag_ranges("sel"):
                return

            # 1. Save view state
            scroll_pos = text_widget.yview()
            sel_start_index, sel_end_index = text_widget.tag_ranges("sel")
            sel_start_offset = len(text_widget.get("1.0", sel_start_index))
            sel_end_offset = len(text_widget.get("1.0", sel_end_index))

            # 2. Map to raw content to find the line(s) affected
            raw_content = current_chapter.content
            raw_sel_start = self._map_clean_to_raw_offset(raw_content, sel_start_offset)
            
            # Find the start and end of the line(s) in the raw content
            raw_line_start = raw_content.rfind('\n', 0, raw_sel_start) + 1
            raw_line_end = raw_content.find('\n', raw_sel_start)
            if raw_line_end == -1:
                raw_line_end = len(raw_content)
            
            raw_line = raw_content[raw_line_start:raw_line_end]

            # 3. Isolate paragraph markers and the actual content of the line
            p_markers = [("###", "###"), ("{", "}"), (">>>", "<<<")]
            line_content = raw_line
            p_start_marker, p_end_marker = "", ""

            for start_m, end_m in p_markers:
                if line_content.startswith(start_m) and line_content.endswith(end_m):
                    p_start_marker, p_end_marker = start_m, end_m
                    line_content = line_content[len(start_m):-len(end_m)]
                    break
            
            # 4. Map selection offsets to be relative to the line_content
            # The clean text of the line does not include paragraph markers.
            clean_line_start_offset = len(text_widget.get("1.0", f"{sel_start_index} linestart"))
            
            # The raw offset of the line's content start (after any paragraph marker)
            raw_content_start_in_line = raw_line.find(line_content)
            
            # Map the clean selection start to the raw line_content
            start_offset_in_clean_line = sel_start_offset - clean_line_start_offset
            raw_start_in_line_content = self._map_clean_to_raw_offset(line_content, start_offset_in_clean_line)
            
            # Map the clean selection end to the raw line_content
            end_offset_in_clean_line = sel_end_offset - clean_line_start_offset
            raw_end_in_line_content = self._map_clean_to_raw_offset(line_content, end_offset_in_clean_line)

            # 5. Apply the inline formatting to the selected part of line_content
            selected_text = line_content[raw_start_in_line_content:raw_end_in_line_content]
            inline_markers = {"bold": "*B*", "italic": "*I*", "underline": "*U*"}
            marker = inline_markers[format_type]

            # Check if the selected text is already formatted
            is_formatted = selected_text.startswith(marker) and selected_text.endswith(marker)

            if is_formatted:
                # Remove formatting
                new_slice = selected_text[len(marker):-len(marker)]
            else:
                # Add formatting
                new_slice = f"{marker}{selected_text}{marker}"
            
            # Reconstruct the line's content
            new_line_content = (line_content[:raw_start_in_line_content] + 
                                new_slice + 
                                line_content[raw_end_in_line_content:])

            # 6. Re-assemble the full line with its paragraph markers
            new_full_line = f"{p_start_marker}{new_line_content}{p_end_marker}"

            # 7. Update the main data model
            current_chapter.content = raw_content[:raw_line_start] + new_full_line + raw_content[raw_line_end:]
            self.app.mark_as_modified()

            # 8. Re-render and restore view state
            self.display_chapter_content(current_chapter)
            
            new_sel_start_index = text_widget.index(f"1.0 + {sel_start_offset} chars")
            # The length of the new selection might have changed
            new_sel_len = len(text_widget.get(new_sel_start_index, f"{new_sel_start_index} + {sel_end_offset - sel_start_offset} chars"))
            new_sel_end_index = text_widget.index(f"{new_sel_start_index} + {new_sel_len} chars")

            text_widget.tag_add("sel", new_sel_start_index, new_sel_end_index)
            text_widget.yview_moveto(scroll_pos[0])
            text_widget.focus_set()

        except tk.TclError:
            pass # Selection error
        except Exception as e:
            messagebox.showerror("Hata", f"Biçimlendirme sırasında bir hata oluştu: {e}")

    def apply_paragraph_format(self, format_type):
        """Applies paragraph-level formatting to the current line."""
        current_chapter = self.app.get_current_chapter()
        if not current_chapter:
            return

        try:
            text_widget = self.app.chapter_content_text
            
            # 1. Save view state
            scroll_pos = text_widget.yview()
            cursor_index = text_widget.index(tk.INSERT)
            
            # 2. Get the clean text of the current line and its start offset
            line_start_index = text_widget.index(f"{cursor_index} linestart")
            line_end_index = text_widget.index(f"{cursor_index} lineend")
            current_line_clean_text = text_widget.get(line_start_index, line_end_index)
            line_start_offset = len(text_widget.get("1.0", line_start_index))

            # 3. Map to raw content to find the actual line
            raw_content = current_chapter.content
            raw_line_start_offset = self._map_clean_to_raw_offset(raw_content, line_start_offset)
            
            # Find the start and end of the line in the raw content
            raw_line_start = raw_content.rfind('\n', 0, raw_line_start_offset) + 1
            raw_line_end = raw_content.find('\n', raw_line_start_offset)
            if raw_line_end == -1:
                raw_line_end = len(raw_content)
            
            raw_line = raw_content[raw_line_start:raw_line_end]

            # 4. Strip existing paragraph markers
            stripped_line = raw_line.strip()
            markers_to_strip = [("###", "###"), ("{", "}"), (">>>", "<<<")]
            for start_marker, end_marker in markers_to_strip:
                if stripped_line.startswith(start_marker) and stripped_line.endswith(end_marker):
                    stripped_line = stripped_line[len(start_marker):-len(end_marker)]
                    break
            
            # 5. Apply new markers
            new_line = stripped_line
            if format_type == "heading":
                new_line = f"###{stripped_line}###"
            elif format_type == "centered":
                new_line = f"{{{stripped_line}}}"
            elif format_type == "right_aligned":
                new_line = f">>>{stripped_line}<<<"
            # "left" format simply uses the stripped line

            # 6. Reconstruct content and update data model
            current_chapter.content = raw_content[:raw_line_start] + new_line + raw_content[raw_line_end:]
            self.app.mark_as_modified()

            # 7. Re-render and restore state
            self.display_chapter_content(current_chapter)
            
            # Restore cursor and scroll position
            new_cursor_index = text_widget.index(f"1.0 + {line_start_offset} chars")
            text_widget.mark_set(tk.INSERT, new_cursor_index)
            text_widget.yview_moveto(scroll_pos[0])
            text_widget.focus_set()

        except Exception as e:
            messagebox.showerror("Hata", f"Paragraf biçimlendirme sırasında bir hata oluştu: {e}")

    def _update_format_toolbar_state(self, event=None):
        """Updates the formatting toolbar based on the tags at the cursor or selection."""
        try:
            text_widget = self.app.chapter_content_text
            
            # Determine the tags to check - from selection if it exists, otherwise from cursor
            if text_widget.tag_ranges("sel"):
                tags = text_widget.tag_names("sel.first")
            else:
                tags = text_widget.tag_names(tk.INSERT)

            # Inline styles
            bold_active = any(t in tags for t in ['bold', 'bold_italic', 'bold_underline', 'bold_italic_underline'])
            italic_active = any(t in tags for t in ['italic', 'bold_italic', 'italic_underline', 'bold_italic_underline'])
            underline_active = any(t in tags for t in ['underline', 'bold_underline', 'italic_underline', 'bold_italic_underline'])
            
            self.format_buttons["bold"].config(relief=tk.SUNKEN if bold_active else tk.RAISED)
            self.format_buttons["italic"].config(relief=tk.SUNKEN if italic_active else tk.RAISED)
            self.format_buttons["underline"].config(relief=tk.SUNKEN if underline_active else tk.RAISED)

            # Paragraph styles
            heading_active = 'heading' in tags
            self.format_buttons["heading"].config(relief=tk.SUNKEN if heading_active else tk.RAISED)

            # Alignment - only one can be active
            align_state = "left" # Default
            if 'centered' in tags:
                align_state = "centered"
            elif 'right_aligned' in tags:
                align_state = "right_aligned"
            
            self.format_buttons["left"].config(relief=tk.SUNKEN if align_state == "left" and not heading_active else tk.RAISED)
            self.format_buttons["centered"].config(relief=tk.SUNKEN if align_state == "centered" and not heading_active else tk.RAISED)
            self.format_buttons["right_aligned"].config(relief=tk.SUNKEN if align_state == "right_aligned" and not heading_active else tk.RAISED)

        except tk.TclError:
            pass # Widget might not be ready
        except Exception as e:
            print(f"Toolbar state update error: {e}")

    def _add_user_highlight(self):
        """Kullanıcının seçtiği metne vurgu ve açıklama ekler."""
        try:
            selected_text = self.app.chapter_content_text.get("sel.first", "sel.last")
            if not selected_text.strip():
                return

            explanation = simpledialog.askstring("Açıklama Ekle", 
                                                 "Bu vurgulama için bir açıklama girin:",
                                                 parent=self.root)
            
            if explanation:
                chapter = self.app.get_current_chapter()
                if not chapter:
                    messagebox.showwarning("Hata", "Aktif bir bölüm bulunamadı.")
                    return

                if not hasattr(chapter, 'highlighting_info'):
                    chapter.highlighting_info = {}

                # Benzersiz bir ID oluştur
                highlight_id = f"user_{uuid.uuid4().hex[:8]}"
                
                # Vurgu bilgilerini kaydet
                chapter.highlighting_info[highlight_id] = {
                    'text': selected_text,
                    'explanation': explanation,
                    'editor_type': 'Kullanıcı Notu',
                    'severity': 'note'  # Özel bir severity tipi
                }

                # Görsel olarak etiketi uygula
                tag_name = f"highlight_Kullanıcı_Notu_note_{highlight_id}"
                bg_color, fg_color = self._get_highlight_colors('Kullanıcı Notu', 'note')
                self.app.chapter_content_text.tag_configure(tag_name, background=bg_color, foreground=fg_color)
                self.app.chapter_content_text.tag_add(tag_name, "sel.first", "sel.last")
                
                # İpucu olaylarını bağla
                self._bind_tooltip_events(tag_name, "", selected_text, explanation, 'Kullanıcı Notu')
                
                self.app.mark_as_modified()
                print(f"Kullanıcı notu başarıyla eklendi: {highlight_id}")

        except tk.TclError:
            # Genellikle seçim olmadığında bu hata oluşur, sessizce geçebiliriz.
            pass
        except Exception as e:
            messagebox.showerror("Hata", f"Vurgu eklenirken bir hata oluştu: {e}")

    def _remove_user_highlight(self, tag_name: str):
        """Kullanıcının eklediği bir vurguyu kaldırır."""
        try:
            # Tag'den highlight_id'yi çıkar (daha güvenilir yöntem)
            prefix = "highlight_Kullanıcı_Notu_note_"
            if not tag_name.startswith(prefix):
                print(f"Hatalı etiket formatı, kaldırılamadı: {tag_name}")
                return
            
            highlight_id = tag_name[len(prefix):]

            chapter = self.app.get_current_chapter()
            if not chapter or not hasattr(chapter, 'highlighting_info'):
                return

            # Vurgu bilgisini chapter nesnesinden sil
            if highlight_id in chapter.highlighting_info:
                del chapter.highlighting_info[highlight_id]
                
                # Text widget'tan etiketi kaldır
                self.app.chapter_content_text.tag_remove(tag_name, '1.0', tk.END)
                
                self.app.mark_as_modified()
                print(f"Kullanıcı notu başarıyla kaldırıldı: {highlight_id}")
            else:
                print(f"Kaldırılacak vurgu bulunamadı: {highlight_id}")

        except Exception as e:
            messagebox.showerror("Hata", f"Vurgu kaldırılırken bir hata oluştu: {e}")

    def show_analysis_status(self, message: str = "", color: str = "black"):
        """Analiz durumu mesajını göster"""
        if self.app.status_message_label:
            self.app.status_message_label.config(text=message, foreground=color)
            self.root.update()  # Update UI immediately

    def show_progress(self, message: str = ""):
        """İlerleme çubuğunu göster ve başlat"""
        self.app.progress_frame.pack(fill=tk.X, pady=(5, 0))
        self.app.progress_bar.start(50)  # Animate every 50ms (more aesthetic)
        if message:
            self.app.progress_label.config(text=message)
        self.root.update()

    def hide_progress(self):
        """İlerleme çubuğunu gizle ve durdur"""
        self.app.progress_bar.stop()
        self.app.progress_frame.pack_forget()
        self.root.update()

    def display_chapter_content(self, chapter=None):
        """Display chapter content - Word compatible"""
        self.app.chapter_content_text.config(state='normal')
        self.app.chapter_content_text.delete('1.0', tk.END)
        
        if chapter is not None:
            # Define tags (Word compatible formatting)
            self.app.chapter_content_text.tag_configure('chapter_title', 
                                                 font=('Arial', 16, 'bold'), 
                                                 spacing3=15)
            self.app.chapter_content_text.tag_configure('heading', 
                                                 font=('Arial', 14, 'bold'), 
                                                 spacing3=10)
            self.app.chapter_content_text.tag_configure('centered', 
                                                 font=('Arial', 11), 
                                                 justify='center',
                                                 spacing1=5, 
                                                 spacing3=5)
            self.app.chapter_content_text.tag_configure('right_aligned',
                                                 font=('Arial', 11),
                                                 justify='right',
                                                 spacing1=5,
                                                 spacing3=5)
            self.app.chapter_content_text.tag_configure('paragraph', 
                                                 font=('Arial', 11), 
                                                 spacing1=5, 
                                                 spacing3=5)
            
            # Formatting tags
            self.app.chapter_content_text.tag_configure('bold', font=('Arial', 11, 'bold'))
            self.app.chapter_content_text.tag_configure('italic', font=('Arial', 11, 'italic'))
            self.app.chapter_content_text.tag_configure('underline', underline=True)
            # --- Combinations for proper nesting ---
            self.app.chapter_content_text.tag_configure('bold_italic', font=('Arial', 11, 'bold italic'))
            self.app.chapter_content_text.tag_configure('bold_underline', font=('Arial', 11, 'bold'), underline=True)
            self.app.chapter_content_text.tag_configure('italic_underline', font=('Arial', 11, 'italic'), underline=True)
            self.app.chapter_content_text.tag_configure('bold_italic_underline', font=('Arial', 11, 'bold italic'), underline=True)

            # Split content into paragraphs and add
            lines = chapter.content.split('\n')
            for line in lines:
                paragraph_tag = 'paragraph'  # Default tag
                text_to_process = line

                # Determine paragraph-level tag and strip markers
                if line.startswith('###') and line.endswith('###'):
                    text_to_process = line[3:-3]
                    paragraph_tag = 'heading'
                elif line.startswith('{') and line.endswith('}'):
                    text_to_process = line[1:-1]
                    paragraph_tag = 'centered'
                elif line.startswith('>>>') and line.endswith('<<<'):
                    text_to_process = line[3:-3]
                    paragraph_tag = 'right_aligned'

                # Get start position for the paragraph tag
                start_index = self.app.chapter_content_text.index(f"{tk.END}-1c")
                
                # Insert the content with inline formatting
                if text_to_process:
                    self._insert_formatted_text(self.app.chapter_content_text, text_to_process)
                
                # Insert the newline
                self.app.chapter_content_text.insert(tk.END, '\n')
                
                # Get end position
                end_index = self.app.chapter_content_text.index(f"{tk.END}-1c")
                
                # Apply the paragraph-level tag to the entire line
                self.app.chapter_content_text.tag_add(paragraph_tag, start_index, end_index)
            
            # --- Vurgulamaları uygula ---
            # İçeriğin başlangıç indeksini al (başlık sonrası)
            content_start_index = '1.0'
            self._highlight_changes(chapter, content_start_index)

            # Metin alanındaki değişiklikleri anında chapter nesnesine kaydet
            def on_content_change(event):
                if chapter:
                    new_content = self.formatting_manager.convert_text_to_raw_content(self.app.chapter_content_text)
                    if chapter.content != new_content:
                        chapter.content = new_content
                        chapter.last_modified = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        self.app.mark_as_modified()
                        print(f"Bölüm {chapter.chapter_number} içeriği güncellendi (biçimlendirme korundu).")

            # Önceki binding'leri temizle ve yenisini ekle
            self.app.chapter_content_text.unbind("<KeyRelease>")
            self.app.chapter_content_text.unbind("<ButtonRelease-1>")
            self.app.chapter_content_text.bind("<KeyRelease>", on_content_change)
            self.app.chapter_content_text.bind("<<ContentChanged>>", on_content_change)
            
            # Bind cursor movement to update toolbar state
            self.app.chapter_content_text.bind("<KeyRelease>", self._update_format_toolbar_state, add="+")
            self.app.chapter_content_text.bind("<ButtonRelease-1>", self._update_format_toolbar_state, add="+")
            
            # Initial update
            self._update_format_toolbar_state()

    def _insert_formatted_text(self, text_widget, text: str):
        """Wrapper to call the formatting manager's method."""
        self.formatting_manager.insert_formatted_text(text_widget, text)

    def _highlight_changes(self, chapter, content_start_index):
        """Highlight changes in chapter content - With saved highlighting information"""
        # Safety check - chapter can be None
        if not chapter:
            return
            
        if not hasattr(chapter, 'suggestion_history') or not chapter.suggestion_history:
            # If no suggestion history, but highlighting_info exists, use it
            if hasattr(chapter, 'highlighting_info') and chapter.highlighting_info:
                self._apply_saved_highlighting(chapter, content_start_index)
            return
            
        # Define change colors
        self.app.chapter_content_text.tag_configure("changed_text", background="#e6f3ff", foreground="#0066cc")
        self.app.chapter_content_text.tag_configure("grammar_change", background="#e6ffe6", foreground="#006600")
        self.app.chapter_content_text.tag_configure("style_change", background="#fff0e6", foreground="#cc6600")
        self.app.chapter_content_text.tag_configure("content_change", background="#ffe6f0", foreground="#cc0066")
        
        # Tooltip system - create tooltip label
        if not hasattr(self.app, 'tooltip_label'):
            self.app.tooltip_label = None
        
        change_counter = 0
        
        # First try to use saved highlighting_info
        if hasattr(chapter, 'highlighting_info') and chapter.highlighting_info:
            self._apply_saved_highlighting(chapter, content_start_index)
            return
        
        # If no highlighting_info, create from suggestion history
        for entry in chapter.suggestion_history:
            if entry['action'] != 'apply':  # Only highlight applied changes
                continue
                
            suggested_text = entry.get('suggested_text', '')
            original_text = entry.get('original_text', '')
            explanation = entry.get('explanation', 'Açıklama mevcut değil')
            
            if not suggested_text or not original_text:
                continue
                
            # Find text
            change_counter += 1
            tag_name = f"change_{change_counter}"
            
            # Get editor type - check suggestion object
            editor_info = "Bilinmeyen Editör"
            suggestion_obj = entry.get('suggestion')
            if suggestion_obj:
                # If EditorialSuggestion object
                if hasattr(suggestion_obj, 'editor_type'):
                    editor_info = suggestion_obj.editor_type
                # If dict
                elif isinstance(suggestion_obj, dict):
                    editor_info = suggestion_obj.get('editor_type', 'Bilinmeyen Editör')
            
            base_tag = "changed_text"
            if "Grammar" in editor_info:
                base_tag = "grammar_change"
            elif "Style" in editor_info:
                base_tag = "style_change"
            elif "Content" in editor_info:
                base_tag = "content_change"
            
            # Find and highlight text in content
            self._highlight_text_in_content(content_start_index, suggested_text, tag_name,
                                           original_text, explanation, editor_info, base_tag=base_tag)

    def _apply_saved_highlighting(self, chapter, content_start_index):
        """Apply saved highlighting information with dynamic, severity-based colors."""
        if not chapter:
            return
            
        # Tooltip system
        if not hasattr(self.app, 'tooltip_label'):
            self.app.tooltip_label = None
        
        if hasattr(chapter, 'highlighting_info') and chapter.highlighting_info:
            for highlight_id, highlight_info in chapter.highlighting_info.items():
                suggested_text = highlight_info.get('text', '')
                if not suggested_text:
                    continue

                original_text = highlight_info.get('original_text', '')
                explanation = highlight_info.get('explanation', 'Açıklama mevcut değil')
                editor_type = highlight_info.get('editor_type', 'Bilinmeyen Editör')
                severity = highlight_info.get('severity', 'medium')

                # Create a unique tag name and configure its style
                tag_name = f"highlight_{editor_type.replace(' ', '_')}_{severity}_{highlight_id}"
                bg_color, fg_color = self._get_highlight_colors(editor_type, severity)
                self.app.chapter_content_text.tag_configure(tag_name, background=bg_color, foreground=fg_color)
                
                # Highlight text using the newly created dynamic tag
                self._highlight_text_in_content(content_start_index, suggested_text, tag_name,
                                               original_text, explanation, editor_type)
            
            print(f"{len(chapter.highlighting_info)} adet kaydedilmiş vurgu geri yüklendi")

    def _get_highlight_colors(self, editor_type, severity):
        """Determine highlight colors based on editor type and severity."""
        # Color Palette
        colors = {
            "Dil Bilgisi Editörü": {"low": "#E8F5E9", "medium": "#C8E6C9", "high": "#A5D6A7"},
            "Üslup Editörü":       {"low": "#FFF3E0", "medium": "#FFE0B2", "high": "#FFCC80"},
            "İçerik Editörü":      {"low": "#FCE4EC", "medium": "#F8BBD0", "high": "#F48FB1"},
            "Kullanıcı Notu":      {"note": "#FFFFE0"},  # Açık sarı
            "default":             {"low": "#F5F5F5", "medium": "#E0E0E0", "high": "#BDBDBD"}
        }
        
        editor_colors = colors.get(editor_type, colors["default"])
        
        # Get the background color. If the severity is not found in the specific editor's colors,
        # try to get it from the default colors. If it's still not found, default to the medium default color.
        bg_color = editor_colors.get(severity)
        if bg_color is None:
            bg_color = colors["default"].get(severity, colors["default"]["medium"])
        
        # For simplicity, we'll use a dark foreground for all. This could be dynamic too.
        fg_color = "#1E1E1E" 
        
        return bg_color, fg_color

    def _highlight_text_in_content(self, content_start_index, suggested_text, tag_name,
                                   original_text, explanation, editor_info, base_tag=None):
        """Find and highlight text in content"""
        content_text = self.app.chapter_content_text.get(content_start_index, tk.END)
        start_pos = content_text.find(suggested_text)
        
        if start_pos != -1:
            # Calculate indices
            start_line, start_col = self._index_to_line_col(content_start_index)
            text_before_match = content_text[:start_pos]
            lines_before = text_before_match.count('\n')
            last_line_chars = len(text_before_match.split('\n')[-1])
            
            match_start_line = start_line + lines_before
            match_start_col = last_line_chars if lines_before > 0 else start_col + last_line_chars
            
            # End position
            match_text_lines = suggested_text.split('\n')
            if len(match_text_lines) == 1:
                match_end_line = match_start_line
                match_end_col = match_start_col + len(suggested_text)
            else:
                match_end_line = match_start_line + len(match_text_lines) - 1
                match_end_col = len(match_text_lines[-1])
            
            start_index = f"{match_start_line}.{match_start_col}"
            end_index = f"{match_end_line}.{match_end_col}"
            
            # Apply the dynamic tag for tooltip binding and a base tag for color
            self.app.chapter_content_text.tag_add(tag_name, start_index, end_index)
            if base_tag:
                self.app.chapter_content_text.tag_add(base_tag, start_index, end_index)
            
            # Bind tooltip events
            self._bind_tooltip_events(tag_name, original_text, suggested_text, explanation, editor_info)
            
            print(f"Değişiklik vurgulandı: '{suggested_text[:30]}...' pozisyon {start_index}-{end_index} with tag {tag_name}")
        else:
            print(f"Değişiklik metni bulunamadı: '{suggested_text[:50]}...'")

    def _index_to_line_col(self, index_str):
        """Convert string index to line.col format"""
        parts = index_str.split('.')
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0

    def _bind_tooltip_events(self, tag_name, original_text, suggested_text, explanation, editor_info):
        """Bind tooltip events to tag"""
        def on_enter(event):
            self._show_tooltip(event, original_text, suggested_text, explanation, editor_info)
        
        def on_leave(event):
            self._hide_tooltip()
        
        # Bind mouse events
        self.app.chapter_content_text.tag_bind(tag_name, "<Enter>", on_enter)
        self.app.chapter_content_text.tag_bind(tag_name, "<Leave>", on_leave)
        self.app.chapter_content_text.tag_bind(tag_name, "<Motion>", on_enter)  # Update when mouse moves

    def _show_tooltip(self, event, original_text, suggested_text, explanation, editor_info):
        """Show tooltip"""
        if self.app.tooltip_label:
            self.app.tooltip_label.destroy()
        
        # Create tooltip window
        self.app.tooltip_label = tk.Toplevel(self.root)
        self.app.tooltip_label.wm_overrideredirect(True)  # Hide title bar
        self.app.tooltip_label.configure(bg="#ffffe0", relief="solid", borderwidth=1)
        
        # Prepare content based on editor type
        if editor_info == "Kullanıcı Notu":
            tooltip_content = f"📌 Kullanıcı Notu\n\n💬 {explanation}"
        else:
            tooltip_content = f"📝 {editor_info}\n\n"
            if original_text:
                tooltip_content += f"🔴 Orijinal:\n{original_text}\n\n"
            tooltip_content += f"🟢 Önerilen:\n{suggested_text}\n\n"
            tooltip_content += f"💬 Açıklama:\n{explanation}"

        label = tk.Label(self.app.tooltip_label, text=tooltip_content, 
                        background="#ffffe0", foreground="black", 
                        font=('Arial', 9), wraplength=400, justify=tk.LEFT,
                        padx=10, pady=8)
        label.pack()
        
        # Set position
        x = event.x_root + 10
        y = event.y_root + 10
        
        # Check screen boundaries
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        self.app.tooltip_label.update_idletasks()  # Calculate dimensions
        tooltip_width = self.app.tooltip_label.winfo_reqwidth()
        tooltip_height = self.app.tooltip_label.winfo_reqheight()
        
        # Adjust position if tooltip goes off screen
        if x + tooltip_width > screen_width:
            x = screen_width - tooltip_width - 10
        if y + tooltip_height > screen_height:
            y = event.y_root - tooltip_height - 10
        
        self.app.tooltip_label.geometry(f"+{x}+{y}")

    def _hide_tooltip(self):
        """Hide tooltip"""
        if self.app.tooltip_label:
            self.app.tooltip_label.destroy()
            self.app.tooltip_label = None

    def start_selection_analysis_wrapper(self):
        """Wrapper to start grammar analysis on the selected text."""
        try:
            selected_text = self.app.chapter_content_text.get("sel.first", "sel.last")
            if not selected_text.strip():
                messagebox.showinfo("Bilgi", "Lütfen analiz edilecek bir metin seçin.")
                return

            current_chapter = self.app.get_current_chapter()
            if not current_chapter:
                messagebox.showwarning("Uyarı", "Lütfen analiz edilecek bir bölüm seçin.")
                return
            
            # Start analysis on the selected text
            if hasattr(self.app, 'analysis_manager'):
                self.app.analysis_manager.start_analysis_on_selection(current_chapter, selected_text)
            else:
                messagebox.showerror("Hata", "Analiz yöneticisi bulunamadı.")

        except tk.TclError:
            messagebox.showinfo("Bilgi", "Analiz için bir metin seçilmedi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Seçim analizi sırasında bir hata oluştu: {e}")

    def start_analysis_wrapper(self):
        """Wrapper to read settings and pass the correct context to the analysis function."""
        # Determine the upcoming analysis type from the current phase
        phase_to_type_map = {
            "none": "grammar_check",
            "grammar": "style_analysis",
            "style": "content_review"
        }
        current_phase = self.app.current_analysis_phase
        current_analysis_type = phase_to_type_map.get(current_phase)

        # If the analysis is completed or in an unknown state, let the main function handle it without special context.
        if not current_analysis_type:
            self.app.start_analysis()
            return
        
        novel_context_to_pass = None
        full_novel_content_to_pass = None

        if current_analysis_type in ["style_analysis", "content_review"]:
            context_source_setting = f"{current_analysis_type}_context_source"
            context_source = self.app.settings_manager.get_setting(context_source_setting, "full_text")
            
            if context_source == "novel_context":
                novel_context_to_pass = self.app.editorial_process.novel_context
                # The check for existing novel_context is removed. 
                # The analysis_manager will handle its creation if it's missing.
            else: # full_text
                # The analysis_manager has the method to generate this.
                if self.app.analysis_manager:
                    full_novel_content_to_pass = self.app.analysis_manager.generate_full_novel_content()
        
        elif current_analysis_type == "grammar_check":
            context_source_setting = "grammar_check_context_source"
            context_source = self.app.settings_manager.get_setting(context_source_setting, "novel_context")
            
            if context_source == "novel_context":
                novel_context_to_pass = self.app.editorial_process.novel_context
                # The check for existing novel_context is removed. 
                # The analysis_manager will handle its creation if it's missing.
            else: # full_text
                if self.app.analysis_manager:
                    full_novel_content_to_pass = self.app.analysis_manager.generate_full_novel_content()

        # Call the main analysis function with the determined context.
        self.app.start_analysis(novel_context=novel_context_to_pass, full_novel_content=full_novel_content_to_pass)
