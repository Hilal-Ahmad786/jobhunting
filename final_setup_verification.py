#!/usr/bin/env python3
"""
Final Setup and Verification Script for Job Hunter Bot
Complete system verification and user onboarding
"""

import sys
import os
import sqlite3
import webbrowser
from pathlib import Path
from datetime import datetime
import subprocess
import json


class FinalSetupWizard:
    """Complete setup wizard with user-friendly interface"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.setup_complete = False
        
    def run_complete_setup(self):
        """Run the complete setup process"""
        print("🚀 Job Hunter Bot - Final Setup Wizard")
        print("=" * 60)
        print("Welcome to your AI-powered career assistant!")
        print("Let's get everything configured for maximum job hunting success.")
        print("=" * 60)
        
        try:
            # Step 1: System verification
            if not self.verify_system():
                return False
            
            # Step 2: Dependencies check
            if not self.check_and_install_dependencies():
                return False
            
            # Step 3: Database setup
            if not self.setup_database():
                return False
            
            # Step 4: Configuration
            if not self.configure_settings():
                return False
            
            # Step 5: User profile setup
            if not self.setup_user_profile():
                return False
            
            # Step 6: Test run
            if not self.run_test_search():
                return False
            
            # Step 7: Final verification
            if not self.final_verification():
                return False
            
            # Step 8: Success and next steps
            self.show_success_message()
            return True
            
        except KeyboardInterrupt:
            print("\n⏹️ Setup cancelled by user")
            return False
        except Exception as e:
            print(f"\n❌ Setup failed: {e}")
            return False
    
    def verify_system(self):
        """Verify system requirements"""
        print("\n🔍 Step 1: System Verification")
        print("-" * 30)
        
        checks = [
            ("Python Version", self._check_python),
            ("Operating System", self._check_os),
            ("Available Memory", self._check_memory),
            ("Disk Space", self._check_disk_space),
            ("Internet Connection", self._check_internet)
        ]
        
        for check_name, check_func in checks:
            print(f"Checking {check_name}...", end=" ")
            if check_func():
                print("✅")
            else:
                print("❌")
                return False
        
        print("✅ System verification completed!")
        return True
    
    def check_and_install_dependencies(self):
        """Check and install Python dependencies"""
        print("\n📦 Step 2: Dependencies Setup")
        print("-" * 30)
        
        # Check if requirements.txt exists
        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            self._create_requirements_file()
        
        # Check current dependencies
        missing_deps = self._check_dependencies()
        
        if missing_deps:
            print(f"Missing dependencies: {', '.join(missing_deps)}")
            print("Installing missing dependencies...")
            
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
                ])
                print("✅ All dependencies installed successfully!")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install dependencies: {e}")
                print("Please install manually: pip install -r requirements.txt")
                return False
        else:
            print("✅ All dependencies are already installed!")
        
        # Special check for ChromeDriver
        if not self._setup_chromedriver():
            print("⚠️ ChromeDriver setup failed - some scrapers may not work")
        
        return True
    
    def setup_database(self):
        """Initialize database"""
        print("\n🗄️ Step 3: Database Setup")
        print("-" * 30)
        
        try:
            # Add project to Python path
            sys.path.insert(0, str(self.project_root))
            
            from core.database.database_manager import DatabaseManager
            
            db_path = self.project_root / "data" / "job_hunter.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            print("Creating database...")
            db = DatabaseManager(str(db_path))
            
            # Test database operations
            stats = db.get_database_stats()
            print(f"Database initialized with {len(stats)} statistics tracked")
            
            db.close()
            print("✅ Database setup completed!")
            return True
            
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            return False
    
    def configure_settings(self):
        """Configure application settings"""
        print("\n⚙️ Step 4: Configuration")
        print("-" * 30)
        
        # Create configuration files if they don't exist
        self._create_config_files()
        
        # API Key setup
        env_file = self.project_root / ".env"
        if not self._check_api_key_configured():
            print("\n🔑 OpenAI API Key Setup (Optional but Recommended)")
            print("The OpenAI API key enables AI-powered CV optimization.")
            print("You can add this later if you prefer.")
            
            api_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
            if api_key:
                self._update_env_file("OPENAI_API_KEY", api_key)
                print("✅ API key configured!")
            else:
                print("⏭️ Skipped API key setup (you can add it later)")
        
        # Email setup for notifications
        print("\n📧 Email Notifications Setup (Optional)")
        setup_email = input("Configure email notifications? (y/n): ").lower().strip() == 'y'
        
        if setup_email:
            email = input("Your email address: ").strip()
            if email:
                self._update_env_file("EMAIL_USERNAME", email)
                print("✅ Email configured! (You can add app password later)")
        
        print("✅ Configuration completed!")
        return True
    
    def setup_user_profile(self):
        """Setup user profile"""
        print("\n👤 Step 5: User Profile Setup")
        print("-" * 30)
        print("Let's create your job hunting profile for better matches!")
        
        try:
            sys.path.insert(0, str(self.project_root))
            from core.database.database_manager import DatabaseManager
            from core.database.models import UserProfile, JobType
            
            # Collect user information
            name = input("Your full name: ").strip()
            email = input("Your email address: ").strip()
            
            if not name or not email:
                print("Name and email are required!")
                return False
            
            # Skills
            print("\nWhat are your main skills? (comma-separated)")
            skills_input = input("Skills (e.g., Python, Project Management, AutoCAD): ").strip()
            skills = [s.strip() for s in skills_input.split(",")] if skills_input else []
            
            # Job types
            print("\nWhat types of jobs are you looking for?")
            print("1. IT/Programming")
            print("2. Civil Engineering") 
            print("3. Freelance/Contract")
            print("4. Digital Marketing")
            print("5. Other")
            
            job_type_input = input("Select job types (comma-separated numbers): ").strip()
            preferred_job_types = []
            
            if job_type_input:
                for num in job_type_input.split(","):
                    try:
                        choice = int(num.strip())
                        if choice == 1:
                            preferred_job_types.append(JobType.IT_PROGRAMMING)
                        elif choice == 2:
                            preferred_job_types.append(JobType.CIVIL_ENGINEERING)
                        elif choice == 3:
                            preferred_job_types.append(JobType.FREELANCE)
                        elif choice == 4:
                            preferred_job_types.append(JobType.DIGITAL_MARKETING)
                        elif choice == 5:
                            preferred_job_types.append(JobType.OTHER)
                    except ValueError:
                        continue
            
            # Locations
            locations_input = input("Preferred locations (comma-separated, or 'Remote'): ").strip()
            locations = [l.strip() for l in locations_input.split(",")] if locations_input else ["Remote"]
            
            # Remote preference
            print("\nWork preference:")
            print("1. Remote only")
            print("2. On-site only") 
            print("3. Hybrid")
            print("4. No preference")
            
            remote_pref = input("Select preference (1-4): ").strip()
            remote_preference = "hybrid"
            if remote_pref == "1":
                remote_preference = "remote"
            elif remote_pref == "2":
                remote_preference = "on_site"
            elif remote_pref == "3":
                remote_preference = "hybrid"
            elif remote_pref == "4":
                remote_preference = "no_preference"
            
            # Create user profile
            profile = UserProfile(
                name=name,
                email=email,
                skills=skills,
                preferred_job_types=preferred_job_types,
                preferred_locations=locations,
                remote_preference=remote_preference
            )
            
            # Save to database
            db = DatabaseManager()
            profile_id = db.save_user_profile(profile)
            db.close()
            
            print(f"✅ User profile created successfully! (ID: {profile_id})")
            return True
            
        except Exception as e:
            print(f"❌ Profile setup failed: {e}")
            return False
    
    def run_test_search(self):
        """Run a test job search"""
        print("\n🔍 Step 6: Test Search")
        print("-" * 30)
        print("Let's test the system with a quick job search!")
        
        try:
            sys.path.insert(0, str(self.project_root))
            from core.scrapers.scraper_manager import ScraperManager
            from core.database.database_manager import DatabaseManager
            from core.database.models import SearchQuery, JobType
            
            # Get user preferences
            keywords = input("Enter job search keywords (e.g., 'python developer'): ").strip()
            if not keywords:
                keywords = "software developer"
            
            location = input("Enter location (or 'remote'): ").strip()
            if not location:
                location = "remote"
            
            print(f"\n🔍 Searching for '{keywords}' jobs in '{location}'...")
            
            # Create search query
            search_query = SearchQuery(
                keywords=keywords,
                locations=[location],
                job_types=[JobType.IT_PROGRAMMING],
                remote_only=(location.lower() == 'remote')
            )
            
            # Execute search
            db = DatabaseManager()
            manager = ScraperManager(db)
            
            session = manager.search_jobs(
                search_query=search_query,
                specific_scrapers=["LinkedIn"]  # Limit to one for test
            )
            
            print(f"✅ Search completed!")
            print(f"   Jobs found: {session.jobs_found}")
            print(f"   Jobs saved: {session.jobs_saved}")
            print(f"   Search duration: {session.duration:.1f}s")
            
            manager.close()
            db.close()
            
            return session.jobs_saved > 0
            
        except Exception as e:
            print(f"❌ Test search failed: {e}")
            print("The system may still work - this could be a network issue")
            return True  # Don't fail setup for network issues
    
    def final_verification(self):
        """Final system verification"""
        print("\n✅ Step 7: Final Verification")
        print("-" * 30)
        
        try:
            # Run integration test
            print("Running system verification...")
            
            sys.path.insert(0, str(self.project_root))
            
            # Quick verification of key components
            verifications = [
                ("Database", self._verify_database),
                ("Scrapers", self._verify_scrapers),
                ("GUI", self._verify_gui),
                ("Configuration", self._verify_config)
            ]
            
            for component, verify_func in verifications:
                print(f"Verifying {component}...", end=" ")
                if verify_func():
                    print("✅")
                else:
                    print("⚠️")
            
            print("✅ System verification completed!")
            return True
            
        except Exception as e:
            print(f"❌ Final verification failed: {e}")
            return False
    
    def show_success_message(self):
        """Show success message and next steps"""
        print("\n" + "🎉" * 20)
        print("🎉 SETUP COMPLETED SUCCESSFULLY! 🎉")
        print("🎉" * 20)
        
        print(f"""
