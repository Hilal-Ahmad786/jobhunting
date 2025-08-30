# ===== main.py - Application Entry Point =====

#!/usr/bin/env python3
"""
Job Hunter Bot - Main Application Entry Point

AI-powered desktop application for automated job hunting,
CV optimization, and application tracking.
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# PyQt6 imports
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

# Our modules
try:
    from gui.main_window import MainWindow, create_application, setup_logging
    from core.database.database_manager import DatabaseManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


def check_dependencies():
    """Check if all required dependencies are available"""
    required_modules = [
        'PyQt6', 'selenium', 'beautifulsoup4', 'requests', 
        'openai', 'pandas', 'webdriver_manager'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if missing:
        print("Missing dependencies:")
        for module in missing:
            print(f"  - {module}")
        print("\nPlease install: pip install -r requirements.txt")
        return False
    
    return True


def create_project_structure():
    """Create necessary project directories"""
    directories = [
        "data/logs",
        "data/backups", 
        "data/exports",
        "data/cv_templates",
        "core/scrapers",
        "core/ai",
        "core/database",
        "core/utils",
        "core/config",
        "gui/dialogs",
        "gui/widgets",
        "gui/resources/icons",
        "tests",
        "docs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py files
    init_files = [
        "core/__init__.py",
        "core/scrapers/__init__.py",
        "core/ai/__init__.py", 
        "core/database/__init__.py",
        "core/utils/__init__.py",
        "core/config/__init__.py",
        "gui/__init__.py",
        "gui/dialogs/__init__.py",
        "gui/widgets/__init__.py",
        "tests/__init__.py"
    ]
    
    for init_file in init_files:
        Path(init_file).touch()


def main():
    """Main application entry point"""
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Create project structure
    create_project_structure()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create Qt application
        app = create_application()
        logger.info("Starting Job Hunter Bot...")
        
        # Check database
        try:
            db = DatabaseManager()
            db.close()
        except Exception as e:
            QMessageBox.critical(None, "Database Error", 
                               f"Failed to initialize database:\n{str(e)}")
            sys.exit(1)
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Job Hunter Bot started successfully")
        
        # Run application
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        if 'app' in locals():
            QMessageBox.critical(None, "Startup Error", 
                               f"Application failed to start:\n{str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# ===== .env.example - Environment Variables Template =====

"""
# Job Hunter Bot Environment Configuration
# Copy this file to .env and update with your actual values

# ===== API KEYS =====
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here-optional

# ===== EMAIL CONFIGURATION =====
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password-here
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# ===== DATABASE =====
DATABASE_PATH=data/job_hunter.db
BACKUP_INTERVAL_DAYS=7
CLEANUP_AFTER_DAYS=90

# ===== SCRAPING CONFIGURATION =====
HEADLESS_SCRAPING=True
MAX_CONCURRENT_SCRAPERS=5
DEFAULT_JOB_LIMIT=100
RATE_LIMIT_RPM=30

# ===== LINKEDIN CREDENTIALS (OPTIONAL) =====
LINKEDIN_USERNAME=your-linkedin-email@email.com
LINKEDIN_PASSWORD=your-linkedin-password

# ===== PROXY SETTINGS (OPTIONAL) =====
HTTP_PROXY=
HTTPS_PROXY=

# ===== LOGGING =====
LOG_LEVEL=INFO
LOG_TO_FILE=True
LOG_TO_CONSOLE=True

# ===== APPLICATION SETTINGS =====
DEFAULT_CURRENCY=USD
TIMEZONE=UTC
LANGUAGE=en

# ===== DEVELOPMENT =====
DEBUG_MODE=False
ENABLE_PROFILING=False
"""


# ===== config.ini - Application Configuration =====

"""
[Database]
path = data/job_hunter.db
backup_interval_days = 7
cleanup_after_days = 90
enable_foreign_keys = True
connection_timeout = 30
max_connections = 10

[Scraping]
max_concurrent_scrapers = 5
default_job_limit = 100
rate_limit_requests_per_minute = 30
enable_stealth_mode = True
user_agent_rotation = True
proxy_rotation = False
retry_attempts = 3
timeout_seconds = 300

[AI]
model = gpt-4
temperature = 0.3
max_tokens = 2000
enable_cv_optimization = True
enable_cover_letter_generation = True
enable_proposal_generation = True
batch_optimization_limit = 10

[Notifications]
enable_desktop = True
enable_email = False
enable_system_tray = True
alert_check_interval_minutes = 60
notification_sound = True

