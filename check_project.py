#!/usr/bin/env python3
"""
Job Hunter Bot Project Diagnostic Script
Checks what's missing and provides specific fix instructions
"""

import sys
import sqlite3
from pathlib import Path
import importlib.util
import subprocess

class ProjectDiagnostic:
    """Diagnose Job Hunter Bot project status"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.issues = []
        self.fixes = []
        
    def run_full_diagnostic(self):
        """Run complete project diagnostic"""
        print("🔍 Job Hunter Bot Project Diagnostic")
        print("=" * 50)
        
        # Check project structure
        self.check_project_structure()
        
        # Check Python files
        self.check_python_files()
        
        # Check dependencies
        self.check_dependencies()
        
        # Check database
        self.check_database()
        
        # Check configuration
        self.check_configuration()
        
        # Print summary
        self.print_summary()
        
        return len(self.issues) == 0
    
    def check_project_structure(self):
        """Check if all directories exist"""
        print("\n📁 Checking Project Structure...")
        
        required_dirs = [
            "core", "core/database", "core/scrapers", "core/ai", "core/utils", "core/config",
            "gui", "gui/dialogs", "gui/widgets", "gui/resources",
            "data", "data/logs", "data/backups", "data/exports", "data/cv_templates",
            "tests", "docs"
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
            else:
                print(f"  ✅ {dir_path}")
        
        if missing_dirs:
            print(f"  ❌ Missing directories: {missing_dirs}")
            self.issues.append("Missing directories")
            self.fixes.append("Run: mkdir -p " + " ".join(missing_dirs))
        else:
            print("  ✅ All directories present")
    
    def check_python_files(self):
        """Check if all required Python files exist"""
        print("\n🐍 Checking Python Files...")
        
        essential_files = {
            "main.py": "Application entry point",
            "core/__init__.py": "Core module init",
            "core/database/__init__.py": "Database module init",
            "core/database/models.py": "Data models (Job, UserProfile, etc.)",
            "core/database/database_manager.py": "Database operations",
            "core/scrapers/__init__.py": "Scrapers module init",
            "core/scrapers/base_scraper.py": "Base scraper framework",
            "core/scrapers/scraper_manager.py": "Multi-scraper coordinator",
            "core/ai/__init__.py": "AI module init",
            "core/ai/cv_optimizer.py": "CV optimization with OpenAI",
            "gui/__init__.py": "GUI module init",
            "gui/main_window.py": "Main application window"
        }
        
        missing_files = []
        for file_path, description in essential_files.items():
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append((file_path, description))
                print(f"  ❌ {file_path} - {description}")
            else:
                # Check if file has content
                if full_path.stat().st_size < 100:  # Less than 100 bytes probably empty
                    print(f"  ⚠️ {file_path} - EXISTS but appears empty")
                    missing_files.append((file_path, description))
                else:
                    print(f"  ✅ {file_path} - {full_path.stat().st_size} bytes")
        
        if missing_files:
            self.issues.append("Missing Python files")
            self.fixes.extend([f"Create {path} - {desc}" for path, desc in missing_files])
        
        return len(missing_files) == 0
    
    def check_dependencies(self):
        """Check Python dependencies"""
        print("\n📦 Checking Dependencies...")
        
        required_packages = [
            ("PyQt6", "GUI framework"),
            ("selenium", "Web scraping"),
            ("beautifulsoup4", "HTML parsing"),
            ("requests", "HTTP requests"),
            ("openai", "AI integration"),
            ("pandas", "Data processing"),
            ("webdriver_manager", "ChromeDriver management")
        ]
        
        missing_packages = []
        for package, description in required_packages:
            try:
                spec = importlib.util.find_spec(package)
                if spec is None:
                    missing_packages.append((package, description))
                    print(f"  ❌ {package} - {description}")
                else:
                    print(f"  ✅ {package}")
            except Exception:
                missing_packages.append((package, description))
                print(f"  ❌ {package} - Error checking")
        
        if missing_packages:
            self.issues.append("Missing dependencies")
            self.fixes.append("Run: pip install " + " ".join([pkg[0] for pkg in missing_packages]))
        
        return len(missing_packages) == 0
    
    def check_database(self):
        """Check database structure"""
        print("\n🗄️ Checking Database...")
        
        db_path = self.project_root / "data" / "job_hunter.db"
        if not db_path.exists():
            print("  ❌ Database file doesn't exist")
            self.issues.append("No database file")
            self.fixes.append("Database will be created on first run")
            return False
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            print(f"  📊 Found tables: {tables}")
            
            # Check for expected tables
            expected_tables = ["jobs", "applications", "user_profiles", "analytics", "settings"]
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                print(f"  ❌ Missing tables: {missing_tables}")
                self.issues.append("Incomplete database schema")
                self.fixes.append("Database needs proper initialization")
            
            # Check jobs table structure if it exists
            if "jobs" in tables:
                cursor.execute("PRAGMA table_info(jobs);")
                columns = [row[1] for row in cursor.fetchall()]
                print(f"  📋 Jobs table columns: {columns}")
                
                expected_columns = ["id", "title", "company_name", "url", "source", "scraped_date"]
                missing_columns = [col for col in expected_columns if col not in columns]
                
                if missing_columns:
                    print(f"  ❌ Jobs table missing columns: {missing_columns}")
                    self.issues.append("Jobs table has wrong schema")
                    self.fixes.append("Database schema needs migration")
                else:
                    print("  ✅ Jobs table schema looks correct")
            
            conn.close()
            return len(missing_tables) == 0
            
        except Exception as e:
            print(f"  ❌ Database error: {e}")
            self.issues.append(f"Database error: {e}")
            self.fixes.append("Delete database file and let app recreate it")
            return False
    
    def check_configuration(self):
        """Check configuration files"""
        print("\n⚙️ Checking Configuration...")
        
        config_files = {
            "requirements.txt": "Python dependencies list",
            "config.ini": "Application configuration",
            ".env.example": "Environment variables template",
            ".gitignore": "Git ignore rules"
        }
        
        for file_path, description in config_files.items():
            full_path = self.project_root / file_path
            if not full_path.exists():
                print(f"  ❌ {file_path} - {description}")
                self.issues.append(f"Missing {file_path}")
            else:
                print(f"  ✅ {file_path}")
    
    def print_summary(self):
        """Print diagnostic summary and fixes"""
        print("\n" + "=" * 50)
        print("📋 DIAGNOSTIC SUMMARY")
        print("=" * 50)
        
        if not self.issues:
            print("🎉 All checks passed! Your project looks good.")
            return
        
        print(f"❌ Found {len(self.issues)} issues:")
        for i, issue in enumerate(self.issues, 1):
            print(f"  {i}. {issue}")
        
        print(f"\n🔧 FIXES NEEDED:")
        print("=" * 30)
        for i, fix in enumerate(self.fixes, 1):
            print(f"{i}. {fix}")
        
        print(f"\n🚀 QUICK FIX COMMANDS:")
        print("=" * 30)
        self.generate_fix_commands()
    
    def generate_fix_commands(self):
        """Generate specific fix commands"""
        
        # Check what's the main issue
        if "Missing Python files" in str(self.issues):
            print("📁 MISSING CORE FILES - Copy these from our conversation:")
            print("""
