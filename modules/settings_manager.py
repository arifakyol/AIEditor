import json
import os
import sys
from typing import Dict, Any, Optional
import datetime

def get_base_path():
    """Uygulamanın ana dizinini alır (.exe veya .py için çalışır)."""
    if getattr(sys, 'frozen', False):
        # PyInstaller tarafından oluşturulan .exe dosyası için
        return os.path.dirname(sys.executable)
    else:
        # Normal .py scripti için
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class SettingsManager:
    def __init__(self):
        self.base_path = get_base_path()
        self.settings_file = os.path.join(self.base_path, 'settings.json')
        
        # Load settings first
        self.settings = self.load_settings()
        
        # Get projects directory from settings, with fallback to default
        projects_dir_setting = self.get_setting('projects_directory')
        if projects_dir_setting and os.path.isdir(projects_dir_setting):
            self.projects_dir = projects_dir_setting
        else:
            self.projects_dir = os.path.join(self.base_path, 'data', 'projects')
        
        # Create projects directory
        os.makedirs(self.projects_dir, exist_ok=True)
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings"""
        default_settings = {
            'api_key': '',
            'model': 'gemini-1.5-flash',
            'individual_models': {
                'style_analysis': 'gemini-1.5-flash',
                'grammar_check': 'gemini-1.5-flash',
                'content_review': 'gemini-1.5-flash'
            },
            'language': 'tr',
            'theme': 'default',
            'auto_save': True,
            'auto_save_interval': 300,  # 5 minutes
            'recent_projects': [],
            'window_geometry': '1200x800',
            'last_project': None,
            'projects_directory': None,  # New setting for custom projects directory
            'ui_settings': {
                'show_suggestions_panel': True,
                'show_chapter_list': True,
                'font_size': 12,
                'font_family': 'Arial'
            },
            'workflow_settings': {
                'auto_grammar_check': True,
                'auto_style_analysis': True,
                'auto_content_review': False,
                'require_approval': True,
                'backup_on_apply': True
            },
            'prompts': {}
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as file:
                    loaded_settings = json.load(file)
                    # Update default settings
                    default_settings.update(loaded_settings)
                    
                    # Clean up invalid paths in recent_projects
                    if 'recent_projects' in default_settings:
                        valid_projects = []
                        for project in default_settings['recent_projects']:
                            if 'path' in project and os.path.exists(project['path']):
                                valid_projects.append(project)
                        default_settings['recent_projects'] = valid_projects
                        
                    # Validate last_project path
                    if 'last_project' in default_settings and default_settings['last_project']:
                        if not os.path.exists(default_settings['last_project']):
                            default_settings['last_project'] = None
            except Exception as e:
                print(f"Settings loading error: {e}")
        
        return default_settings
    
    def save_settings(self):
        """Save settings"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as file:
                json.dump(self.settings, file, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Settings saving error: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value"""
        return self.settings.get(key, default)
    
    def set_setting(self, key: str, value: Any):
        """Set setting value"""
        self.settings[key] = value
        self.save_settings()
    
    def get_nested_setting(self, path: str, default: Any = None) -> Any:
        """Get nested setting (e.g. 'ui_settings.font_size')"""
        keys = path.split('.')
        current = self.settings
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def set_nested_setting(self, path: str, value: Any):
        """Set nested setting"""
        keys = path.split('.')
        current = self.settings
        
        # Navigate to the parent of the last key
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Set the last key
        current[keys[-1]] = value
        self.save_settings()
    
    def add_recent_project(self, project_path: str, project_name: str):
        """Add project to recent projects list"""
        recent_projects = self.get_setting('recent_projects', [])
        
        # Remove existing project from list
        recent_projects = [p for p in recent_projects if p['path'] != project_path]
        
        # Add new project to the beginning
        recent_projects.insert(0, {
            'path': project_path,
            'name': project_name,
            'last_opened': datetime.datetime.now().isoformat()
        })
        
        # Keep maximum 10 projects
        recent_projects = recent_projects[:10]
        
        self.set_setting('recent_projects', recent_projects)
    
    def get_recent_projects(self) -> list:
        """Get recent projects"""
        return self.get_setting('recent_projects', [])
    
    def set_projects_directory(self, directory_path: str):
        """Set custom projects directory"""
        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            self.set_setting('projects_directory', directory_path)
            self.projects_dir = directory_path
            return True
        return False
    
    def create_project(self, project_name: str) -> Optional[str]:
        """Create new project"""
        project_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        project_folder = os.path.join(self.projects_dir, f"{project_id}_{project_name}")
        
        os.makedirs(project_folder, exist_ok=True)
        
        project_file = os.path.join(project_folder, 'project.json')
        project_data = {
            'id': project_id,
            'name': project_name,
            'created_date': datetime.datetime.now().isoformat(),
            'last_modified': datetime.datetime.now().isoformat(),
            'file_manager_state': {},
            'editorial_process_state': {},
            'current_chapter': 1,
            'version': '1.0'
        }
        
        try:
            with open(project_file, 'w', encoding='utf-8') as file:
                json.dump(project_data, file, ensure_ascii=False, indent=2)
            
            self.add_recent_project(project_file, project_name)
            return project_file
        except Exception as e:
            print(f"Project creation error: {e}")
            return None
    
    def save_project_state(self, file_manager_state: Dict, editorial_process_state: Dict, 
                          ui_state: Optional[Dict] = None, save_reason: str = 'manual'):
        """Save project state - Enhanced error handling"""
        last_project = self.get_setting('last_project')
        
        print(f"PROJECT SAVING INITIATED...")
        print(f"Last project setting: {last_project}")
        
        # If no last project, create one automatically
        if not last_project:
            print("No last project setting found! Creating automatic project...")
            auto_project_name = f"Auto_Save_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_file = self.create_project(auto_project_name)
            
            if not project_file:
                print("ERROR: Could not create automatic project!")
                return False
                
            # Update last project setting
            self.set_setting('last_project', project_file)
            last_project = project_file
            print(f"Automatic project created: {project_file}")
        
        # Check file existence
        if not os.path.exists(last_project):
            print(f"ERROR: Project file not found: {last_project}")
            print("Project file may have been deleted or moved.")
            # Try to create a new project
            auto_project_name = f"Recovery_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_file = self.create_project(auto_project_name)
            
            if not project_file:
                print("ERROR: Could not create recovery project!")
                return False
                
            # Update last project setting
            self.set_setting('last_project', project_file)
            last_project = project_file
            print(f"Recovery project created: {project_file}")
        
        try:
            print(f"Reading project file: {last_project}")
            
            # Load existing project file
            with open(last_project, 'r', encoding='utf-8') as file:
                project_data = json.load(file)
            
            print(f"Loaded existing project: {project_data.get('name', 'Unknown')}")
            
            # Update state
            project_data['file_manager_state'] = file_manager_state
            project_data['editorial_process_state'] = editorial_process_state
            project_data['last_modified'] = datetime.datetime.now().isoformat()
            
            if ui_state:
                project_data['ui_state'] = ui_state
            
            print(f"Data updated. Saving to file...")
            
            # Check write permissions
            project_dir = os.path.dirname(last_project)
            if not os.access(project_dir, os.W_OK):
                print(f"ERROR: No write permission to folder: {project_dir}")
                return False
            
            # Create timestamped backup in a 'history' subfolder
            project_dir = os.path.dirname(last_project)
            history_dir = os.path.join(project_dir, 'history')
            os.makedirs(history_dir, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(history_dir, f"project_{save_reason}_{timestamp}.json")
            
            try:
                import shutil
                if os.path.exists(last_project):
                    shutil.copy2(last_project, backup_file)
                    print(f"Backup created: {backup_file}")
            except Exception as backup_error:
                print(f"Could not create backup: {backup_error}")
            
            # Save
            with open(last_project, 'w', encoding='utf-8') as file:
                json.dump(project_data, file, ensure_ascii=False, indent=2)
            
            # Check file size
            file_size = os.path.getsize(last_project)
            print(f"✅ PROJECT SUCCESSFULLY SAVED!")
            print(f"File: {last_project}")
            print(f"Size: {file_size} bytes")
            print(f"Last modified: {project_data['last_modified']}")
            
            return True
            
        except PermissionError as e:
            print(f"ERROR: File write permission issue: {e}")
            print("Please run the application as administrator.")
            return False
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON format: {e}")
            return False
        except Exception as e:
            print(f"PROJECT SAVING ERROR: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            return False
    
    def load_project_state(self, project_file: str) -> Optional[Dict]:
        """Load project state"""
        try:
            with open(project_file, 'r', encoding='utf-8') as file:
                project_data = json.load(file)
            
            self.set_setting('last_project', project_file)
            
            # Update recent projects list
            project_name = project_data.get('name', 'Unknown Project')
            self.add_recent_project(project_file, project_name)
            
            return project_data
        except Exception as e:
            print(f"Project loading error: {e}")
            return None
    
    def get_project_list(self) -> list:
        """List all projects"""
        projects = []
        
        if not os.path.exists(self.projects_dir):
            return projects
        
        for folder_name in os.listdir(self.projects_dir):
            folder_path = os.path.join(self.projects_dir, folder_name)
            project_file = os.path.join(folder_path, 'project.json')
            
            if os.path.isfile(project_file):
                try:
                    with open(project_file, 'r', encoding='utf-8') as file:
                        project_data = json.load(file)
                    
                    projects.append({
                        'file_path': project_file,
                        'name': project_data.get('name', 'Unknown'),
                        'created_date': project_data.get('created_date', ''),
                        'last_modified': project_data.get('last_modified', ''),
                        'version': project_data.get('version', '1.0')
                    })
                except Exception as e:
                    print(f"Project reading error {project_file}: {e}")
        
        # Sort by last modified date
        projects.sort(key=lambda x: x['last_modified'], reverse=True)
        return projects
    
    def export_settings(self, file_path: str) -> bool:
        """Export settings"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(self.settings, file, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Settings export error: {e}")
            return False
    
    def import_settings(self, file_path: str) -> bool:
        """Import settings"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                imported_settings = json.load(file)
            
            # Update current settings (don't replace completely)
            self.settings.update(imported_settings)
            self.save_settings()
            return True
        except Exception as e:
            print(f"Settings import error: {e}")
            return False
    
    def reset_settings(self):
        """Reset settings to default"""
        # Keep certain settings
        keep_settings = {
            'recent_projects': self.get_setting('recent_projects', []),
            'last_project': self.get_setting('last_project'),
            'projects_directory': self.get_setting('projects_directory')
        }
        
        self.settings = self.load_settings()
        self.settings.update(keep_settings)
        self.save_settings()
    
    def get_backup_settings(self) -> Dict:
        """Get backup settings"""
        return {
            'auto_backup': self.get_nested_setting('workflow_settings.backup_on_apply', True),
            'backup_interval': self.get_setting('auto_save_interval', 300),
            'max_backups': self.get_setting('max_backups', 10)
        }
