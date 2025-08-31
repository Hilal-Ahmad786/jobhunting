#!/usr/bin/env python3
"""
Quick Fix Script for Job Hunter Bot
Fixes critical issues and gets the app running
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

def setup_logging():
    """Setup basic logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def fix_imports():
    """Fix common import issues"""
    logger = logging.getLogger(__name__)
    
    # Add current directory to Python path
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    
    logger.info("✅ Python path configured")

def create_missing_directories():
    """Create any missing directories"""
    logger = logging.getLogger(__name__)
    
    directories = [
        "data/logs", "data/backups", "data/exports", "data/cv_templates",
        "core/scrapers", "core/database", "core/ai", "gui/dialogs", "gui/widgets"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Create __init__.py files
    init_files = [
        "core/__init__.py", "core/database/__init__.py", "core/scrapers/__init__.py",
        "core/ai/__init__.py", "gui/__init__.py", "gui/dialogs/__init__.py", "gui/widgets/__init__.py"
    ]
    
    for init_file in init_files:
        Path(init_file).touch()
    
    logger.info("✅ Directory structure verified")

def test_database_connection():
    """Test database connection and create if needed"""
    logger = logging.getLogger(__name__)
    
    try:
        db_path = "data/job_hunter.db"
        Path("data").mkdir(exist_ok=True)
        
        # Test connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create basic table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company_name TEXT NOT NULL,
                url TEXT UNIQUE,
                source TEXT NOT NULL,
                job_type TEXT NOT NULL,
                description TEXT,
                location_data TEXT,
                salary_data TEXT,
                scraped_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Database connection successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return False

def test_core_imports():
    """Test if core modules can be imported"""
    logger = logging.getLogger(__name__)
    
    core_modules = [
        ('PyQt6.QtWidgets', 'QApplication'),
        ('requests', 'get'),
        ('bs4', 'BeautifulSoup'),
        ('sqlite3', 'connect')
    ]
    
    missing_modules = []
    
    for module_name, attr in core_modules:
        try:
            module = __import__(module_name, fromlist=[attr])
            getattr(module, attr)
            logger.info(f"✅ {module_name} imported successfully")
        except ImportError:
            missing_modules.append(module_name)
            logger.error(f"❌ {module_name} not found")
        except AttributeError:
            logger.error(f"❌ {module_name}.{attr} not found")
    
    return len(missing_modules) == 0, missing_modules

def fix_scraper_imports():
    """Fix common scraper import issues"""
    logger = logging.getLogger(__name__)
    
    # Check if critical scraper files exist
    scraper_files = [
        "core/scrapers/linkedin_scraper.py",
        "core/scrapers/indeed_scraper.py",
        "core/scrapers/base_scraper.py"
    ]
    
    missing_files = []
    for file_path in scraper_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.warning(f"⚠️  Missing scraper files: {missing_files}")
        return False
    
    logger.info("✅ Core scraper files present")
    return True

def create_sample_env_file():
    """Create .env file from .env.example if it doesn't exist"""
    logger = logging.getLogger(__name__)
    
    if not Path(".env").exists() and Path(".env.example").exists():
        # Copy .env.example to .env
        env_example = Path(".env.example").read_text()
        Path(".env").write_text(env_example)
        logger.info("✅ Created .env file from example")
    elif not Path(".env").exists():
        # Create basic .env file
        basic_env = """# Job Hunter Bot Environment Configuration
OPENAI_API_KEY=your_openai_api_key_here
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
HEADLESS_SCRAPING=True
LOG_LEVEL=INFO
"""
        Path(".env").write_text(basic_env)
        logger.info("✅ Created basic .env file")

def run_basic_functionality_test():
    """Test basic application functionality"""
    logger = logging.getLogger(__name__)
    
    try:
        # Test if we can import our core modules
        sys.path.insert(0, '.')
        
        # Test database models
        from core.database.models import Job, Company, Location, JobType
        logger.info("✅ Models imported successfully")
        
        # Test creating a sample job
        company = Company(name="Test Company")
        location = Location(city="Test City")
        job = Job(
            title="Test Job",
            company=company,
            location=location,
            description="Test description",
            url="https://test.com",
            source="Test",
            job_type=JobType.IT_PROGRAMMING
        )
        logger.info("✅ Job object created successfully")
        
        # Test database manager
        from core.database.database_manager import DatabaseManager
        db = DatabaseManager()
        db.close()
        logger.info("✅ Database manager initialized")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Functionality test failed: {e}")
        return False

def install_missing_dependencies():
    """Install missing Python dependencies"""
    logger = logging.getLogger(__name__)
    
    try:
        import subprocess
        
        # Essential packages
        essential_packages = [
            'PyQt6', 'requests', 'beautifulsoup4', 'selenium', 
            'webdriver-manager', 'openai', 'pandas'
        ]
        
        for package in essential_packages:
            try:
                __import__(package.replace('-', '_').lower())
            except ImportError:
                logger.info(f"Installing {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        
        logger.info("✅ All dependencies verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Dependency installation failed: {e}")
        return False

def main():
    """Main quick fix function"""
    print("🔧 Job Hunter Bot Quick Fix")
    print("=" * 40)
    
    logger = setup_logging()
    
    # Run fixes in order
    fixes = [
        ("Setting up logging", lambda: True),
        ("Fixing imports", fix_imports),
        ("Creating directories", create_missing_directories),
        ("Creating .env file", create_sample_env_file),
        ("Testing database", test_database_connection),
        ("Checking dependencies", lambda: test_core_imports()[0]),
        ("Testing scrapers", fix_scraper_imports),
        ("Testing functionality", run_basic_functionality_test)
    ]
    
    passed = 0
    failed = 0
    
    for description, fix_func in fixes:
        print(f"\n🔧 {description}...")
        try:
            if fix_func():
                print(f"✅ {description} - SUCCESS")
                passed += 1
            else:
                print(f"⚠️  {description} - NEEDS ATTENTION")
                failed += 1
        except Exception as e:
            print(f"❌ {description} - FAILED: {e}")
            failed += 1
    
    print(f"\n📊 RESULTS")
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Need attention: {failed}")
    
    if failed == 0:
        print(f"\n🎉 All fixes applied successfully!")
        print(f"🚀 You can now run: python main.py")
    else:
        print(f"\n🔧 Some issues need manual attention")
        print(f"💡 Check the output above and fix the failed items")
    
    # Give specific next steps
    print(f"\n📋 NEXT STEPS:")
    print(f"1. Run: python main.py")
    print(f"2. If you get import errors, install: pip install -r requirements.txt")
    print(f"3. Add your OpenAI API key to .env file for AI features")
    print(f"4. Start searching for jobs!")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)