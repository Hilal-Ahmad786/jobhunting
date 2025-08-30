#!/usr/bin/env python3
"""
Job Hunter Bot - Enhanced Main Window
"""

import sys
import logging
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

class JobSearchWidget(QWidget):
    """Job search controls"""
    
    search_requested = pyqtSignal(str, str)  # keywords, location
    
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # Search inputs
        search_layout = QHBoxLayout()
        
        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("Enter job keywords (e.g., 'Python Developer')")
        search_layout.addWidget(QLabel("Keywords:"))
        search_layout.addWidget(self.keywords_input)
        
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Location or 'Remote'")
        search_layout.addWidget(QLabel("Location:"))
        search_layout.addWidget(self.location_input)
        
        search_btn = QPushButton("Search Jobs")
        search_btn.clicked.connect(self.start_search)
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)
    
    def start_search(self):
        keywords = self.keywords_input.text().strip()
        location = self.location_input.text().strip()
        
        if not keywords:
            QMessageBox.warning(self, "Invalid Input", "Please enter job keywords!")
            return
        
        self.search_requested.emit(keywords, location)

class JobTableWidget(QTableWidget):
    """Job listing table"""
    
    def __init__(self):
        super().__init__()
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(["Title", "Company", "Location", "Source", "Posted", "Actions"])
        
        # Table appearance
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Column sizing
        header = self.horizontalHeader()
        header.setStretchLastSection(True)

