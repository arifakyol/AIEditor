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

class FileOperationsManager:
    def __init__(self, app):
        self.app = app
        self.file_manager = app.file_manager
        self.editorial_process = app.editorial_process
        self.settings_manager = app.settings_manager

    def load_novel(self):
        # Check for unsaved changes before loading a new novel
        if self.app.has_unsaved_changes:
            response = messagebox.askyesnocancel(
                "Kaydedilmemiş Değişiklikler",
                "Mevcut projenizde kaydedilmemiş değişiklikler var. Yeni bir roman yüklemeden önce kaydetmek ister misiniz?",
                icon='warning'
            )
            if response is True:  # Yes, save
                self.app.save_project()
            elif response is None:  # Cancel
                return

        file_path = filedialog.askopenfilename(
            title="Roman Dosyasını Seçin",
            filetypes=[("Metin dosyaları", "*.txt *.docx"), ("Word dosyaları", "*.docx"), ("Tüm dosyalar", "*.*")]
        )
        
        if file_path:
            # Reset the application state for the new novel
            self.app.reset_project_state()
            self.file_manager.load_novel(file_path, self.app.chapter_split_callback)

    def export_as_txt(self):
        """Romanı TXT dosyası olarak dışa aktar"""
        if not self.file_manager.chapters:
            messagebox.showinfo("Bilgi", "Dışa aktarılacak bölüm yok.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="TXT olarak Dışa Aktar",
            defaultextension=".txt",
            filetypes=[("Metin dosyaları", "*.txt"), ("Tüm dosyalar", "*.*")]
        )
        
        if file_path:
            exported_path = self.file_manager.export_novel(file_path)
            if exported_path:
                messagebox.showinfo("Başarılı", f"Roman başarıyla dışa aktarıldı:\n{exported_path}")
            else:
                messagebox.showerror("Hata", "Dışa aktarma sırasında bir hata oluştu.")

    def export_as_docx(self):
        """Romanı DOCX dosyası olarak dışa aktar"""
        if not self.file_manager.chapters:
            messagebox.showinfo("Bilgi", "Dışa aktarılacak bölüm yok.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Word olarak Dışa Aktar",
            defaultextension=".docx",
            filetypes=[("Word dosyaları", "*.docx"), ("Tüm dosyalar", "*.*")]
        )
        
        if file_path:
            # Dosyanın .docx uzantısına sahip olduğundan emin ol
            if not file_path.lower().endswith('.docx'):
                file_path += '.docx'
                
            exported_path = self.file_manager.export_novel(file_path)
            if exported_path:
                messagebox.showinfo("Başarılı", f"Roman başarıyla dışa aktarıldı:\n{exported_path}")
            else:
                messagebox.showerror("Hata", "Dışa aktarma sırasında bir hata oluştu.")

    def save_project(self, auto_save=False, new_project_name=None, save_reason='manual'):
        """Save project - Create automatically if no project exists"""
        # If no project file exists yet, create one automatically
        last_project = self.settings_manager.get_setting('last_project')
        
        if not last_project:
            # Create automatic project name
            import datetime
            project_name = new_project_name if new_project_name else f"Novel_Project_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            print(f"Henüz kaydedilmiş proje yok. Otomatik proje oluşturuluyor: {project_name}")
            
            # Yeni proje oluştur
            project_file = self.settings_manager.create_project(project_name)
            
            if not project_file:
                messagebox.showerror("Hata", "Proje oluşturulamadı. Lütfen klasör izinlerini kontrol edin.")
                return
            
            # Son proje ayarını güncelle
            self.settings_manager.set_setting('last_project', project_file)
            print(f"Yeni proje oluşturuldu: {project_file}")
        
        # Now save the project
        success = self.settings_manager.save_project_state(
            self.file_manager.get_state(),
            self.editorial_process.get_state(),
            self.app.project_panel.get_state(),
            save_reason=save_reason
        )
        
        if success:
            project_path = self.settings_manager.get_setting('last_project')
            self.app.mark_as_saved()  # Mark project as saved
            
            # Also export the edited text as .txt and .docx files
            try:
                project_dir = os.path.dirname(project_path)
                novel_title = getattr(self.file_manager, 'novel_title', 'edited_novel')
                
                # Export as .txt
                txt_export_path = os.path.join(project_dir, f"{novel_title}_edited.txt")
                txt_exported = self.file_manager.export_novel(txt_export_path)
                
                # Export as .docx
                docx_export_path = os.path.join(project_dir, f"{novel_title}_edited.docx")
                docx_exported = self.file_manager.export_novel(docx_export_path)
                
                exported_files_info = []
                if txt_exported:
                    exported_files_info.append(f"Metin Dosyası:\n{txt_exported}")
                    print(f"DÜZENLENEN METİN (TXT) DIŞA AKTARILDI: {txt_exported}")
                if docx_exported:
                    exported_files_info.append(f"Word Dosyası:\n{docx_exported}")
                    print(f"DÜZENLENEN METİN (DOCX) DIŞA AKTARILDI: {docx_exported}")

                if exported_files_info:
                    messagebox.showinfo("Başarılı", f"Proje başarıyla kaydedildi!\n\nProje Dosyası:\n{project_path}\n\n" + "\n\n".join(exported_files_info))
                else:
                    messagebox.showinfo("Başarılı", f"Proje başarıyla kaydedildi!\n\nDosya konumu:\n{project_path}\n\n(Düzenlenen metinler dışa aktarılamadı)")
                
                print(f"PROJE KAYDEDİLDİ: {project_path}")

            except Exception as export_error:
                messagebox.showinfo("Başarılı", f"Proje başarıyla kaydedildi!\n\nDosya konumu:\n{project_path}\n\n(Dışa aktarma hatası: {str(export_error)})")
                print(f"PROJE KAYDEDİLDİ: {project_path}")
                print(f"DIŞA AKTARMA HATASI: {export_error}")
        else:
            messagebox.showerror("Hata", "Proje kaydedilemedi. Detaylar için konsolu kontrol edin.")
            print("PROJE KAYDETME BAŞARISIZ OLDU")

    def load_project(self):
        """Mevcut projeyi aç"""
        # Mevcut projeleri listele
        projects = self.settings_manager.get_project_list()
        
        if not projects:
            messagebox.showinfo("Bilgi", "Kaydedilmiş proje bulunamadı.\n\nÖnce bir roman yükleyin ve bir proje oluşturmak için 'Projeyi Kaydet'i kullanın.")
            return
        
        # Proje seçim penceresi
        project_window = tk.Toplevel(self.app.root)
        project_window.title("Proje Seç")
        project_window.geometry("700x500")
        project_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(project_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(main_frame, text="Açılacak projeyi seçin:", font=('Arial', 12, 'bold')).pack(pady=(0, 10))
        
        # Project list
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview for project list
        columns = ('name', 'created', 'modified')
        project_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
        # Sütun başlıkları
        project_tree.heading('name', text='Proje Adı')
        project_tree.heading('created', text='Oluşturulma Tarihi')
        project_tree.heading('modified', text='Son Değiştirilme')
        
        # Column widths
        project_tree.column('name', width=250)
        project_tree.column('created', width=150)
        project_tree.column('modified', width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=project_tree.yview)
        project_tree.configure(yscrollcommand=scrollbar.set)
        
        project_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add projects to list
        for project in projects:
            created_date = project['created_date'][:16].replace('T', ' ') if project['created_date'] else 'Unknown'
            modified_date = project['last_modified'][:16].replace('T', ' ') if project['last_modified'] else 'Unknown'
            
            project_tree.insert('', tk.END, 
                               values=(project['name'], created_date, modified_date),
                               tags=(project['file_path'],))
        
        # Store selected project path
        selected_project_path: list = [None]
        
        def on_select(event):
            selection = project_tree.selection()
            if selection:
                item = project_tree.item(selection[0])
                selected_project_path[0] = item['tags'][0] if item['tags'] else None
        
        project_tree.bind('<<TreeviewSelect>>', on_select)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def open_selected_project():
            if not selected_project_path[0]:
                messagebox.showwarning("Uyarı", "Lütfen bir proje seçin.")
                return
                
            try:
                # Projeyi aç
                success = self._load_project_file(selected_project_path[0])
                if success:
                    project_window.destroy()
                    messagebox.showinfo("Başarılı", "Proje başarıyla açıldı!")
                else:
                    messagebox.showerror("Hata", "Proje açılırken bir hata oluştu.")
            except Exception as e:
                messagebox.showerror("Hata", f"Proje açma hatası:\n{str(e)}")
        
        def delete_selected_project():
            """Seçili projeyi sil"""
            if not selected_project_path[0]:
                messagebox.showwarning("Uyarı", "Lütfen silinecek bir projeyi seçin.")
                return

            # Onay iste
            project_name = ""
            selection = project_tree.selection()
            if selection:
                item = project_tree.item(selection[0])
                project_name = item['values'][0]

            confirm = messagebox.askyesno(
                "Projeyi Sil",
                f"'{project_name}' projesini kalıcı olarak silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!"
            )

            if not confirm:
                return

            try:
                # Proje dosyasının bulunduğu klasörü sil
                project_folder = os.path.dirname(selected_project_path[0])
                import shutil
                shutil.rmtree(project_folder)

                # Listeden kaldır
                project_tree.delete(selection[0])
                selected_project_path[0] = None

                messagebox.showinfo("Başarılı", f"'{project_name}' projesi başarıyla silindi.")
                
                # Eğer silinen proje son açılan proje ise, ayarı temizle
                if self.settings_manager.get_setting('last_project') == selected_project_path[0]:
                    self.settings_manager.set_setting('last_project', None)

            except Exception as e:
                messagebox.showerror("Hata", f"Proje silinirken bir hata oluştu:\n{str(e)}")

        ttk.Button(button_frame, text="Aç", command=open_selected_project).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="İptal", command=project_window.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Sil", command=delete_selected_project).pack(side=tk.LEFT, padx=(0, 5))
        
        # Double-click to open
        def on_double_click(event):
            if selected_project_path[0]:
                open_selected_project()
                
        project_tree.bind('<Double-1>', on_double_click)

    def load_project_history(self):
        """Proje geçmişinden bir sürümü yükle"""
        last_project = self.settings_manager.get_setting('last_project')
        if not last_project:
            messagebox.showinfo("Bilgi", "Aktif bir proje bulunamadı.")
            return

        project_dir = os.path.dirname(last_project)
        history_dir = os.path.join(project_dir, 'history')

        if not os.path.exists(history_dir) or not os.listdir(history_dir):
            messagebox.showinfo("Bilgi", "Bu proje için kaydedilmiş bir geçmiş bulunamadı.")
            return

        def get_timestamp_from_filename(filename):
            try:
                # Dosya adını '_' karakterine göre ayır
                parts = filename.replace('project_', '').replace('.json', '').split('_')
                # Zaman damgası her zaman son iki parçadır (YYYYMMDD ve HHMMSS)
                if len(parts) >= 2:
                    return f"{parts[-2]}_{parts[-1]}"
                return parts[0] # Eski format için
            except IndexError:
                return filename # Hata durumunda sıralamayı bozma

        history_files = sorted(
            [f for f in os.listdir(history_dir) if f.startswith('project_') and f.endswith('.json')],
            key=get_timestamp_from_filename,
            reverse=True
        )

        if not history_files:
            messagebox.showinfo("Bilgi", "Bu proje için kaydedilmiş bir geçmiş bulunamadı.")
            return

        history_window = tk.Toplevel(self.app.root)
        history_window.title("Proje Geçmişi")
        history_window.geometry("700x500")
        history_window.grab_set()

        main_frame = ttk.Frame(history_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(main_frame, text="Yüklenecek bir kayıt noktası seçin:", font=('Arial', 12, 'bold')).pack(pady=(0, 10))

        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ('timestamp', 'source', 'size')
        history_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        history_tree.heading('timestamp', text='Kayıt Zamanı')
        history_tree.heading('source', text='Kaynak')
        history_tree.heading('size', text='Boyut (KB)')
        history_tree.column('timestamp', width=250)
        history_tree.column('source', width=150)
        history_tree.column('size', width=100, anchor='e')

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=history_tree.yview)
        history_tree.configure(yscrollcommand=scrollbar.set)
        history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        reason_map = {
            'manual': 'Kullanıcı Kaydı',
            'auto': 'Otomatik Kayıt',
            'restore_backup': 'Geri Yükleme Öncesi',
            'manual_test': 'Test Kaydı'
        }

        for filename in history_files:
            file_path = os.path.join(history_dir, filename)
            try:
                parts = filename.replace('project_', '').replace('.json', '').split('_')
                
                # Zaman damgası her zaman son iki parçadır
                if len(parts) >= 3: # project_{reason...}_{date}_{time}
                    timestamp_str = f"{parts[-2]}_{parts[-1]}"
                    reason_key = "_".join(parts[:-2])
                    source_text = reason_map.get(reason_key, reason_key.replace('_', ' ').capitalize())
                else: # Eski formatla uyumluluk: project_{date}_{time} veya project_{timestamp}
                    timestamp_str = "_".join(parts)
                    source_text = "Belirtilmemiş"

                dt_obj = datetime.datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                formatted_time = dt_obj.strftime('%d %B %Y, %H:%M:%S')
                file_size = round(os.path.getsize(file_path) / 1024, 2)
                history_tree.insert('', tk.END, values=(formatted_time, source_text, f"{file_size} KB"), tags=(file_path,))
            except (ValueError, FileNotFoundError, IndexError):
                continue

        selected_history_path = [None]

        def on_select(event):
            selection = history_tree.selection()
            if selection:
                item = history_tree.item(selection[0])
                selected_history_path[0] = item['tags'][0] if item['tags'] else None

        history_tree.bind('<<TreeviewSelect>>', on_select)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        def restore_selected_history():
            if not selected_history_path[0]:
                messagebox.showwarning("Uyarı", "Lütfen bir kayıt noktası seçin.")
                return

            confirm = messagebox.askyesno(
                "Geçmişi Geri Yükle",
                "Seçili kayıt noktasını geri yüklemek istediğinizden emin misiniz?\n\n"
                "Mevcut çalışmanız bu kayıt noktasındaki haliyle değiştirilecektir. "
                "Bu işlem öncesi mevcut durumun bir yedeği otomatik olarak alınacaktır."
            )

            if not confirm:
                return

            try:
                # First, save the current state as a new history point before overwriting
                self.app.save_project(save_reason='restore_backup')

                # Now, restore the selected history file
                import shutil
                shutil.copy2(selected_history_path[0], last_project)

                # Reload the project state
                if self._load_project_file(last_project):
                    history_window.destroy()
                    messagebox.showinfo("Başarılı", "Proje geçmişi başarıyla geri yüklendi!")
                else:
                    messagebox.showerror("Hata", "Proje durumu geri yüklendikten sonra yeniden yüklenemedi.")
            except Exception as e:
                messagebox.showerror("Hata", f"Geçmiş geri yüklenirken bir hata oluştu:\n{str(e)}")

        def delete_selected_history():
            """Seçili geçmiş dosyasını sil"""
            if not selected_history_path[0]:
                messagebox.showwarning("Uyarı", "Lütfen silinecek bir kayıt noktası seçin.")
                return

            selection = history_tree.selection()
            if not selection:
                return
            
            item = history_tree.item(selection[0])
            timestamp = item['values'][0]

            confirm = messagebox.askyesno(
                "Kaydı Sil",
                f"'{timestamp}' zamanına ait kayıt noktasını kalıcı olarak silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!"
            )

            if not confirm:
                return

            try:
                os.remove(selected_history_path[0])
                history_tree.delete(selection[0])
                selected_history_path[0] = None
                messagebox.showinfo("Başarılı", "Kayıt noktası başarıyla silindi.")
            except Exception as e:
                messagebox.showerror("Hata", f"Kayıt silinirken bir hata oluştu:\n{str(e)}")

        ttk.Button(button_frame, text="Seçili Kaydı Yükle", command=restore_selected_history).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="İptal", command=history_window.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Sil", command=delete_selected_history).pack(side=tk.LEFT, padx=(0, 5))

        def on_double_click(event):
            if selected_history_path[0]:
                restore_selected_history()

        history_tree.bind('<Double-1>', on_double_click)


    def _load_project_file(self, project_file: str = "") -> bool:
        """Proje dosyasını yükle"""
        try:
            # Projeyi yükle
            state = self.settings_manager.load_project_state(project_file)
            if not state:
                messagebox.showerror("Hata", "Proje dosyası yüklenemedi.")
                return False
            
            # Load FileManager state
            if 'file_manager_state' in state:
                self.file_manager.load_state(state['file_manager_state'])
            
            # Load EditorialProcess state
            if 'editorial_process_state' in state:
                self.editorial_process.load_state(state['editorial_process_state'])
            
            # Update last project setting
            self.settings_manager.set_setting('last_project', project_file)
            
            # Update UI
            if hasattr(self.app, 'project_panel') and self.app.project_panel:
                # 1. Önce bölüm listesini panele yükle, böylece panel veriyle dolar.
                self.app.project_panel.update_chapters(self.file_manager.chapters)
                
                # 2. Şimdi panelin durumunu (örn. seçili bölüm indeksi) yükle.
                #    Bu aşamada panelin `chapters` listesi dolu olduğu için `load_state` doğru çalışacaktır.
                if 'project_panel' in state and state['project_panel']:
                    self.app.project_panel.load_state(state['project_panel'])
                
                # 3. `load_state` zaten durumu güncelledi, ancak seçimi garantilemek için
                #    mevcut indeksi kullanarak bölümü yeniden seçtirelim.
                if self.file_manager.chapters:
                    current_index = self.app.project_panel.current_chapter_index
                    self.app.project_panel.select_chapter(current_index)

            print(f"Proje başarıyla yüklendi: {project_file}")
            return True
            
        except Exception as e:
            print(f"Proje yükleme hatası: {e}")
            messagebox.showerror("Hata", f"Proje yüklenirken hata oluştu:\n{str(e)}")
            return False