# 1. Create core/database/models.py with our complete data models
# 2. Create core/database/database_manager.py with database operations  
# 3. Create core/scrapers/base_scraper.py with scraper framework
# 4. Create core/scrapers/scraper_manager.py with multi-scraper logic
# 5. Create core/ai/cv_optimizer.py with OpenAI integration
# 6. Create gui/main_window.py with complete desktop interface
""")
        
        if "database" in str(self.issues).lower():
            print("🗄️ DATABASE ISSUES:")
            print("# Delete and recreate database:")
            print("rm data/job_hunter.db")
            print("python -c \"from core.database.database_manager import DatabaseManager; DatabaseManager()\"")
        
        if "Missing dependencies" in str(self.issues):
            print("📦 INSTALL MISSING PACKAGES:")
            print("pip install -r requirements.txt")
        
        print(f"\n💡 NEXT STEPS:")
        print("1. Fix the issues above")
        print("2. Run: python check_project.py  (to verify fixes)")
        print("3. Run: python main.py  (to start the app)")


def create_minimal_files():
    """Create minimal versions of missing essential files"""
    print("\n🔧 Creating minimal essential files...")
    
    files_to_create = {
        "main.py": '''#!/usr/bin/env python3
import sys
from pathlib import Path

def main():
    print("Job Hunter Bot - Minimal Version")
    print("Add the core modules to make it fully functional!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
''',
        
        "core/__init__.py": "# Job Hunter Bot Core Module\n",
        "core/database/__init__.py": "# Database Module\n",
        "core/scrapers/__init__.py": "# Scrapers Module\n", 
        "core/ai/__init__.py": "# AI Module\n",
        "gui/__init__.py": "# GUI Module\n",
        
        "requirements.txt": '''PyQt6>=6.6.0
selenium>=4.15.0
beautifulsoup4>=4.12.2
requests>=2.31.0
openai>=1.3.0
pandas>=2.1.0
webdriver-manager>=4.0.1
python-dateutil>=2.8.2
''',
    }
    
    created = []
    for file_path, content in files_to_create.items():
        full_path = Path(file_path)
        
        if not full_path.exists():
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            created.append(file_path)
            print(f"  ✅ Created {file_path}")
    
    if created:
        print(f"Created {len(created)} minimal files.")
        print("Now you need to add the full code from our conversation!")
    else:
        print("All essential files already exist.")


def main():
    """Main diagnostic function"""
    diagnostic = ProjectDiagnostic()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        create_minimal_files()
        print("\n" + "="*30)
    
    success = diagnostic.run_full_diagnostic()
    
    if not success:
        print(f"\n❌ Project has issues that need fixing.")
        print(f"💡 Run: python check_project.py --fix  (to create minimal files)")
        return 1
    else:
        print(f"\n✅ Project diagnostic passed!")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)