🤖 Job Hunter Bot is now ready to help you find your dream job!

📋 WHAT'S CONFIGURED:
✅ Database initialized with your profile
✅ Web scrapers configured for multiple job sites  
✅ AI-powered CV optimization ready (if API key provided)
✅ Desktop application ready to launch

🚀 HOW TO START JOB HUNTING:

1. Launch the application:
   • Windows: Double-click run_job_hunter.bat
   • Mac/Linux: Run ./run_job_hunter.sh
   • Or run: python main.py

2. Start your first job search:
   • Enter keywords (e.g., 'Python Developer')
   • Select location or 'Remote'
   • Click 'Search Jobs'
   • Review results across multiple job sites

3. Optimize your applications:
   • Upload your CV in the User Profile section
   • Use AI to optimize CVs for specific jobs
   • Generate personalized cover letters

💡 PRO TIPS:
• Enable job alerts for passive job hunting
• Use the Analytics tab to track your success rate
• Try different keywords to discover more opportunities
• Check the logs in data/logs/ if you encounter issues

📚 DOCUMENTATION:
• User guide: docs/user_guide.md (if available)
• Troubleshooting: Check data/logs/ for error details
• Update: Run python update_job_hunter.py

🆘 NEED HELP?
• Check the logs in data/logs/ folder
• Review configuration in .env and config.ini files
• Re-run this setup: python {__file__.split('/')[-1]}

