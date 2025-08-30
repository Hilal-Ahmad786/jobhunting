#!/usr/bin/env python3
"""
Job Hunter Bot - Main Application Entry Point
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check if all required dependencies are available"""
    required_modules = [
        ('PyQt6', 'PyQt6'),
        ('selenium', 'selenium'), 
        ('bs4', 'beautifulsoup4'),  # bs4 is the import name
        ('requests', 'requests'),
        ('openai', 'openai'),
        ('pandas', 'pandas'),
        ('webdriver_manager', 'webdriver_manager')
    ]
    
    missing = []
    for import_name, package_name in required_modules:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
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
        "data/logs", "data/backups", "data/exports", "data/cv_templates"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def setup_logging():
    """Setup application logging"""
    os.makedirs("data/logs", exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"data/logs/job_hunter.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main application entry point"""
    
    # Check dependencies first
    if not check_dependencies():
        return 1
    
    # Create project structure
    create_project_structure()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # PyQt6 imports
        from PyQt6.QtWidgets import QApplication, QMessageBox
        from PyQt6.QtCore import Qt
        
        # Import our modules
        from gui.main_window import MainWindow, create_application
        from core.database.database_manager import DatabaseManager
        
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
            return 1
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Job Hunter Bot started successfully")
        
        # Run application
        return app.exec()
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure all core files are created!")
        return 1
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
