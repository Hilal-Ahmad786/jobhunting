#!/usr/bin/env python3
"""
Smart Application Launcher for Job Hunter Bot
Handles all startup checks and initialization
"""

import sys
import os
import logging
import subprocess
from pathlib import Path
import importlib.util


class JobHunterLauncher:
    """Smart launcher that handles all startup requirements"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.logger = None
        self.setup_basic_logging()
    
    def setup_basic_logging(self):
        """Setup basic logging before full initialization"""
        log_dir = self.project_root / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "launcher.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def launch_application(self):
        """Main launcher method"""
        print("🤖 Job Hunter Bot - Smart Launcher")
        print("=" * 50)
        
        try:
            # Pre-flight checks
            if not self.run_preflight_checks():
                return False
            
            # Launch main application
            return self.start_main_application()
            
        except KeyboardInterrupt:
            print("\n⏹️ Launch cancelled by user")
            return False
        except Exception as e:
            self.logger.error(f"Launch failed: {e}")
            print(f"❌ Launch failed: {e}")
            return False
    
    def run_preflight_checks(self):
        """Run all pre-flight checks"""
        checks = [
            ("Python Version", self.check_python_version),
            ("Project Structure", self.check_project_structure),
            ("Dependencies", self.check_dependencies),
            ("Database", self.check_database),
            ("Configuration", self.check_configuration)
        ]
        
        print("🔍 Running pre-flight checks...")
        
        for check_name, check_func in checks:
            print(f"  Checking {check_name}...", end=" ")
            try:
                if check_func():
                    print("✅")
                else:
                    print("❌")
                    return False
            except Exception as e:
                print(f"❌ ({e})")
                return False
        
        print("✅ All pre-flight checks passed!")
        return True
    
    def check_python_version(self):
        """Check Python version compatibility"""
        version = sys.version_info
        if version < (3, 9):
            print(f"\n❌ Python 3.9+ required, found {version.major}.{version.minor}")
            print("Please upgrade Python: https://www.python.org/downloads/")
            return False
        return True
    
    def check_project_structure(self):
        """Check project directory structure"""
        required_dirs = [
            "core", "core/database", "core/scrapers", "core/ai",
            "gui", "data", "data/logs"
        ]
        
        for directory in required_dirs:
            if not (self.project_root / directory).exists():
                print(f"\n❌ Missing directory: {directory}")
                return False
        
        # Create __init__.py files if missing
        init_files = [
            "core/__init__.py", "core/database/__init__.py", 
            "core/scrapers/__init__.py", "core/ai/__init__.py", "gui/__init__.py"
        ]
        
        for init_file in init_files:
            init_path = self.project_root / init_file
            if not init_path.exists():
                init_path.touch()
        
        return True
    
    def check_dependencies(self):
        """Check critical dependencies"""
        critical_deps = [
            ('PyQt6', 'PyQt6.QtWidgets'),
            ('requests', 'requests'),
            ('beautifulsoup4', 'bs4'),
            ('selenium', 'selenium'),
            ('openai', 'openai'),
            ('pandas', 'pandas')
        ]
        
        missing = []
        for package_name, import_name in critical_deps:
            try:
                importlib.import_module(import_name)
            except ImportError:
                missing.append(package_name)
        
        if missing:
            print(f"\n❌ Missing dependencies: {', '.join(missing)}")
            print("Install with: pip install -r requirements.txt")
            
            # Offer to install automatically
            response = input("Install missing dependencies now? (y/n): ").lower().strip()
            if response == 'y':
                return self.install_dependencies()
            return False
        
        return True
    
    def install_dependencies(self):
        """Install missing dependencies"""
        try:
            print("📦 Installing dependencies...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ])
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
    
    def check_database(self):
        """Check database connectivity"""
        try:
            # Add project to path
            sys.path.insert(0, str(self.project_root))
            
            # Try to create database manager
            from core.database.database_manager import DatabaseManager
            db = DatabaseManager()
            db.close()
            return True
        except ImportError:
            print(f"\n❌ Database module not found")
            return False
        except Exception as e:
            print(f"\n❌ Database check failed: {e}")
            return False
    
    def check_configuration(self):
        """Check configuration files"""
        config_files = ["config.ini"]
        
        for config_file in config_files:
            config_path = self.project_root / config_file
            if not config_path.exists():
                self.create_default_config(config_path)
        
        # Check .env file
        env_path = self.project_root / ".env"
        if not env_path.exists():
            env_example = self.project_root / ".env.example"
            if env_example.exists():
                # Copy example to .env
                env_path.write_text(env_example.read_text())
            else:
                # Create basic .env
                self.create_default_env(env_path)
        
        return True
    
    def create_default_config(self, config_path):
        """Create default configuration file"""
        default_config = """[Database]
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
        config_path.write_text(default_config)
        self.logger.info(f"Created default config: {config_path}")
    
    def create_default_env(self, env_path):
        """Create default environment file"""
        default_env = """# Job Hunter Bot Environment Configuration
OPENAI_API_KEY=your_openai_api_key_here
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
HEADLESS_SCRAPING=True
LOG_LEVEL=INFO
"""
        env_path.write_text(default_env)
        self.logger.info(f"Created default .env: {env_path}")
    
    def start_main_application(self):
        """Start the main Job Hunter Bot application"""
        print("\n🚀 Starting Job Hunter Bot...")
        
        try:
            # Add project to path
            sys.path.insert(0, str(self.project_root))
            
            # Import and run main application
            from main import main as run_main_app
            return run_main_app()
            
        except ImportError as e:
            print(f"❌ Failed to import main application: {e}")
            print("Please ensure main.py exists and is properly configured")
            return False
        except Exception as e:
            print(f"❌ Application failed to start: {e}")
            self.logger.error(f"Application start failed: {e}", exc_info=True)
            return False
    
    def show_help(self):
        """Show help information"""
        help_text = """
🤖 Job Hunter Bot - Smart Launcher Help

USAGE:
  python smart_launcher.py [options]

OPTIONS:
  --help, -h      Show this help message
  --check-only    Run checks without starting the application
  --install-deps  Install missing dependencies
  --reset-config  Reset configuration to defaults

TROUBLESHOOTING:
  1. If dependencies are missing:
     pip install -r requirements.txt
     
  2. If database issues occur:
     Delete data/job_hunter.db to reset database
     
  3. If GUI doesn't start:
     Check that PyQt6 is properly installed
     
  4. For AI features:
     Add your OpenAI API key to .env file

DOCUMENTATION:
  - User Guide: docs/user_guide.md
  - API Reference: docs/api_reference.md
  - Troubleshooting: docs/troubleshooting.md

For more help, visit: https://github.com/your-repo/job-hunter-bot
"""
        print(help_text)
    
    def reset_configuration(self):
        """Reset configuration to defaults"""
        print("🔄 Resetting configuration...")
        
        # Reset config files
        config_files = [
            ("config.ini", self.create_default_config),
            (".env", self.create_default_env)
        ]
        
        for filename, creator_func in config_files:
            file_path = self.project_root / filename
            if file_path.exists():
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                file_path.rename(backup_path)
                print(f"  Backed up {filename} to {backup_path.name}")
            
            creator_func(file_path)
            print(f"  Created default {filename}")
        
        print("✅ Configuration reset complete")


def main():
    """Main launcher function"""
    launcher = JobHunterLauncher()
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ['--help', '-h']:
            launcher.show_help()
            return 0
        elif arg == '--check-only':
            success = launcher.run_preflight_checks()
            return 0 if success else 1
        elif arg == '--install-deps':
            success = launcher.install_dependencies()
            return 0 if success else 1
        elif arg == '--reset-config':
            launcher.reset_configuration()
            return 0
        else:
            print(f"Unknown option: {arg}")
            launcher.show_help()
            return 1
    
    # Normal launch
    success = launcher.launch_application()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)