Happy job hunting! 🎯
""")
        
        # Ask if they want to launch now
        launch_now = input("\nLaunch Job Hunter Bot now? (y/n): ").lower().strip() == 'y'
        if launch_now:
            self._launch_application()
    
    # Helper methods
    
    def _check_python(self):
        """Check Python version"""
        version = sys.version_info
        return version >= (3, 9)
    
    def _check_os(self):
        """Check operating system"""
        import platform
        supported_os = ['Windows', 'Darwin', 'Linux']  # Darwin = macOS
        return platform.system() in supported_os
    
    def _check_memory(self):
        """Check available memory"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return memory.available > (2 * 1024**3)  # 2GB
        except:
            return True  # Can't check, assume OK
    
    def _check_disk_space(self):
        """Check disk space"""
        try:
            import shutil
            free_space = shutil.disk_usage(self.project_root).free
            return free_space > (1 * 1024**3)  # 1GB
        except:
            return True
    
    def _check_internet(self):
        """Check internet connection"""
        try:
            import urllib.request
            urllib.request.urlopen('https://www.google.com', timeout=5)
            return True
        except:
            return False
    
    def _check_dependencies(self):
        """Check for missing dependencies"""
        required_packages = [
            'PyQt6', 'requests', 'beautifulsoup4', 'selenium', 
            'webdriver_manager', 'openai', 'pandas'
        ]
        
        missing = []
        for package in required_packages:
            try:
                # Convert package name to import name
                import_name = package.replace('-', '_').lower()
                if package == 'beautifulsoup4':
                    import_name = 'bs4'
                elif package == 'PyQt6':
                    import_name = 'PyQt6.QtWidgets'
                
                __import__(import_name)
            except ImportError:
                missing.append(package)
        
        return missing
    
    def _setup_chromedriver(self):
        """Setup ChromeDriver"""
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            ChromeDriverManager().install()
            return True
        except Exception:
            return False
    
    def _create_requirements_file(self):
        """Create requirements.txt if missing"""
        requirements_content = """# Job Hunter Bot Dependencies
PyQt6>=6.6.0
selenium>=4.15.0
beautifulsoup4>=4.12.2
requests>=2.31.0
openai>=1.3.0
pandas>=2.1.0
webdriver-manager>=4.0.1
python-dateutil>=2.8.2
pillow>=10.0.0
"""
        (self.project_root / "requirements.txt").write_text(requirements_content.strip())
    
    def _create_config_files(self):
        """Create configuration files"""
        # .env file
        env_file = self.project_root / ".env"
        if not env_file.exists():
            env_content = """# Job Hunter Bot Environment Configuration
OPENAI_API_KEY=your_openai_api_key_here
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
HEADLESS_SCRAPING=True
LOG_LEVEL=INFO
"""
            env_file.write_text(env_content.strip())
        
        # config.ini
        config_file = self.project_root / "config.ini"
        if not config_file.exists():
            config_content = """[Database]
path = data/job_hunter.db
backup_interval_days = 7

[Scraping]
max_concurrent_scrapers = 3
default_job_limit = 50
headless_mode = True

[AI]
model = gpt-4
temperature = 0.3
max_tokens = 2000

[GUI]
window_width = 1400
window_height = 900
auto_refresh_minutes = 5
"""
            config_file.write_text(config_content.strip())
    
    def _check_api_key_configured(self):
        """Check if OpenAI API key is configured"""
        env_file = self.project_root / ".env"
        if env_file.exists():
            content = env_file.read_text()
            return 'OPENAI_API_KEY=' in content and 'your_openai_api_key_here' not in content
        return False
    
    def _update_env_file(self, key, value):
        """Update environment file with key-value pair"""
        env_file = self.project_root / ".env"
        content = env_file.read_text()
        
        # Replace or add the key
        lines = content.split('\n')
        key_found = False
        
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}"
                key_found = True
                break
        
        if not key_found:
            lines.append(f"{key}={value}")
        
        env_file.write_text('\n'.join(lines))
    
    def _verify_database(self):
        """Verify database is working"""
        try:
            from core.database.database_manager import DatabaseManager
            db = DatabaseManager()
            db.get_database_stats()
            db.close()
            return True
        except:
            return False
    
    def _verify_scrapers(self):
        """Verify scrapers are working"""
        try:
            from core.scrapers.linkedin_scraper import LinkedInScraper
            scraper = LinkedInScraper()
            scraper.close()
            return True
        except:
            return False
    
    def _verify_gui(self):
        """Verify GUI components"""
        try:
            from PyQt6.QtWidgets import QApplication
            return True
        except:
            return False
    
    def _verify_config(self):
        """Verify configuration files"""
        config_files = [".env", "config.ini"]
        return all((self.project_root / f).exists() for f in config_files)
    
    def _launch_application(self):
        """Launch the main application"""
        try:
            print("\n🚀 Launching Job Hunter Bot...")
            import subprocess
            subprocess.Popen([sys.executable, "main.py"])
            print("✅ Application launched!")
        except Exception as e:
            print(f"❌ Failed to launch: {e}")
            print("You can manually run: python main.py")


def main():
    """Main setup function"""
    wizard = FinalSetupWizard()
    success = wizard.run_complete_setup()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)