[GUI]
theme = modern
auto_refresh_interval_minutes = 5
window_width = 1600
window_height = 1000
remember_window_state = True
enable_animations = True
show_system_tray = True

[Security]
encrypt_api_keys = True
hash_personal_data = True
enable_ssl_verification = True

[Performance]
enable_caching = True
cache_expiry_minutes = 60
max_memory_usage_mb = 1024
enable_compression = True

[Export]
default_format = json
include_personal_data = False
compress_exports = True

[Advanced]
enable_market_analysis = True
enable_salary_predictions = True
enable_skills_recommendations = True
enable_company_research = True
"""


# ===== .gitignore - Git Ignore Rules =====

"""
# Job Hunter Bot - Git Ignore File

# ===== SENSITIVE DATA =====
.env
*.env
config.ini
api_keys.json

# ===== DATABASE FILES =====
*.db
*.sqlite
*.sqlite3
data/job_hunter.db*
data/backups/*.db

# ===== LOG FILES =====
*.log
logs/
data/logs/

# ===== TEMPORARY FILES =====
*.tmp
*.temp
temp/
cache/

# ===== USER DATA =====
data/cv_templates/
data/exports/
user_profiles/

# ===== PYTHON =====
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# ===== VIRTUAL ENVIRONMENTS =====
job_hunter_env/
venv/
env/
ENV/
.venv/

# ===== IDE FILES =====
.vscode/
.idea/
*.swp
*.swo
*~

# ===== MACOS =====
.DS_Store
.AppleDouble
.LSOverride

# ===== WINDOWS =====
Thumbs.db
ehthumbs.db
Desktop.ini

# ===== WEB DRIVERS =====
chromedriver*
geckodriver*
*.exe

# ===== BACKUP FILES =====
*.bak
*.backup
*.old

# ===== EXPORTS =====
*.csv
*.xlsx
*.json
data/exports/

# ===== SCREENSHOTS =====
screenshots/
*.png
*.jpg
*.jpeg
"""


# ===== setup.py - Package Configuration =====

"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="job-hunter-bot",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered job hunting desktop application",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/job-hunter-bot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-qt>=4.2.0",
            "black>=23.9.1",
            "flake8>=6.1.0",
            "mypy>=1.6.0",
        ],
        "advanced": [
            "schedule>=1.2.0",
            "APScheduler>=3.10.4",
            "redis>=5.0.0",
            "celery>=5.3.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "job-hunter=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "gui": ["resources/*", "resources/icons/*"],
        "docs": ["*.md"],
    },
)
"""


# ===== Dockerfile - Container Deployment =====

"""
# Job Hunter Bot - Docker Configuration
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/logs data/backups data/exports data/cv_templates

# Set environment variables
ENV DISPLAY=:99
ENV HEADLESS_SCRAPING=True
ENV LOG_LEVEL=INFO

# Expose port (if web interface added later)
EXPOSE 8000

# Create startup script
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1024x768x24 &\npython main.py' > /app/start.sh
RUN chmod +x /app/start.sh

# Run application
CMD ["/app/start.sh"]
"""


# ===== docker-compose.yml - Docker Compose Configuration =====

"""
version: '3.8'

services:
  job-hunter-bot:
    build: .
    container_name: job-hunter-bot
    volumes:
      - ./data:/app/data
      - ./config.ini:/app/config.ini
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - EMAIL_USERNAME=${EMAIL_USERNAME}
      - EMAIL_PASSWORD=${EMAIL_PASSWORD}
      - HEADLESS_SCRAPING=True
    restart: unless-stopped
    
    # Optional: Add database service
    depends_on:
      - postgres
      
  postgres:
    image: postgres:15
    container_name: job-hunter-db
    environment:
      - POSTGRES_DB=job_hunter
      - POSTGRES_USER=jobhunter
      - POSTGRES_PASSWORD=secure_password_here
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  postgres_data:
"""


# ===== install_wizard.py - GUI Installation Wizard =====

#!/usr/bin/env python3
"""
Job Hunter Bot Installation Wizard
Interactive GUI installer for easy setup
"""

import sys
import os
import subprocess
from pathlib import Path

try:
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *
except ImportError:
    print("PyQt6 not found. Installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
    from PyQt6.QtWidgets import *
    from PyQt6.QtCore import *
    from PyQt6.QtGui import *


class InstallationWizard(QWizard):
    """GUI installation wizard"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Job Hunter Bot - Installation Wizard")
        self.setFixedSize(600, 400)
        
        # Add wizard pages
        self.addPage(self.create_intro_page())
        self.addPage(self.create_dependencies_page())
        self.addPage(self.create_config_page())
        self.addPage(self.create_completion_page())
    
    def create_intro_page(self):
        """Create introduction page"""
        page = QWizardPage()
        page.setTitle("Welcome to Job Hunter Bot")
        page.setSubTitle("AI-powered job hunting assistant")
        
        layout = QVBoxLayout()
        
        intro_text = QLabel("""
        <h2>Welcome!</h2>
        <p>This wizard will help you set up Job Hunter Bot, an AI-powered application that:</p>
        <ul>
        <li><b>Finds jobs automatically</b> across LinkedIn, Indeed, Upwork, and more</li>
        <li><b>Optimizes your CV</b> using AI for each specific position</li>
        <li><b>Tracks applications</b> and response rates</li>
        <li><b>Sends job alerts</b> for your dream roles</li>
        </ul>
        
        <p>Let's get started!</p>
        """)
        intro_text.setWordWrap(True)
        layout.addWidget(intro_text)
        
        page.setLayout(layout)
        return page
    
    def create_dependencies_page(self):
        """Create dependencies installation page"""
        page = QWizardPage()
        page.setTitle("Installing Dependencies")
        page.setSubTitle("Setting up required libraries and tools")
        
        layout = QVBoxLayout()
        
        self.dep_progress = QProgressBar()
        layout.addWidget(self.dep_progress)
        
        self.dep_status = QLabel("Ready to install dependencies...")
        layout.addWidget(self.dep_status)
        
        install_btn = QPushButton("Install Dependencies")
        install_btn.clicked.connect(self.install_dependencies)
        layout.addWidget(install_btn)
        
        page.setLayout(layout)
        return page
    
    def create_config_page(self):
        """Create configuration page"""
        page = QWizardPage()
        page.setTitle("Configuration")
        page.setSubTitle("Set up your preferences and API keys")
        
        layout = QFormLayout()
        
        # User info
        self.name_input = QLineEdit()
        layout.addRow("Your Name:", self.name_input)
        
        self.email_input = QLineEdit()
        layout.addRow("Email:", self.email_input)
        
        # API key
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("OpenAI API Key:", self.api_key_input)
        
        api_help = QLabel('<a href="https://platform.openai.com/api-keys">Get your API key here</a>')
        api_help.setOpenExternalLinks(True)
        layout.addRow("", api_help)
        
        page.setLayout(layout)
        return page
    
    def create_completion_page(self):
        """Create completion page"""
        page = QWizardPage()
        page.setTitle("Installation Complete!")
        page.setSubTitle("Your Job Hunter Bot is ready to use")
        
        layout = QVBoxLayout()
        
        completion_text = QLabel("""
        <h3>🎉 Setup Complete!</h3>
        
        <p>Your Job Hunter Bot is now configured and ready to help you find your dream job.</p>
        
        <h4>Next Steps:</h4>
        <ol>
        <li><b>Upload your CV</b> in the User Profile section</li>
        <li><b>Set job preferences</b> (remote, salary, locations)</li>
        <li><b>Start your first job search</b> with relevant keywords</li>
        <li><b>Let AI optimize your applications</b> automatically</li>
        </ol>
        
        <p><b>Pro Tips:</b></p>
        <ul>
        <li>Enable job alerts for passive job hunting</li>
        <li>Use the analytics tab to track your success</li>
        <li>Try batch applying to save time</li>
        </ul>
        
        <p>Happy job hunting! 🚀</p>
        """)
        completion_text.setWordWrap(True)
        layout.addWidget(completion_text)
        
        page.setLayout(layout)
        return page
    
    def install_dependencies(self):
        """Install Python dependencies"""
        try:
            self.dep_status.setText("Installing Python packages...")
            self.dep_progress.setValue(20)
            
            # Install requirements
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ])
            
            self.dep_progress.setValue(60)
            self.dep_status.setText("Setting up ChromeDriver...")
            
            # Setup ChromeDriver
            subprocess.check_call([
                sys.executable, "-c", 
                "from webdriver_manager.chrome import ChromeDriverManager; ChromeDriverManager().install()"
            ])
            
            self.dep_progress.setValue(100)
            self.dep_status.setText("Dependencies installed successfully! ✓")
            
        except subprocess.CalledProcessError as e:
            self.dep_status.setText(f"Installation failed: {e}")
            QMessageBox.critical(self, "Installation Error", 
                               f"Failed to install dependencies:\n{str(e)}")


def run_installation_wizard():
    """Run the GUI installation wizard"""
    app = QApplication(sys.argv)
    
    wizard = InstallationWizard()
    
    if wizard.exec() == QWizard.DialogCode.Accepted:
        # Create config files with user input
        name = wizard.name_input.text()
        email = wizard.email_input.text()
        api_key = wizard.api_key_input.text()
        
        # Save to config file or database
        print(f"Setup completed for {name} ({email})")
        
    app.quit()


# ===== Quick Start Scripts =====

# run_windows.bat
"""
@echo off
title Job Hunter Bot
cd /d "%~dp0"

if not exist "job_hunter_env" (
    echo Creating virtual environment...
    python -m venv job_hunter_env
)

call job_hunter_env\Scripts\activate
python main.py
pause
"""

# run_macos_linux.sh  
"""
#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "job_hunter_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv job_hunter_env
fi

source job_hunter_env/bin/activate
python main.py
"""


# ===== Development Tools =====

# run_tests.py
"""
#!/usr/bin/env python3
import subprocess
import sys

def run_tests():
    \"\"\"Run all tests\"\"\"
    
    print("Running Job Hunter Bot Tests...")
    print("=" * 40)
    
    test_commands = [
        # Unit tests
        ["python", "-m", "pytest", "tests/", "-v"],
        
        # Code quality
        ["python", "-m", "flake8", "core/", "gui/", "--max-line-length=100"],
        
        # Type checking  
        ["python", "-m", "mypy", "core/", "--ignore-missing-imports"],
        
        # Security check
        ["python", "-m", "bandit", "-r", "core/", "gui/"]
    ]
    
    for cmd in test_commands:
        try:
            print(f"Running: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            print("✓ Passed\n")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed: {e}\n")
            return False
    
    print("All tests passed! ✓")
    return True

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
"""


# ===== Performance Monitor =====

# monitor_performance.py
"""
#!/usr/bin/env python3
import psutil
import time
from datetime import datetime

def monitor_application():
    \"\"\"Monitor Job Hunter Bot performance\"\"\"
    
    print("Job Hunter Bot Performance Monitor")
    print("=" * 40)
    
    while True:
        try:
            # Find Job Hunter Bot process
            job_hunter_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                if 'python' in proc.info['name'].lower() and 'main.py' in ' '.join(proc.cmdline()):
                    job_hunter_processes.append(proc)
            
            if job_hunter_processes:
                for proc in job_hunter_processes:
                    memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                    cpu_percent = proc.info['cpu_percent']
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"PID: {proc.info['pid']} | "
                          f"Memory: {memory_mb:.1f}MB | "
                          f"CPU: {cpu_percent:.1f}%")
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Job Hunter Bot not running")
            
            time.sleep(30)  # Check every 30 seconds
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            break
        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    monitor_application()
"""


# ===== Database Migration Tool =====

# migrate_database.py
"""
#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.database.database_manager import DatabaseManager, DatabaseMigrator

def main():
    \"\"\"Database migration utility\"\"\"
    
    print("Job Hunter Bot Database Migration Tool")
    print("=" * 40)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    migrator = DatabaseMigrator(db_manager)
    
    # Get current version
    current_version = migrator.get_current_version()
    print(f"Current database version: {current_version}")
    
    # Check if migration is needed
    target_version = 3  # Latest version
    
    if current_version >= target_version:
        print("Database is up to date!")
        return
    
    # Run migration
    print(f"Migrating database from v{current_version} to v{target_version}...")
    
    try:
        migrator.migrate_to_version(target_version)
        print("Migration completed successfully! ✓")
    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    
    # Close database
    db_manager.close()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
"""


# ===== Build Script =====

# build_executable.py
"""
#!/usr/bin/env python3
\"\"\"
Build standalone executable for Job Hunter Bot
Uses PyInstaller to create distributable application
\"\"\"

import subprocess
import sys
import shutil
from pathlib import Path

def build_executable():
    \"\"\"Build standalone executable\"\"\"
    
    print("Building Job Hunter Bot Executable...")
    print("=" * 40)
    
    # Install PyInstaller if not available
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=JobHunterBot",
        "--windowed",  # No console window
        "--onefile",   # Single executable
        "--icon=gui/resources/icons/app.ico",  # App icon
        "--add-data=core;core",
        "--add-data=gui;gui", 
        "--add-data=data;data",
        "--hidden-import=PyQt6",
        "--hidden-import=selenium",
        "--hidden-import=openai",
        "main.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("✓ Executable built successfully!")
        print("Find it in: dist/JobHunterBot.exe")
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)
"""