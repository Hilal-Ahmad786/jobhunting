#!/usr/bin/env python3
"""
Job Hunter Bot - Complete Setup Script

This script automatically sets up the entire Job Hunter Bot application:
- Creates project structure
- Installs dependencies
- Configures database
- Sets up initial user profile
- Tests all components
- Creates desktop shortcuts
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
import json
import sqlite3
from typing import Dict, Any


class JobHunterSetup:
    """Complete setup automation for Job Hunter Bot"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.system = platform.system().lower()
        self.python_cmd = self._get_python_command()
        
        print("🤖 Job Hunter Bot Setup")
        print("=" * 50)
        print(f"Operating System: {platform.system()} {platform.release()}")
        print(f"Python Version: {platform.python_version()}")
        print(f"Project Path: {self.project_root}")
        print("=" * 50)
    
    def _get_python_command(self) -> str:
        """Get appropriate Python command for the system"""
        if shutil.which('python3'):
            return 'python3'
        elif shutil.which('python'):
            return 'python'
        else:
            raise RuntimeError("Python not found in PATH")
    
    def run_complete_setup(self) -> bool:
        """Run complete setup process"""
        try:
            print("🚀 Starting complete setup process...")
            
            steps = [
                ("1/8", "Checking system requirements", self.check_requirements),
                ("2/8", "Creating project structure", self.create_project_structure),
                ("3/8", "Setting up virtual environment", self.setup_virtual_environment),
                ("4/8", "Installing dependencies", self.install_dependencies),
                ("5/8", "Setting up ChromeDriver", self.setup_chromedriver),
                ("6/8", "Initializing database", self.setup_database),
                ("7/8", "Creating configuration files", self.create_config_files),
                ("8/8", "Running initial tests", self.test_installation)
            ]
            
            for step_num, description, method in steps:
                print(f"\n{step_num} {description}...")
                if not method():
                    print(f"❌ Setup failed at step: {description}")
                    return False
                print(f"✅ {description} completed")
            
            print(f"\n🎉 Setup completed successfully!")
            print(f"📋 Next steps:")
            print(f"   1. Run: {self.python_cmd} main.py")
            print(f"   2. Set up your user profile")
            print(f"   3. Configure your OpenAI API key")
            print(f"   4. Start searching for jobs!")
            
            return True
            
        except Exception as e:
            print(f"❌ Setup failed with error: {e}")
            return False
    
    def check_requirements(self) -> bool:
        """Check system requirements"""
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 9):
            print(f"❌ Python 3.9+ required, found {python_version.major}.{python_version.minor}")
            return False
        
        # Check for Chrome/Chromium
        chrome_paths = [
            "google-chrome", "chromium-browser", "chrome", "chromium",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ]
        
        chrome_found = any(shutil.which(path) or Path(path).exists() for path in chrome_paths)
        if not chrome_found:
            print("⚠️ Google Chrome not found - web scraping may not work")
            print("   Please install Chrome from: https://www.google.com/chrome/")
        
        # Check disk space (at least 2GB)
        free_space = shutil.disk_usage(self.project_root).free / (1024**3)
        if free_space < 2:
            print(f"❌ Insufficient disk space: {free_space:.1f}GB available, 2GB required")
            return False
        
        return True
    
    def create_project_structure(self) -> bool:
        """Create complete project directory structure"""
        
        directories = [
            # Data directories
            "data/logs", "data/backups", "data/exports", "data/cv_templates",
            
            # Core modules
            "core/database", "core/scrapers", "core/ai", "core/utils", "core/config",
            
            # GUI modules
            "gui/dialogs", "gui/widgets", "gui/resources/icons", "gui/resources/styles",
            
            # Documentation and tests
            "docs", "tests", "examples",
            
            # Configuration
            "config", "scripts"
        ]
        
        for directory in directories:
            (self.project_root / directory).mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py files
        init_files = [
            "core/__init__.py", "core/database/__init__.py", "core/scrapers/__init__.py",
            "core/ai/__init__.py", "core/utils/__init__.py", "core/config/__init__.py",
            "gui/__init__.py", "gui/dialogs/__init__.py", "gui/widgets/__init__.py",
            "tests/__init__.py"
        ]
        
        for init_file in init_files:
            (self.project_root / init_file).touch()
        
        return True
    
    def setup_virtual_environment(self) -> bool:
        """Create and activate virtual environment"""
        
        venv_path = self.project_root / "job_hunter_env"
        
        if venv_path.exists():
            print("Virtual environment already exists")
            return True
        
        try:
            # Create virtual environment
            subprocess.check_call([
                self.python_cmd, "-m", "venv", str(venv_path)
            ])
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to create virtual environment: {e}")
            return False
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        
        venv_python = self._get_venv_python()
        requirements_file = self.project_root / "requirements.txt"
        
        if not requirements_file.exists():
            print(f"Creating requirements.txt...")
            self._create_requirements_file()
        
        try:
            # Upgrade pip first
            subprocess.check_call([
                venv_python, "-m", "pip", "install", "--upgrade", "pip"
            ])
            
            # Install requirements
            subprocess.check_call([
                venv_python, "-m", "pip", "install", "-r", str(requirements_file)
            ])
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Dependency installation failed: {e}")
            return False
    
    def setup_chromedriver(self) -> bool:
        """Setup ChromeDriver for web scraping"""
        
        venv_python = self._get_venv_python()
        
        try:
            # Install and setup ChromeDriver
            subprocess.check_call([
                venv_python, "-c", 
                "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"
            ])
            
            return True
            
        except Exception as e:
            print(f"ChromeDriver setup failed: {e}")
            print("You may need to install Chrome browser first")
            return False
    
    def setup_database(self) -> bool:
        """Initialize SQLite database"""
        
        try:
            # Create database file
            db_path = self.project_root / "data" / "job_hunter.db"
            
            # Import database manager and initialize
            sys.path.insert(0, str(self.project_root))
            
            # Create a minimal database setup
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create basic tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    url TEXT UNIQUE,
                    source TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert initial settings
            initial_settings = [
                ('schema_version', '1'),
                ('setup_completed', 'true'),
                ('first_run', 'true')
            ]
            
            for key, value in initial_settings:
                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    (key, value)
                )
            
            conn.commit()
            conn.close()
            
            print(f"Database created: {db_path}")
            return True
            
        except Exception as e:
            print(f"Database setup failed: {e}")
            return False
    
    def create_config_files(self) -> bool:
        """Create configuration files"""
        
        try:
            # Create .env.example
            env_example = self.project_root / ".env.example"
            env_example.write_text("""
# Job Hunter Bot Environment Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
HEADLESS_SCRAPING=True
LOG_LEVEL=INFO
""".strip())
            
            # Create config.ini
            config_ini = self.project_root / "config.ini"
            config_ini.write_text("""
[Database]
path = data/job_hunter.db
backup_interval_days = 7

[Scraping]
max_concurrent_scrapers = 5
default_job_limit = 100
headless_mode = True

[AI]
model = gpt-4
temperature = 0.3
max_tokens = 2000

[GUI]
window_width = 1600
window_height = 1000
auto_refresh_minutes = 5
""".strip())
            
            # Create .gitignore
            gitignore = self.project_root / ".gitignore"
            gitignore.write_text("""
# Job Hunter Bot
.env
*.db
*.log
job_hunter_env/
__pycache__/
*.pyc
data/logs/
data/backups/
""".strip())
            
            return True
            
        except Exception as e:
            print(f"Config file creation failed: {e}")
            return False
    
    def test_installation(self) -> bool:
        """Test the installation"""
        
        venv_python = self._get_venv_python()
        
        test_script = """
import sys
sys.path.insert(0, '.')

try:
    # Test imports
    from PyQt6.QtWidgets import QApplication
    from selenium import webdriver
    from bs4 import BeautifulSoup
    import requests
    import openai
    import sqlite3
    
    print("✓ All core dependencies imported successfully")
    
    # Test database
    from core.database.database_manager import DatabaseManager
    db = DatabaseManager('data/job_hunter.db')
    db.close()
    print("✓ Database connection successful")
    
    print("✓ Installation test passed!")
    
except Exception as e:
    print(f"✗ Installation test failed: {e}")
    sys.exit(1)
"""
        
        try:
            # Write test script to temp file
            test_file = self.project_root / "test_install.py"
            test_file.write_text(test_script)
            
            # Run test
            result = subprocess.run([
                venv_python, str(test_file)
            ], capture_output=True, text=True)
            
            # Clean up test file
            test_file.unlink()
            
            if result.returncode == 0:
                print(result.stdout)
                return True
            else:
                print(f"Test failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Test execution failed: {e}")
            return False
    
    def _get_venv_python(self) -> str:
        """Get path to virtual environment Python"""
        venv_path = self.project_root / "job_hunter_env"
        
        if self.system == "windows":
            return str(venv_path / "Scripts" / "python.exe")
        else:
            return str(venv_path / "bin" / "python")
    
    def _create_requirements_file(self):
        """Create requirements.txt if it doesn't exist"""
        requirements_content = """
# Job Hunter Bot Dependencies
PyQt6>=6.6.0
selenium>=4.15.0
beautifulsoup4>=4.12.2
requests>=2.31.0
openai>=1.3.0
pandas>=2.1.0
webdriver-manager>=4.0.1
python-dateutil>=2.8.2
pillow>=10.0.0
colorlog>=6.7.0
email-validator>=2.1.0
cryptography>=41.0.0
fake-useragent>=1.4.0
plyer>=2.1.0
""".strip()
        
        requirements_file = self.project_root / "requirements.txt"
        requirements_file.write_text(requirements_content)
    
    def create_desktop_shortcuts(self) -> bool:
        """Create desktop shortcuts for easy access"""
        
        try:
            if self.system == "windows":
                self._create_windows_shortcut()
            elif self.system == "darwin":  # macOS
                self._create_macos_shortcut()
            else:  # Linux
                self._create_linux_shortcut()
            
            return True
            
        except Exception as e:
            print(f"Shortcut creation failed: {e}")
            return False
    
    def _create_windows_shortcut(self):
        """Create Windows desktop shortcut"""
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "Job Hunter Bot.lnk")
        target = str(self.project_root / "job_hunter_env" / "Scripts" / "python.exe")
        arguments = str(self.project_root / "main.py")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.Arguments = arguments
        shortcut.WorkingDirectory = str(self.project_root)
        shortcut.IconLocation = target
        shortcut.save()
    
    def _create_macos_shortcut(self):
        """Create macOS application bundle"""
        app_path = Path.home() / "Applications" / "Job Hunter Bot.app"
        app_path.mkdir(parents=True, exist_ok=True)
        
        # Create Contents directory structure
        contents_dir = app_path / "Contents"
        contents_dir.mkdir(exist_ok=True)
        
        macos_dir = contents_dir / "MacOS"
        macos_dir.mkdir(exist_ok=True)
        
        # Create executable script
        executable = macos_dir / "JobHunterBot"
        executable.write_text(f"""#!/bin/bash
cd "{self.project_root}"
source job_hunter_env/bin/activate
python main.py
""")
        executable.chmod(0o755)
        
        # Create Info.plist
        info_plist = contents_dir / "Info.plist"
        info_plist.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>Job Hunter Bot</string>
    <key>CFBundleExecutable</key>
    <string>JobHunterBot</string>
    <key>CFBundleIdentifier</key>
    <string>com.jobhunter.bot</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
