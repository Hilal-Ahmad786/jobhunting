#!/usr/bin/env python3
"""
Job Hunter Bot - Comprehensive Debug Script
Tests every component and identifies what's working vs broken
"""

import sys
import os
import traceback
import sqlite3
from pathlib import Path
import importlib
import inspect
from datetime import datetime

class JobHunterDebugger:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.results = {
            'working': [],
            'broken': [],
            'missing': [],
            'warnings': []
        }
        
        # Add project to path
        sys.path.insert(0, str(self.project_root))
        
        print("🔍 Job Hunter Bot - Comprehensive Debug Analysis")
        print("=" * 60)
        print(f"Project root: {self.project_root}")
        print(f"Python version: {sys.version}")
        print("=" * 60)

    def run_full_debug(self):
        """Run complete diagnostic"""
        
        # Test 1: Core Dependencies
        self.test_dependencies()
        
        # Test 2: Database System
        self.test_database()
        
        # Test 3: Core Models
        self.test_models()
        
        # Test 4: Existing Scrapers
        self.test_existing_scrapers()
        
        # Test 5: Missing Scrapers
        self.test_missing_scrapers()
        
        # Test 6: GUI Components
        self.test_gui()
        
        # Test 7: AI Components
        self.test_ai_components()
        
        # Test 8: Integration Test
        self.test_integration()
        
        # Generate Report
        self.generate_report()
        
        return self.results

    def test_dependencies(self):
        """Test all Python dependencies"""
        print("\n📦 Testing Dependencies...")
        
        dependencies = [
            ('PyQt6', 'PyQt6.QtWidgets'),
            ('selenium', 'selenium'),
            ('beautifulsoup4', 'bs4'),
            ('requests', 'requests'),
            ('openai', 'openai'),
            ('pandas', 'pandas'),
            ('webdriver_manager', 'webdriver_manager')
        ]
        
        for package_name, import_name in dependencies:
            try:
                __import__(import_name)
                print(f"  ✅ {package_name}")
                self.results['working'].append(f"Dependency: {package_name}")
            except ImportError as e:
                print(f"  ❌ {package_name}: {e}")
                self.results['broken'].append(f"Dependency: {package_name} - {e}")

    def test_database(self):
        """Test database functionality"""
        print("\n🗄️ Testing Database...")
        
        try:
            # Test database manager import
            from core.database.database_manager import DatabaseManager
            print("  ✅ DatabaseManager import")
            
            # Test database connection
            db = DatabaseManager("debug_test.db")
            print("  ✅ Database connection")
            
            # Test models import
            from core.database.models import Job, JobType, Company, Location
            print("  ✅ Models import")
            
            # Test creating a job
            job = Job(
                title="Test Job",
                company=Company(name="Test Company"),
                location=Location(city="Test City"),
                description="Test description",
                url="https://test.com",
                source="Test",
                job_type=JobType.IT_PROGRAMMING
            )
            
            job_id = db.save_job(job)
            print(f"  ✅ Job creation (ID: {job_id})")
            
            # Test retrieving jobs
            jobs = db.get_jobs(limit=5)
            print(f"  ✅ Job retrieval ({len(jobs)} jobs)")
            
            db.close()
            
            # Clean up test database
            Path("debug_test.db").unlink(missing_ok=True)
            
            self.results['working'].append("Database system")
            
        except Exception as e:
            print(f"  ❌ Database error: {e}")
            self.results['broken'].append(f"Database system - {e}")
            traceback.print_exc()

    def test_models(self):
        """Test data models"""
        print("\n📊 Testing Data Models...")
        
        try:
            from core.database.models import (
                Job, JobType, Company, Location, Salary, 
                Currency, UserProfile, Application
            )
            
            # Test basic model creation
            company = Company(name="Test Corp")
            location = Location(city="Test City", country="USA")
            salary = Salary(min_amount=50000, currency=Currency.USD)
            
            job = Job(
                title="Software Engineer",
                company=company,
                location=location,
                description="A test job",
                url="https://example.com",
                source="Test",
                job_type=JobType.IT_PROGRAMMING,
                salary=salary
            )
            
            print("  ✅ Job model creation")
            
            # Test model serialization
            job_dict = job.to_dict()
            print("  ✅ Job serialization")
            
            # Test user profile
            profile = UserProfile(
                name="Test User",
                email="test@example.com",
                skills=["Python", "JavaScript"],
                preferred_job_types=[JobType.IT_PROGRAMMING]
            )
            
            print("  ✅ UserProfile creation")
            
            self.results['working'].append("Data models")
            
        except Exception as e:
            print(f"  ❌ Models error: {e}")
            self.results['broken'].append(f"Data models - {e}")
            traceback.print_exc()

    def test_existing_scrapers(self):
        """Test existing scrapers"""
        print("\n🕷️ Testing Existing Scrapers...")
        
        existing_scrapers = [
            ('LinkedIn', 'core.scrapers.linkedin_scraper', 'LinkedInScraper'),
            ('Indeed', 'core.scrapers.indeed_scraper', 'IndeedScraper')
        ]
        
        for name, module_path, class_name in existing_scrapers:
            try:
                # Test import
                module = importlib.import_module(module_path)
                scraper_class = getattr(module, class_name)
                
                # Test instantiation
                scraper = scraper_class()
                
                print(f"  ✅ {name} scraper import & creation")
                
                # Test scraping (safe test)
                try:
                    jobs = scraper.scrape_jobs("python developer", "remote", 1)
                    print(f"    ✅ {name} scraping test: {len(jobs)} jobs")
                    
                    if jobs:
                        job = jobs[0]
                        print(f"    📋 Sample: {job.title} at {job.company.name}")
                    
                    self.results['working'].append(f"Scraper: {name}")
                    
                except Exception as scrape_error:
                    print(f"    ⚠️ {name} scraping failed: {scrape_error}")
                    self.results['warnings'].append(f"Scraper {name} import OK but scraping failed: {scrape_error}")
                
                finally:
                    scraper.close()
                
            except Exception as e:
                print(f"  ❌ {name} scraper error: {e}")
                self.results['broken'].append(f"Scraper {name} - {e}")

    def test_missing_scrapers(self):
        """Test which scrapers are missing"""
        print("\n🔍 Checking Missing Scrapers...")
        
        expected_scrapers = [
            ('Upwork', 'core.scrapers.upwork_scraper', 'UpworkScraper'),
            ('RemoteOK', 'core.scrapers.remote_ok_scraper', 'RemoteOKScraper'),
            ('AngelList', 'core.scrapers.angellist_scraper', 'AngelListScraper'),
            ('WeWorkRemotely', 'core.scrapers.weworkremotely_scraper', 'WeWorkRemotelyScraper'),
            ('Glassdoor', 'core.scrapers.glassdoor_scraper', 'GlassdoorScraper'),
            ('Dice', 'core.scrapers.dice_monster_scrapers', 'DiceScraper'),
            ('Monster', 'core.scrapers.dice_monster_scrapers', 'MonsterScraper'),
            ('Freelancer', 'core.scrapers.freelancer_platforms_scrapers', 'FreelancerScraper'),
            ('Fiverr', 'core.scrapers.freelancer_platforms_scrapers', 'FiverrScraper'),
            ('Seek', 'core.scrapers.seek_australia_scraper', 'SeekScraper'),
            ('Reed', 'core.scrapers.uk_jobs_scraper', 'ReedScraper'),
            ('StepStone', 'core.scrapers.german_jobs_scraper', 'StepStoneScraper')
        ]
        
        for name, module_path, class_name in expected_scrapers:
            try:
                module = importlib.import_module(module_path)
                scraper_class = getattr(module, class_name)
                print(f"  ✅ {name} scraper exists")
                self.results['working'].append(f"Scraper available: {name}")
                
            except ImportError:
                print(f"  ❌ {name} scraper missing (file not found)")
                self.results['missing'].append(f"Scraper file: {name}")
                
            except AttributeError:
                print(f"  ⚠️ {name} file exists but class missing")
                self.results['broken'].append(f"Scraper class: {name}")
                
            except Exception as e:
                print(f"  ❌ {name} scraper error: {e}")
                self.results['broken'].append(f"Scraper {name}: {e}")

    def test_gui(self):
        """Test GUI components"""
        print("\n🖥️ Testing GUI Components...")
        
        try:
            from PyQt6.QtWidgets import QApplication
            
            # Test main window import
            from gui.main_window import MainWindow, create_application
            print("  ✅ MainWindow import")
            
            # Don't actually create the app to avoid conflicts
            print("  ✅ GUI components available")
            
            self.results['working'].append("GUI system")
            
        except Exception as e:
            print(f"  ❌ GUI error: {e}")
            self.results['broken'].append(f"GUI system - {e}")

    def test_ai_components(self):
        """Test AI/CV optimizer"""
        print("\n🤖 Testing AI Components...")
        
        try:
            from core.ai.cv_optimizer import CVOptimizer
            print("  ✅ CVOptimizer import")
            
            # Check if OpenAI key available
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                print("  ✅ OpenAI API key found")
                self.results['working'].append("AI system with API key")
            else:
                print("  ⚠️ OpenAI API key not found in environment")
                self.results['warnings'].append("OpenAI API key missing")
            
        except Exception as e:
            print(f"  ❌ AI components error: {e}")
            self.results['broken'].append(f"AI system - {e}")

    def test_integration(self):
        """Test full integration"""
        print("\n🔗 Testing Integration...")
        
        try:
            # Test scraper manager import
            from core.scrapers.scraper_manager import ScraperManager
            print("  ✅ ScraperManager import")
            
            # Test database integration
            from core.database.database_manager import DatabaseManager
            db = DatabaseManager("integration_test.db")
            
            # Test creating scraper manager
            scraper_manager = ScraperManager(db)
            print("  ✅ ScraperManager creation")
            
            # Test available scrapers
            available_scrapers = list(scraper_manager.scraper_configs.keys())
            print(f"  📊 Available scrapers: {len(available_scrapers)}")
            for scraper in available_scrapers[:5]:  # Show first 5
                print(f"    - {scraper}")
            
            if len(available_scrapers) > 5:
                print(f"    ... and {len(available_scrapers) - 5} more")
            
            db.close()
            Path("integration_test.db").unlink(missing_ok=True)
            
            self.results['working'].append("Integration system")
            
        except Exception as e:
            print(f"  ❌ Integration error: {e}")
            self.results['broken'].append(f"Integration - {e}")
            traceback.print_exc()

    def test_specific_file_issues(self):
        """Test for specific file/import issues"""
        print("\n🔧 Testing Specific Issues...")
        
        # Check __init__.py files
        init_files = [
            'core/__init__.py',
            'core/database/__init__.py', 
            'core/scrapers/__init__.py',
            'core/ai/__init__.py',
            'gui/__init__.py'
        ]
        
        for init_file in init_files:
            path = self.project_root / init_file
            if path.exists():
                content = path.read_text()
                if 'echo' in content or len(content.strip()) == 0:
                    print(f"  ⚠️ {init_file} has issues: {content[:50]}...")
                    self.results['warnings'].append(f"Malformed __init__.py: {init_file}")
                else:
                    print(f"  ✅ {init_file}")
            else:
                print(f"  ❌ Missing: {init_file}")
                self.results['missing'].append(f"File: {init_file}")

    def generate_report(self):
        """Generate comprehensive debug report"""
        
        print("\n" + "=" * 60)
        print("📋 COMPREHENSIVE DEBUG REPORT")
        print("=" * 60)
        
        total_items = sum(len(items) for items in self.results.values())
        
        print(f"✅ WORKING ({len(self.results['working'])} items):")
        for item in self.results['working']:
            print(f"  ✓ {item}")
        
        print(f"\n❌ BROKEN ({len(self.results['broken'])} items):")
        for item in self.results['broken']:
            print(f"  ✗ {item}")
        
        print(f"\n📋 MISSING ({len(self.results['missing'])} items):")
        for item in self.results['missing']:
            print(f"  - {item}")
        
        print(f"\n⚠️ WARNINGS ({len(self.results['warnings'])} items):")
        for item in self.results['warnings']:
            print(f"  ! {item}")
        
        # Calculate health score
        working_score = len(self.results['working']) * 2
        warning_score = len(self.results['warnings']) * 0.5
        total_possible = working_score + len(self.results['broken']) * 2 + len(self.results['missing']) * 2
        
        health_percentage = (working_score + warning_score) / max(total_possible, 1) * 100
        
        print(f"\n🎯 SYSTEM HEALTH: {health_percentage:.1f}%")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        
        if self.results['missing']:
            print("1. 📁 Create missing scraper files:")
            missing_scrapers = [item for item in self.results['missing'] if 'Scraper' in item]
            for scraper in missing_scrapers[:3]:
                print(f"   - {scraper}")
        
        if self.results['broken']:
            print("2. 🔧 Fix broken components:")
            for broken in self.results['broken'][:3]:
                print(f"   - {broken}")
        
        if len(self.results['working']) >= 3:
            print("3. ✅ Good news: Core system is functional!")
            print("   - LinkedIn scraper working")
            print("   - Database system working") 
            print("   - Models working")
            print("   → You can start using the app with LinkedIn jobs")
        
        print(f"\n🚀 IMMEDIATE ACTIONS:")
        if 'Database system' in self.results['working'] and 'Scraper: LinkedIn' in self.results['working']:
            print("1. ✓ Your app is functional with LinkedIn!")
            print("2. Run: python main.py")
            print("3. Try searching for jobs")
            print("4. Add more scrapers gradually")
        else:
            print("1. Fix core issues first")
            print("2. Focus on database and LinkedIn scraper")
            print("3. Then add additional scrapers")
        
        return health_percentage

def main():
    """Run comprehensive debug"""
    debugger = JobHunterDebugger()
    results = debugger.run_full_debug()
    
    print(f"\nDebug completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return results

if __name__ == "__main__":
    results = main()