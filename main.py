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

# Yeni oluşturulan yöneticiler
from app_core import EditorialApp
from ui_manager import UIManager
from ai_manager import AIManager
from file_operations import FileOperationsManager
from auto_save_manager import AutoSaveManager
from analysis_manager import AnalysisManager

def main():
    app = EditorialApp()
    
    # Managers setup
    ui_manager = UIManager(app)
    ai_manager = AIManager(app)
    file_ops_manager = FileOperationsManager(app)
    auto_save_manager = AutoSaveManager(app)
    analysis_manager = AnalysisManager(app)
    
    # Connect managers to app
    app.ui_manager = ui_manager
    app.ai_manager = ai_manager
    app.file_ops_manager = file_ops_manager
    app.auto_save_manager = auto_save_manager
    app.analysis_manager = analysis_manager
    
    # Connect manager methods to app for UI callbacks BEFORE setting up UI
    # File operations
    app.load_novel = file_ops_manager.load_novel
    app.save_project = file_ops_manager.save_project
    app.load_project = file_ops_manager.load_project
    app.export_as_txt = file_ops_manager.export_as_txt
    app.export_as_docx = file_ops_manager.export_as_docx
    
    # AI operations
    app.open_ai_settings = ai_manager.open_ai_settings
    app.open_prompt_settings = ai_manager.open_prompt_settings
    app.show_novel_context = ai_manager.show_novel_context
    
    # Auto save operations
    app.open_auto_save_settings = auto_save_manager.open_auto_save_settings
    app.setup_auto_save = auto_save_manager.setup_auto_save
    app._auto_save_timer = auto_save_manager._auto_save_timer
    app._restart_auto_save_timer = auto_save_manager._restart_auto_save_timer
    
    # Analysis operations
    app.start_analysis = analysis_manager.start_analysis
    app.next_chapter = analysis_manager.next_chapter
    app.prev_chapter = analysis_manager.prev_chapter
    app.apply_all_suggestions = analysis_manager.apply_all_suggestions
    app.show_suggestion_history = analysis_manager.show_suggestion_history
    app.display_suggestions = lambda suggestions=None: analysis_manager.display_suggestions(suggestions or [])
    app.handle_suggestion = lambda suggestion=None, action=None, update_display=True: analysis_manager.handle_suggestion(suggestion, action, update_display)
    app.check_project_status = analysis_manager.check_project_status
    app.open_debug_console = analysis_manager.open_debug_console
    app.chapter_split_callback = lambda content=None: analysis_manager.chapter_split_callback(content)
    app._has_pending_suggestions = analysis_manager._has_pending_suggestions
    app.on_chapter_selection_changed = analysis_manager.on_chapter_selection_changed
    
    # UI operations
    app.display_chapter_content = lambda chapter=None: ui_manager.display_chapter_content(chapter)
    app.show_analysis_status = lambda message="", color="black": ui_manager.show_analysis_status(message, color)
    app.show_progress = ui_manager.show_progress
    app.hide_progress = ui_manager.hide_progress
    
    # Special methods
    app._load_project_file = lambda project_file="": file_ops_manager._load_project_file(project_file)
    
    # Now set up the UI after connecting methods
    ui_manager.setup_ui()
    
    # Set the project panel in the auto save manager
    if hasattr(app, 'project_panel') and app.project_panel:
        auto_save_manager.set_project_panel(app.project_panel)
    
    # Initialize managers that need it
    app.load_project_state()
    app.setup_auto_save()
    
    # Uygulamayı çalıştır
    app.run()

if __name__ == "__main__":
    main()