</dict>
</plist>
""")
    
    def _create_linux_shortcut(self):
        """Create Linux .desktop file"""
        desktop_entry = f"""[Desktop Entry]
Name=Job Hunter Bot
Comment=AI-powered job hunting assistant
Exec={self._get_venv_python()} {self.project_root}/main.py
Icon=applications-office
Terminal=false
Type=Application
Categories=Office;
StartupNotify=true
Path={self.project_root}
"""
        
        desktop_file = Path.home() / "Desktop" / "JobHunterBot.desktop"
        desktop_file.write_text(desktop_entry)
        desktop_file.chmod(0o755)
        
        # Also create in applications directory
        apps_dir = Path.home() / ".local" / "share" / "applications"
        apps_dir.mkdir(parents=True, exist_ok=True)
        
        app_file = apps_dir / "JobHunterBot.desktop"
        app_file.write_text(desktop_entry)
        app_file.chmod(0o755)


def create_run_scripts():
    """Create platform-specific run scripts"""
    
    # Windows batch file
    windows_script = """@echo off
title Job Hunter Bot
cd /d "%~dp0"

echo Starting Job Hunter Bot...
echo.

if not exist "job_hunter_env" (
    echo Virtual environment not found!
    echo Please run setup_job_hunter.py first.
    pause
    exit /b 1
)