class MainWindow(QMainWindow):
    """Enhanced main window with real job search functionality"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.setup_ui()
        
        # Initialize backend systems
        self.db_manager = None
        self.scraper_manager = None
        self.cv_optimizer = None
        self.init_backend()
    
    def setup_ui(self):
        self.setWindowTitle("Job Hunter Bot - AI-Powered Career Assistant")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Job Hunter Bot")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 32px; font-weight: bold; margin: 20px; color: #2c3e50;")
        main_layout.addWidget(title)
        
        # Search widget
        self.search_widget = JobSearchWidget()
        self.search_widget.search_requested.connect(self.search_jobs)
        main_layout.addWidget(self.search_widget)
        
        # Status and progress
        self.status_label = QLabel("Ready to search for jobs...")
        main_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Job results tabs
        self.tab_widget = QTabWidget()
        
        # All Jobs tab
        self.all_jobs_table = JobTableWidget()
        self.tab_widget.addTab(self.all_jobs_table, "All Jobs")
        
        # IT Jobs tab
        self.it_jobs_table = JobTableWidget()
        self.tab_widget.addTab(self.it_jobs_table, "IT/Programming")
        
        # Civil Engineering tab
        self.civil_jobs_table = JobTableWidget()
        self.tab_widget.addTab(self.civil_jobs_table, "Civil Engineering")
        
        # Freelance tab
        self.freelance_jobs_table = JobTableWidget()
        self.tab_widget.addTab(self.freelance_jobs_table, "Freelance")
        
        main_layout.addWidget(self.tab_widget)
        
        # Menu setup
        self.setup_menus()
    
    def setup_menus(self):
        """Setup application menus"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        cv_action = QAction("CV Optimizer", self)
        cv_action.triggered.connect(self.open_cv_optimizer)
        tools_menu.addAction(cv_action)
    
    def init_backend(self):
        """Initialize backend systems"""
        try:
            from core.database.database_manager import DatabaseManager
            self.db_manager = DatabaseManager()
            
            # Try to initialize CV optimizer if API key available
            try:
                import os
                api_key = os.getenv('OPENAI_API_KEY')
                if api_key:
                    from core.ai.cv_optimizer import CVOptimizer
                    self.cv_optimizer = CVOptimizer(api_key)
                    self.status_label.setText("Backend systems initialized with AI support")
                else:
                    self.status_label.setText("Backend systems initialized - Add OpenAI key for AI features")
            except Exception as e:
                self.status_label.setText("Backend systems initialized - AI features unavailable")
            
            self.logger.info("Backend systems ready")
            
        except Exception as e:
            self.status_label.setText(f"Backend initialization failed: {e}")
            self.logger.error(f"Backend init failed: {e}")
    
    def search_jobs(self, keywords, location):
        """Search for jobs using real scrapers"""
        if not self.db_manager:
            QMessageBox.critical(self, "Error", "Database not initialized")
            return
        
        try:
            self.status_label.setText(f"Searching for '{keywords}' jobs...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(20)
            
            # Import and use real scrapers
            from core.scrapers.linkedin_scraper import LinkedInScraper
            from core.scrapers.indeed_scraper import IndeedScraper
            
            all_jobs = []
            
            # LinkedIn search
            self.status_label.setText("Searching LinkedIn...")
            self.progress_bar.setValue(40)
            
            linkedin_scraper = LinkedInScraper()
            linkedin_jobs = linkedin_scraper.scrape_jobs(keywords, location, 25)
            all_jobs.extend(linkedin_jobs)
            linkedin_scraper.close()
            
            # Indeed search
            self.status_label.setText("Searching Indeed...")
            self.progress_bar.setValue(60)
            
            indeed_scraper = IndeedScraper()
            indeed_jobs = indeed_scraper.scrape_jobs(keywords, location, 25)
            all_jobs.extend(indeed_jobs)
            indeed_scraper.close()
            
            # Save jobs to database
            self.progress_bar.setValue(80)
            saved_count = 0
            for job in all_jobs:
                try:
                    self.db_manager.save_job(job)
                    saved_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to save job: {e}")
            
            # Update display
            self.progress_bar.setValue(100)
            self.refresh_all_tables()
            self.progress_bar.setVisible(False)
            
            self.status_label.setText(f"Found {len(all_jobs)} jobs, saved {saved_count} to database")
            
            if saved_count > 0:
                QMessageBox.information(self, "Search Complete", 
                                      f"Search successful!\n\n"
                                      f"Found: {len(all_jobs)} jobs\n"
                                      f"Saved: {saved_count} to database\n"
                                      f"Keywords: {keywords}\n"
                                      f"Location: {location or 'Any'}")
            
        except ImportError as e:
            self.progress_bar.setVisible(False)
            self.status_label.setText("Scraper modules not found")
            QMessageBox.critical(self, "Import Error", f"Scraper implementation missing:\n{e}")
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.status_label.setText(f"Search error: {str(e)}")
            QMessageBox.critical(self, "Search Error", f"Job search failed:\n{str(e)}")
    
    def refresh_all_tables(self):
        """Refresh all job tables"""
        if not self.db_manager:
            return
        
        try:
            from core.database.models import JobType
            
            # Get jobs by type
            all_jobs = self.db_manager.get_jobs(limit=200)
            it_jobs = self.db_manager.get_jobs(JobType.IT_PROGRAMMING, limit=100)
            civil_jobs = self.db_manager.get_jobs(JobType.CIVIL_ENGINEERING, limit=100)
            freelance_jobs = self.db_manager.get_jobs(JobType.FREELANCE, limit=100)
            
            # Populate tables
            self.populate_table(self.all_jobs_table, all_jobs)
            self.populate_table(self.it_jobs_table, it_jobs)
            self.populate_table(self.civil_jobs_table, civil_jobs)
            self.populate_table(self.freelance_jobs_table, freelance_jobs)
            
        except Exception as e:
            self.logger.error(f"Error refreshing tables: {e}")
    
    def populate_table(self, table, jobs):
        """Populate table with job data"""
        table.setRowCount(len(jobs))
        
        for row, job in enumerate(jobs):
            table.setItem(row, 0, QTableWidgetItem(job.title))
            table.setItem(row, 1, QTableWidgetItem(job.company.name))
            table.setItem(row, 2, QTableWidgetItem(str(job.location)))
            table.setItem(row, 3, QTableWidgetItem(job.source))
            table.setItem(row, 4, QTableWidgetItem(job.posted_date.strftime('%Y-%m-%d') if job.posted_date else 'Unknown'))
            
            # Action button
            action_btn = QPushButton("View")
            action_btn.clicked.connect(lambda checked, url=job.url: self.open_job_url(url))
            table.setCellWidget(row, 5, action_btn)
    
    def open_job_url(self, url):
        """Open job URL in browser"""
        import webbrowser
        if url:
            webbrowser.open(url)
    
    def open_settings(self):
        """Open settings dialog"""
        QMessageBox.information(self, "Settings", "Settings dialog - Add your OpenAI API key in .env file")
    
    def open_cv_optimizer(self):
        """Open CV optimizer"""
        if not self.cv_optimizer:
            QMessageBox.information(self, "CV Optimizer", "Add your OpenAI API key to .env file to enable CV optimization")
            return
        
        QMessageBox.information(self, "CV Optimizer", "CV optimization is available! This would open the optimizer dialog.")
    
    def closeEvent(self, event):
        """Clean shutdown"""
        if self.db_manager:
            self.db_manager.close()
        event.accept()

def create_application():
    """Create QApplication"""
    app = QApplication(sys.argv)
    app.setApplicationName("Job Hunter Bot")
    app.setApplicationVersion("1.0.0")
    
    # Styling
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f8f9fa;
        }
        QTabWidget::pane {
            border: 1px solid #dee2e6;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #e9ecef;
            border: 1px solid #dee2e6;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #007bff;
            color: white;
        }
        QPushButton {
            padding: 8px 16px;
            font-size: 14px;
            border: 1px solid #007bff;
            border-radius: 4px;
            background-color: #007bff;
            color: white;
        }
        QPushButton:hover {
            background-color: #0056b3;
        }
        QLineEdit {
            padding: 8px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 14px;
        }
        QTableWidget {
            gridline-color: #dee2e6;
            background-color: white;
        }
    """)
    
    return app

def setup_logging():
    """Setup application logging"""
    import os
    os.makedirs("data/logs", exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("data/logs/job_hunter.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

if __name__ == "__main__":
    app = create_application()
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