call job_hunter_env\Scripts\activate
python main.py

if errorlevel 1 (
    echo.
    echo Job Hunter Bot encountered an error.
    echo Check the log files in data/logs/ for details.
    pause
)
"""
    
    with open("run_job_hunter.bat", "w") as f:
        f.write(windows_script)
    
    # Unix shell script  
    unix_script = """#!/bin/bash

echo "Starting Job Hunter Bot..."
echo

cd "$(dirname "$0")"

if [ ! -d "job_hunter_env" ]; then
    echo "Virtual environment not found!"
    echo "Please run: python3 setup_job_hunter.py"
    exit 1
fi

source job_hunter_env/bin/activate

if ! python main.py; then
    echo
    echo "Job Hunter Bot encountered an error."
    echo "Check the log files in data/logs/ for details."
    read -p "Press Enter to continue..."
fi
"""
    
    with open("run_job_hunter.sh", "w") as f:
        f.write(unix_script)
    
    # Make executable on Unix systems
    if platform.system() != "Windows":
        os.chmod("run_job_hunter.sh", 0o755)


def create_development_tools():
    """Create development and maintenance tools"""
    
    # Update script
    update_script = """#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

def update_job_hunter():
    print("Updating Job Hunter Bot...")
    
    # Update from git if available
    try:
        subprocess.check_call(["git", "pull"])
        print("✓ Updated from Git repository")
    except:
        print("⚠ Git update not available")
    
    # Update Python dependencies
    venv_python = "job_hunter_env/bin/python" if sys.platform != "win32" else "job_hunter_env/Scripts/python.exe"
    
    try:
        subprocess.check_call([venv_python, "-m", "pip", "install", "--upgrade", "-r", "requirements.txt"])
        print("✓ Updated Python dependencies")
    except Exception as e:
        print(f"✗ Failed to update dependencies: {e}")
        return False
    
    print("✓ Job Hunter Bot updated successfully!")
    return True

if __name__ == "__main__":
    update_job_hunter()
"""
    
    with open("update_job_hunter.py", "w") as f:
        f.write(update_script)
    
    # Backup script
    backup_script = """#!/usr/bin/env python3
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

def backup_job_hunter():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = Path(f"data/backups/backup_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup database
    if Path("data/job_hunter.db").exists():
        shutil.copy2("data/job_hunter.db", backup_dir / "job_hunter.db")
        print(f"✓ Database backed up")
    
    # Backup configuration
    config_files = ["config.ini", ".env"]
    for config_file in config_files:
        if Path(config_file).exists():
            shutil.copy2(config_file, backup_dir / config_file)
    
    print(f"✓ Backup created: {backup_dir}")
    return str(backup_dir)

if __name__ == "__main__":
    backup_job_hunter()
"""
    
    with open("backup_job_hunter.py", "w") as f:
        f.write(backup_script)


def main():
    """Main setup function"""
    
    print("🤖 Job Hunter Bot - Complete Setup")
    print("=" * 50)
    print("This will set up your AI-powered job hunting assistant!")
    print()
    
    setup = JobHunterSetup()
    
    # Ask user for setup preferences
    print("Setup Options:")
    print("1. Complete setup (recommended)")
    print("2. Quick setup (minimal)")
    print("3. Development setup (includes testing tools)")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "3":
        # Development setup
        success = setup.run_complete_setup()
        if success:
            create_development_tools()
            print("🔧 Development tools created")
    elif choice == "2":
        # Quick setup - just the essentials
        print("Running quick setup...")
        success = (
            setup.check_requirements() and
            setup.create_project_structure() and
            setup.setup_virtual_environment() and
            setup.install_dependencies() and
            setup.setup_database()
        )
    else:
        # Complete setup
        success = setup.run_complete_setup()
        if success:
            setup.create_desktop_shortcuts()
    
    # Create run scripts regardless
    create_run_scripts()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\n📋 Next steps:")
        print("   1. Run the application:")
        if platform.system() == "Windows":
            print("      Double-click: run_job_hunter.bat")
        else:
            print("      Run: ./run_job_hunter.sh")
        print("   2. Set up your user profile")
        print("   3. Add your OpenAI API key")
        print("   4. Start job hunting!")
        
        print("\n📚 Documentation:")
        print("   - User Guide: docs/user_guide.md")
        print("   - Troubleshooting: docs/troubleshooting.md")
        print("   - API Reference: docs/api_reference.md")
        
        print("\n🆘 Need help?")
        print("   - Check logs: data/logs/")
        print("   - GitHub Issues: https://github.com/your-repo/job-hunter-bot/issues")
        
    else:
        print("\n❌ Setup failed!")
        print("Please check the error messages above and try again.")
        print("You can also run individual setup steps manually.")
        
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)