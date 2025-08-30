#!/usr/bin/env python3
"""
Database Manager for Job Hunter Bot

This module handles all database operations including:
- Creating and managing SQLite database
- CRUD operations for jobs, applications, and user profiles
- Data migrations and schema updates
- Query optimization and indexing
- Backup and recovery operations
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from pathlib import Path
import threading
from contextlib import contextmanager

# Import our data models
from core.database.models import (
    Job, Application, UserProfile, Analytics, SearchQuery,
    Company, Location, Salary, JobRequirements,
    JobType, ApplicationStatus, Currency
)


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class DatabaseManager:
    """
    Comprehensive database manager for Job Hunter Bot
    Handles all SQLite operations with thread safety and error handling
    """
    
    def __init__(self, db_path: str = "data/job_hunter.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread safety
        self._local = threading.local()
        self._lock = threading.RLock()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self.init_database()
        
    @contextmanager
    def get_connection(self):
        """Thread-safe database connection context manager"""
        with self._lock:
            if not hasattr(self._local, 'connection'):
                self._local.connection = sqlite3.connect(
                    str(self.db_path),
                    timeout=30.0,
                    check_same_thread=False
                )
                self._local.connection.row_factory = sqlite3.Row
                # Enable foreign keys
                self._local.connection.execute("PRAGMA foreign_keys = ON")
                
            try:
                yield self._local.connection
            except Exception as e:
                self._local.connection.rollback()
                self.logger.error(f"Database operation failed: {e}")
                raise DatabaseError(f"Database operation failed: {e}")
    
    def init_database(self):
        """Initialize database tables and indexes"""
        self.logger.info("Initializing database...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tables
            self._create_jobs_table(cursor)
            self._create_applications_table(cursor)
            self._create_user_profiles_table(cursor)
            self._create_analytics_table(cursor)
            self._create_search_history_table(cursor)
            self._create_settings_table(cursor)
            
            # Create indexes for performance
            self._create_indexes(cursor)
            
            conn.commit()
            self.logger.info("Database initialized successfully")
    
    def _create_jobs_table(self, cursor: sqlite3.Cursor):
        """Create jobs table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company_name TEXT NOT NULL,
                company_data TEXT,  -- JSON for full Company object
                location_data TEXT, -- JSON for full Location object
                description TEXT,
                url TEXT UNIQUE,
                source TEXT NOT NULL,
                job_type TEXT NOT NULL,
                employment_type TEXT DEFAULT 'full_time',
                salary_data TEXT,   -- JSON for Salary object
                requirements_data TEXT, -- JSON for JobRequirements object
                posted_date TEXT,
                application_deadline TEXT,
                scraped_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_bookmarked BOOLEAN DEFAULT FALSE,
                match_score REAL,
                notes TEXT DEFAULT '',
                extra_data TEXT,    -- JSON for additional metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_applications_table(self, cursor: sqlite3.Cursor):
        """Create applications table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                cv_version TEXT NOT NULL,
                cover_letter TEXT,
                portfolio_links TEXT, -- JSON array
                status TEXT NOT NULL DEFAULT 'draft',
                applied_date TEXT,
                response_date TEXT,
                communications TEXT,  -- JSON array of communication history
                interview_dates TEXT, -- JSON array of interview dates
                interview_notes TEXT,
                offer_details TEXT,   -- JSON for offer information
                rejection_reason TEXT,
                created_date TEXT NOT NULL,
                updated_date TEXT NOT NULL,
                FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
            )
        ''')
    
    def _create_user_profiles_table(self, cursor: sqlite3.Cursor):
        """Create user profiles table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                linkedin_url TEXT,
                portfolio_url TEXT,
                current_title TEXT,
                experience_years INTEGER DEFAULT 0,
                skills TEXT,          -- JSON array
                certifications TEXT,  -- JSON array
                education TEXT,       -- JSON array
                cv_templates TEXT,    -- JSON object {name: content}
                preferred_job_types TEXT, -- JSON array
                preferred_locations TEXT, -- JSON array
                salary_expectations TEXT, -- JSON object
                remote_preference TEXT DEFAULT 'hybrid',
                keywords_civil TEXT,     -- JSON array
                keywords_it TEXT,        -- JSON array
                keywords_freelance TEXT, -- JSON array
                auto_apply_enabled BOOLEAN DEFAULT FALSE,
                auto_apply_filters TEXT, -- JSON object
                email_notifications BOOLEAN DEFAULT TRUE,
                desktop_notifications BOOLEAN DEFAULT TRUE,
                notification_keywords TEXT, -- JSON array
                openai_api_key TEXT,
                other_api_keys TEXT,     -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_analytics_table(self, cursor: sqlite3.Cursor):
        """Create analytics tracking table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_jobs_found INTEGER DEFAULT 0,
                jobs_by_type TEXT,      -- JSON object
                jobs_by_source TEXT,    -- JSON object
                applications_sent INTEGER DEFAULT 0,
                responses_received INTEGER DEFAULT 0,
                interviews_scheduled INTEGER DEFAULT 0,
                offers_received INTEGER DEFAULT 0,
                response_rate REAL DEFAULT 0.0,
                interview_rate REAL DEFAULT 0.0,
                offer_rate REAL DEFAULT 0.0,
                avg_application_time REAL,
                avg_response_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_search_history_table(self, cursor: sqlite3.Cursor):
        """Create search history table"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_data TEXT NOT NULL,  -- JSON for SearchQuery object
                results_count INTEGER DEFAULT 0,
                execution_time REAL,      -- seconds
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_settings_table(self, cursor: sqlite3.Cursor):
        """Create settings table for app configuration"""
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    def _create_indexes(self, cursor: sqlite3.Cursor):
        """Create database indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_jobs_type ON jobs(job_type)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_scraped_date ON jobs(scraped_date)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_salary ON jobs(salary_data)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location_data)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_bookmarked ON jobs(is_bookmarked)",
            "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)",
            "CREATE INDEX IF NOT EXISTS idx_applications_job_id ON applications(job_id)",
            "CREATE INDEX IF NOT EXISTS idx_applications_date ON applications(applied_date)",
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
    
    # ===== JOB OPERATIONS =====
    
    def save_job(self, job: Job) -> int:
        """Save a single job to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if job already exists (by URL)
            cursor.execute("SELECT id FROM jobs WHERE url = ?", (job.url,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing job
                job.id = existing['id']
                return self._update_job(cursor, job)
            else:
                # Insert new job
                return self._insert_job(cursor, job)
    
    def _insert_job(self, cursor: sqlite3.Cursor, job: Job) -> int:
        """Insert new job into database"""
        cursor.execute('''
            INSERT INTO jobs (
                title, company_name, company_data, location_data, description, url,
                source, job_type, employment_type, salary_data, requirements_data,
                posted_date, application_deadline, scraped_date, is_bookmarked,
                match_score, notes, extra_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            job.title,
            job.company.name,
            json.dumps(job.company.to_dict()),
            json.dumps(job.location.to_dict()),
            job.description,
            job.url,
            job.source,
            job.job_type.value,
            job.employment_type,
            json.dumps(job.salary.to_dict()) if job.salary else None,
            json.dumps(job.requirements.to_dict()),
            job.posted_date.isoformat() if job.posted_date else None,
            job.application_deadline.isoformat() if job.application_deadline else None,
            job.scraped_date.isoformat(),
            job.is_bookmarked,
            job.match_score,
            job.notes,
            json.dumps(job.extra_data)
        ))
        
        job_id = cursor.lastrowid
        cursor.connection.commit()
        self.logger.info(f"Saved new job: {job.title} (ID: {job_id})")
        return job_id
    
    def _update_job(self, cursor: sqlite3.Cursor, job: Job) -> int:
        """Update existing job in database"""
        cursor.execute('''
            UPDATE jobs SET
                title = ?, company_name = ?, company_data = ?, location_data = ?,
                description = ?, salary_data = ?, requirements_data = ?,
                match_score = ?, notes = ?, extra_data = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            job.title,
            job.company.name,
            json.dumps(job.company.to_dict()),
            json.dumps(job.location.to_dict()),
            job.description,
            json.dumps(job.salary.to_dict()) if job.salary else None,
            json.dumps(job.requirements.to_dict()),
            job.match_score,
            job.notes,
            json.dumps(job.extra_data),
            job.id
        ))
        
        cursor.connection.commit()
        self.logger.info(f"Updated job: {job.title} (ID: {job.id})")
        return job.id
    
    def save_jobs_batch(self, jobs: List[Job]) -> List[int]:
        """Save multiple jobs efficiently"""
        job_ids = []
        with self.get_connection() as conn:
            for job in jobs:
                cursor = conn.cursor()
                job_id = self.save_job(job)
                job_ids.append(job_id)
        
        self.logger.info(f"Batch saved {len(jobs)} jobs")
        return job_ids
    
    def get_jobs(self, 
                 job_type: Optional[JobType] = None,
                 source: Optional[str] = None,
                 remote_only: bool = False,
                 bookmarked_only: bool = False,
                 limit: int = 100,
                 offset: int = 0) -> List[Job]:
        """Retrieve jobs with filtering options"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic query
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            
            if job_type:
                query += " AND job_type = ?"
                params.append(job_type.value)
            
            if source:
                query += " AND source = ?"
                params.append(source)
            
            if remote_only:
                query += " AND location_data LIKE '%\"is_remote\": true%'"
            
            if bookmarked_only:
                query += " AND is_bookmarked = 1"
            
            query += " ORDER BY scraped_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_job(row) for row in rows]
    
    def get_job_by_id(self, job_id: int) -> Optional[Job]:
        """Get specific job by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            
            return self._row_to_job(row) if row else None
    
    def _row_to_job(self, row: sqlite3.Row) -> Job:
        """Convert database row to Job object"""
        # Parse JSON data
        company_data = json.loads(row['company_data']) if row['company_data'] else {}
        location_data = json.loads(row['location_data']) if row['location_data'] else {}
        salary_data = json.loads(row['salary_data']) if row['salary_data'] else None
        requirements_data = json.loads(row['requirements_data']) if row['requirements_data'] else {}
        extra_data = json.loads(row['extra_data']) if row['extra_data'] else {}
        
        # Reconstruct objects
        company = Company(**company_data)
        location = Location(**location_data)
        salary = Salary.from_dict(salary_data) if salary_data else None
        requirements = JobRequirements(**requirements_data)
        
        return Job(
            id=row['id'],
            title=row['title'],
            company=company,
            location=location,
            description=row['description'],
            url=row['url'],
            source=row['source'],
            job_type=JobType(row['job_type']),
            employment_type=row['employment_type'],
            salary=salary,
            requirements=requirements,
            posted_date=datetime.fromisoformat(row['posted_date']) if row['posted_date'] else None,
            application_deadline=datetime.fromisoformat(row['application_deadline']) if row['application_deadline'] else None,
            scraped_date=datetime.fromisoformat(row['scraped_date']),
            is_bookmarked=bool(row['is_bookmarked']),
            match_score=row['match_score'],
            notes=row['notes'],
            extra_data=extra_data
        )
    
    def search_jobs(self, keywords: str, filters: Dict[str, Any] = None) -> List[Job]:
        """Full-text search for jobs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Basic text search
            search_query = f"%{keywords.lower()}%"
            
            query = '''
                SELECT * FROM jobs 
                WHERE (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(company_name) LIKE ?)
            '''
            params = [search_query, search_query, search_query]
            
            # Apply additional filters
            if filters:
                if filters.get('job_type'):
                    query += " AND job_type = ?"
                    params.append(filters['job_type'])
                
                if filters.get('remote_only'):
                    query += " AND location_data LIKE '%\"is_remote\": true%'"
                
                if filters.get('min_salary'):
                    query += " AND salary_data LIKE ?"
                    params.append(f'%"min_amount": {filters["min_salary"]}%')
            
            query += " ORDER BY match_score DESC, scraped_date DESC LIMIT 200"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_job(row) for row in rows]
    
    def delete_job(self, job_id: int) -> bool:
        """Delete a job and its applications"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            
            if deleted:
                self.logger.info(f"Deleted job ID: {job_id}")
            
            return deleted
    
    def bookmark_job(self, job_id: int, bookmarked: bool = True) -> bool:
        """Bookmark or unbookmark a job"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE jobs SET is_bookmarked = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
                (bookmarked, job_id)
            )
            success = cursor.rowcount > 0
            conn.commit()
            return success
    
    # ===== APPLICATION OPERATIONS =====
    
    def save_application(self, application: Application) -> int:
        """Save job application"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if application.id:
                # Update existing
                return self._update_application(cursor, application)
            else:
                # Insert new
                return self._insert_application(cursor, application)
    
    def _insert_application(self, cursor: sqlite3.Cursor, app: Application) -> int:
        """Insert new application"""
        cursor.execute('''
            INSERT INTO applications (
                job_id, cv_version, cover_letter, portfolio_links, status,
                applied_date, response_date, communications, interview_dates,
                interview_notes, offer_details, rejection_reason, created_date, updated_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            app.job_id,
            app.cv_version,
            app.cover_letter,
            json.dumps(app.portfolio_links),
            app.status.value,
            app.applied_date.isoformat() if app.applied_date else None,
            app.response_date.isoformat() if app.response_date else None,
            json.dumps(app.communications),
            json.dumps([d.isoformat() for d in app.interview_dates]),
            app.interview_notes,
            json.dumps(app.offer_details) if app.offer_details else None,
            app.rejection_reason,
            app.created_date.isoformat(),
            app.updated_date.isoformat()
        ))
        
        app_id = cursor.lastrowid
        cursor.connection.commit()
        self.logger.info(f"Saved new application for job ID: {app.job_id}")
        return app_id
    
    def _update_application(self, cursor: sqlite3.Cursor, app: Application) -> int:
        """Update existing application"""
        cursor.execute('''
            UPDATE applications SET
                cv_version = ?, cover_letter = ?, status = ?, applied_date = ?,
                response_date = ?, communications = ?, interview_dates = ?,
                interview_notes = ?, offer_details = ?, rejection_reason = ?,
                updated_date = ?
            WHERE id = ?
        ''', (
            app.cv_version,
            app.cover_letter,
            app.status.value,
            app.applied_date.isoformat() if app.applied_date else None,
            app.response_date.isoformat() if app.response_date else None,
            json.dumps(app.communications),
            json.dumps([d.isoformat() for d in app.interview_dates]),
            app.interview_notes,
            json.dumps(app.offer_details) if app.offer_details else None,
            app.rejection_reason,
            app.updated_date.isoformat(),
            app.id
        ))
        
        cursor.connection.commit()
        self.logger.info(f"Updated application ID: {app.id}")
        return app.id
    
    def get_applications(self, 
                        job_id: Optional[int] = None,
                        status: Optional[ApplicationStatus] = None,
                        limit: int = 100) -> List[Application]:
        """Retrieve applications with filtering"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM applications WHERE 1=1"
            params = []
            
            if job_id:
                query += " AND job_id = ?"
                params.append(job_id)
            
            if status:
                query += " AND status = ?"
                params.append(status.value)
            
            query += " ORDER BY created_date DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_application(row) for row in rows]
    
    def _row_to_application(self, row: sqlite3.Row) -> Application:
        """Convert database row to Application object"""
        portfolio_links = json.loads(row['portfolio_links']) if row['portfolio_links'] else []
        communications = json.loads(row['communications']) if row['communications'] else []
        interview_dates_str = json.loads(row['interview_dates']) if row['interview_dates'] else []
        interview_dates = [datetime.fromisoformat(d) for d in interview_dates_str]
        offer_details = json.loads(row['offer_details']) if row['offer_details'] else None
        
        return Application(
            id=row['id'],
            job_id=row['job_id'],
            cv_version=row['cv_version'],
            cover_letter=row['cover_letter'],
            portfolio_links=portfolio_links,
            status=ApplicationStatus(row['status']),
            applied_date=datetime.fromisoformat(row['applied_date']) if row['applied_date'] else None,
            response_date=datetime.fromisoformat(row['response_date']) if row['response_date'] else None,
            communications=communications,
            interview_dates=interview_dates,
            interview_notes=row['interview_notes'],
            offer_details=offer_details,
            rejection_reason=row['rejection_reason'],
            created_date=datetime.fromisoformat(row['created_date']),
            updated_date=datetime.fromisoformat(row['updated_date'])
        )
    
    # ===== USER PROFILE OPERATIONS =====
    
    def save_user_profile(self, profile: UserProfile) -> int:
        """Save user profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if profile exists
            cursor.execute("SELECT id FROM user_profiles WHERE email = ?", (profile.email,))
            existing = cursor.fetchone()
            
            if existing:
                return self._update_user_profile(cursor, profile, existing['id'])
            else:
                return self._insert_user_profile(cursor, profile)
    
    def _insert_user_profile(self, cursor: sqlite3.Cursor, profile: UserProfile) -> int:
        """Insert new user profile"""
        cursor.execute('''
            INSERT INTO user_profiles (
                name, email, phone, linkedin_url, portfolio_url, current_title,
                experience_years, skills, certifications, education, cv_templates,
                preferred_job_types, preferred_locations, salary_expectations,
                remote_preference, keywords_civil, keywords_it, keywords_freelance,
                auto_apply_enabled, auto_apply_filters, email_notifications,
                desktop_notifications, notification_keywords, openai_api_key, other_api_keys
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile.name, profile.email, profile.phone, profile.linkedin_url,
            profile.portfolio_url, profile.current_title, profile.experience_years,
            json.dumps(profile.skills), json.dumps(profile.certifications),
            json.dumps(profile.education), json.dumps(profile.cv_templates),
            json.dumps([jt.value for jt in profile.preferred_job_types]),
            json.dumps(profile.preferred_locations),
            json.dumps({k: v.to_dict() for k, v in profile.salary_expectations.items()}),
            profile.remote_preference, json.dumps(profile.keywords_civil),
            json.dumps(profile.keywords_it), json.dumps(profile.keywords_freelance),
            profile.auto_apply_enabled, json.dumps(profile.auto_apply_filters),
            profile.email_notifications, profile.desktop_notifications,
            json.dumps(profile.notification_keywords), profile.openai_api_key,
            json.dumps(profile.other_api_keys)
        ))
        
        profile_id = cursor.lastrowid
        cursor.connection.commit()
        self.logger.info(f"Created user profile: {profile.name}")
        return profile_id
    
    def _update_user_profile(self, cursor: sqlite3.Cursor, profile: UserProfile, profile_id: int) -> int:
        """Update existing user profile"""
        cursor.execute('''
            UPDATE user_profiles SET
                name = ?, phone = ?, linkedin_url = ?, portfolio_url = ?, current_title = ?,
                experience_years = ?, skills = ?, certifications = ?, education = ?,
                cv_templates = ?, preferred_job_types = ?, preferred_locations = ?,
                salary_expectations = ?, remote_preference = ?, keywords_civil = ?,
                keywords_it = ?, keywords_freelance = ?, auto_apply_enabled = ?,
                auto_apply_filters = ?, email_notifications = ?, desktop_notifications = ?,
                notification_keywords = ?, openai_api_key = ?, other_api_keys = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            profile.name, profile.phone, profile.linkedin_url, profile.portfolio_url,
            profile.current_title, profile.experience_years, json.dumps(profile.skills),
            json.dumps(profile.certifications), json.dumps(profile.education),
            json.dumps(profile.cv_templates),
            json.dumps([jt.value for jt in profile.preferred_job_types]),
            json.dumps(profile.preferred_locations),
            json.dumps({k: v.to_dict() for k, v in profile.salary_expectations.items()}),
            profile.remote_preference, json.dumps(profile.keywords_civil),
            json.dumps(profile.keywords_it), json.dumps(profile.keywords_freelance),
            profile.auto_apply_enabled, json.dumps(profile.auto_apply_filters),
            profile.email_notifications, profile.desktop_notifications,
            json.dumps(profile.notification_keywords), profile.openai_api_key,
            json.dumps(profile.other_api_keys), profile_id
        ))
        
        cursor.connection.commit()
        self.logger.info(f"Updated user profile: {profile.name}")
        return profile_id
    
    def get_user_profile(self, email: str = None) -> Optional[UserProfile]:
        """Get user profile (first one if email not specified)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if email:
                cursor.execute("SELECT * FROM user_profiles WHERE email = ?", (email,))
            else:
                cursor.execute("SELECT * FROM user_profiles LIMIT 1")
            
            row = cursor.fetchone()
            return self._row_to_user_profile(row) if row else None
    
    def _row_to_user_profile(self, row: sqlite3.Row) -> UserProfile:
        """Convert database row to UserProfile object"""
        # Parse JSON arrays and objects
        skills = json.loads(row['skills']) if row['skills'] else []
        certifications = json.loads(row['certifications']) if row['certifications'] else []
        education = json.loads(row['education']) if row['education'] else []
        cv_templates = json.loads(row['cv_templates']) if row['cv_templates'] else {}
        preferred_job_types = [JobType(jt) for jt in json.loads(row['preferred_job_types'])] if row['preferred_job_types'] else []
        preferred_locations = json.loads(row['preferred_locations']) if row['preferred_locations'] else []
        salary_expectations_data = json.loads(row['salary_expectations']) if row['salary_expectations'] else {}
        salary_expectations = {k: Salary.from_dict(v) for k, v in salary_expectations_data.items()}
        keywords_civil = json.loads(row['keywords_civil']) if row['keywords_civil'] else []
        keywords_it = json.loads(row['keywords_it']) if row['keywords_it'] else []
        keywords_freelance = json.loads(row['keywords_freelance']) if row['keywords_freelance'] else []
        auto_apply_filters = json.loads(row['auto_apply_filters']) if row['auto_apply_filters'] else {}
        notification_keywords = json.loads(row['notification_keywords']) if row['notification_keywords'] else []
        other_api_keys = json.loads(row['other_api_keys']) if row['other_api_keys'] else {}
        
        return UserProfile(
            name=row['name'],
            email=row['email'],
            phone=row['phone'],
            linkedin_url=row['linkedin_url'],
            portfolio_url=row['portfolio_url'],
            current_title=row['current_title'],
            experience_years=row['experience_years'],
            skills=skills,
            certifications=certifications,
            education=education,
            cv_templates=cv_templates,
            preferred_job_types=preferred_job_types,
            preferred_locations=preferred_locations,
            salary_expectations=salary_expectations,
            remote_preference=row['remote_preference'],
            keywords_civil=keywords_civil,
            keywords_it=keywords_it,
            keywords_freelance=keywords_freelance,
            auto_apply_enabled=bool(row['auto_apply_enabled']),
            auto_apply_filters=auto_apply_filters,
            email_notifications=bool(row['email_notifications']),
            desktop_notifications=bool(row['desktop_notifications']),
            notification_keywords=notification_keywords,
            openai_api_key=row['openai_api_key'],
            other_api_keys=other_api_keys
        )
    
    # ===== ANALYTICS OPERATIONS =====
    
    def save_analytics(self, analytics: Analytics, date: str = None) -> int:
        """Save analytics data for specific date"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if analytics for this date exists
            cursor.execute("SELECT id FROM analytics WHERE date = ?", (date,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE analytics SET
                        total_jobs_found = ?, jobs_by_type = ?, jobs_by_source = ?,
                        applications_sent = ?, responses_received = ?, interviews_scheduled = ?,
                        offers_received = ?, response_rate = ?, interview_rate = ?,
                        offer_rate = ?, avg_application_time = ?, avg_response_time = ?
                    WHERE id = ?
                ''', (
                    analytics.total_jobs_found,
                    json.dumps(analytics.jobs_by_type),
                    json.dumps(analytics.jobs_by_source),
                    analytics.applications_sent,
                    analytics.responses_received,
                    analytics.interviews_scheduled,
                    analytics.offers_received,
                    analytics.response_rate,
                    analytics.interview_rate,
                    analytics.offer_rate,
                    analytics.avg_application_time,
                    analytics.avg_response_time,
                    existing['id']
                ))
                analytics_id = existing['id']
            else:
                # Insert new
                cursor.execute('''
                    INSERT INTO analytics (
                        date, total_jobs_found, jobs_by_type, jobs_by_source,
                        applications_sent, responses_received, interviews_scheduled,
                        offers_received, response_rate, interview_rate, offer_rate,
                        avg_application_time, avg_response_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date,
                    analytics.total_jobs_found,
                    json.dumps(analytics.jobs_by_type),
                    json.dumps(analytics.jobs_by_source),
                    analytics.applications_sent,
                    analytics.responses_received,
                    analytics.interviews_scheduled,
                    analytics.offers_received,
                    analytics.response_rate,
                    analytics.interview_rate,
                    analytics.offer_rate,
                    analytics.avg_application_time,
                    analytics.avg_response_time
                ))
                analytics_id = cursor.lastrowid
            
            conn.commit()
            return analytics_id
    
    def get_analytics(self, date: str = None) -> Optional[Analytics]:
        """Get analytics for specific date (today if not specified)"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analytics WHERE date = ?", (date,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return Analytics(
                total_jobs_found=row['total_jobs_found'],
                jobs_by_type=json.loads(row['jobs_by_type']) if row['jobs_by_type'] else {},
                jobs_by_source=json.loads(row['jobs_by_source']) if row['jobs_by_source'] else {},
                applications_sent=row['applications_sent'],
                responses_received=row['responses_received'],
                interviews_scheduled=row['interviews_scheduled'],
                offers_received=row['offers_received'],
                response_rate=row['response_rate'],
                interview_rate=row['interview_rate'],
                offer_rate=row['offer_rate'],
                avg_application_time=row['avg_application_time'],
                avg_response_time=row['avg_response_time']
            )
    
    def calculate_current_analytics(self) -> Analytics:
        """Calculate analytics from current database state"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get job statistics
            cursor.execute("SELECT COUNT(*) as total FROM jobs")
            total_jobs = cursor.fetchone()['total']
            
            cursor.execute('''
                SELECT job_type, COUNT(*) as count 
                FROM jobs 
                GROUP BY job_type
            ''')
            jobs_by_type = {row['job_type']: row['count'] for row in cursor.fetchall()}
            
            cursor.execute('''
                SELECT source, COUNT(*) as count 
                FROM jobs 
                GROUP BY source
            ''')
            jobs_by_source = {row['source']: row['count'] for row in cursor.fetchall()}
            
            # Get application statistics
            cursor.execute("SELECT COUNT(*) as total FROM applications")
            applications_sent = cursor.fetchone()['total']
            
            cursor.execute('''
                SELECT COUNT(*) as count 
                FROM applications 
                WHERE status IN ('reviewed', 'interview_scheduled', 'interviewed', 'offer_received', 'accepted')
            ''')
            responses_received = cursor.fetchone()['count']
            
            cursor.execute('''
                SELECT COUNT(*) as count 
                FROM applications 
                WHERE status IN ('interview_scheduled', 'interviewed')
            ''')
            interviews_scheduled = cursor.fetchone()['count']
            
            cursor.execute('''
                SELECT COUNT(*) as count 
                FROM applications 
                WHERE status = 'offer_received'
            ''')
            offers_received = cursor.fetchone()['count']
            
            # Create analytics object
            analytics = Analytics(
                total_jobs_found=total_jobs,
                jobs_by_type=jobs_by_type,
                jobs_by_source=jobs_by_source,
                applications_sent=applications_sent,
                responses_received=responses_received,
                interviews_scheduled=interviews_scheduled,
                offers_received=offers_received
            )
            
            # Calculate rates
            analytics.calculate_rates()
            
            return analytics
    
    # ===== SEARCH HISTORY OPERATIONS =====
    
    def save_search_query(self, query: SearchQuery, results_count: int, execution_time: float) -> int:
        """Save search query to history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO search_history (query_data, results_count, execution_time)
                VALUES (?, ?, ?)
            ''', (
                json.dumps(query.to_dict()),
                results_count,
                execution_time
            ))
            
            search_id = cursor.lastrowid
            conn.commit()
            return search_id
    
    def get_search_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent search history"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM search_history 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ===== SETTINGS OPERATIONS =====
    
    def set_setting(self, key: str, value: Any):
        """Set application setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, json.dumps(value) if not isinstance(value, str) else value))
            conn.commit()
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get application setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if not row:
                return default
            
            try:
                return json.loads(row['value'])
            except (json.JSONDecodeError, TypeError):
                return row['value']
    
    # ===== UTILITY OPERATIONS =====
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Table counts
            tables = ['jobs', 'applications', 'user_profiles', 'analytics', 'search_history', 'settings']
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[f'{table}_count'] = cursor.fetchone()['count']
            
            # Job statistics
            cursor.execute('''
                SELECT 
                    job_type,
                    COUNT(*) as count,
                    AVG(match_score) as avg_match_score
                FROM jobs 
                GROUP BY job_type
            ''')
            job_type_stats = {row['job_type']: {
                'count': row['count'], 
                'avg_match_score': row['avg_match_score']
            } for row in cursor.fetchall()}
            stats['job_type_breakdown'] = job_type_stats
            
            # Recent activity
            cursor.execute('''
                SELECT DATE(scraped_date) as date, COUNT(*) as jobs_scraped
                FROM jobs 
                WHERE scraped_date >= date('now', '-7 days')
                GROUP BY DATE(scraped_date)
                ORDER BY date DESC
            ''')
            recent_activity = {row['date']: row['jobs_scraped'] for row in cursor.fetchall()}
            stats['recent_activity'] = recent_activity
            
            # Database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()['size']
            stats['database_size_bytes'] = db_size
            
            return stats
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to keep database manageable"""
        cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete old non-bookmarked jobs
            cursor.execute('''
                DELETE FROM jobs 
                WHERE scraped_date < ? AND is_bookmarked = FALSE
            ''', (cutoff_date,))
            jobs_deleted = cursor.rowcount
            
            # Delete old search history
            cursor.execute('''
                DELETE FROM search_history 
                WHERE created_at < ?
            ''', (cutoff_date,))
            searches_deleted = cursor.rowcount
            
            # Delete old analytics (keep monthly summaries)
            cursor.execute('''
                DELETE FROM analytics 
                WHERE created_at < ? AND date NOT LIKE '%-01'
            ''', (cutoff_date,))
            analytics_deleted = cursor.rowcount
            
            conn.commit()
            
            self.logger.info(f"Cleanup completed: {jobs_deleted} jobs, {searches_deleted} searches, {analytics_deleted} analytics deleted")
            
            return {
                'jobs_deleted': jobs_deleted,
                'searches_deleted': searches_deleted,
                'analytics_deleted': analytics_deleted
            }
    
    def export_data(self, file_path: str, table_names: List[str] = None) -> bool:
        """Export data to JSON file"""
        if table_names is None:
            table_names = ['jobs', 'applications', 'user_profiles']
        
        try:
            export_data = {}
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                for table in table_names:
                    cursor.execute(f"SELECT * FROM {table}")
                    rows = cursor.fetchall()
                    export_data[table] = [dict(row) for row in rows]
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Data exported to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            return False
    
    def import_data(self, file_path: str) -> bool:
        """Import data from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Import each table
                for table_name, rows in import_data.items():
                    if not rows:
                        continue
                    
                    # Get column names
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = [col[1] for col in cursor.fetchall() if col[1] != 'id']
                    
                    # Prepare insert statement
                    placeholders = ', '.join(['?' for _ in columns])
                    insert_sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
                    
                    # Insert rows
                    for row in rows:
                        values = [row.get(col) for col in columns]
                        cursor.execute(insert_sql, values)
                
                conn.commit()
            
            self.logger.info(f"Data imported from {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Import failed: {e}")
            return False
    
    def backup_database(self, backup_path: str = None) -> str:
        """Create database backup"""
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"data/backups/job_hunter_backup_{timestamp}.db"
        
        # Ensure backup directory exists
        Path(backup_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with self.get_connection() as source:
                backup_conn = sqlite3.connect(backup_path)
                source.backup(backup_conn)
                backup_conn.close()
            
            self.logger.info(f"Database backed up to {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise DatabaseError(f"Backup failed: {e}")
    
    def vacuum_database(self):
        """Optimize database by reclaiming space"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            conn.commit()
        
        self.logger.info("Database vacuumed and optimized")
    
    # ===== ADVANCED QUERY METHODS =====
    
    def get_jobs_with_applications(self) -> List[Dict[str, Any]]:
        """Get jobs with their application status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    j.*,
                    a.status as application_status,
                    a.applied_date,
                    a.id as application_id
                FROM jobs j
                LEFT JOIN applications a ON j.id = a.job_id
                ORDER BY j.scraped_date DESC
            ''')
            
            results = []
            for row in cursor.fetchall():
                job_data = dict(row)
                results.append(job_data)
            
            return results
    
    def get_top_companies(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get companies with most job postings"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    company_name,
                    COUNT(*) as job_count,
                    AVG(match_score) as avg_match_score,
                    company_data
                FROM jobs
                GROUP BY company_name
                ORDER BY job_count DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_salary_trends(self, job_type: JobType = None) -> List[Dict[str, Any]]:
        """Get salary trends over time"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    DATE(scraped_date) as date,
                    job_type,
                    salary_data,
                    COUNT(*) as job_count
                FROM jobs
                WHERE salary_data IS NOT NULL
            '''
            params = []
            
            if job_type:
                query += " AND job_type = ?"
                params.append(job_type.value)
            
            query += '''
                GROUP BY DATE(scraped_date), job_type
                ORDER BY date DESC
            '''
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_application_pipeline(self) -> Dict[str, int]:
        """Get current application pipeline status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM applications
                GROUP BY status
            ''')
            
            pipeline = {}
            for row in cursor.fetchall():
                pipeline[row['status']] = row['count']
            
            return pipeline
    
    def search_jobs_advanced(self, 
                           keywords: str = "",
                           job_types: List[JobType] = None,
                           locations: List[str] = None,
                           salary_min: float = None,
                           currency: Currency = Currency.USD,
                           remote_only: bool = False,
                           posted_after: datetime = None,
                           sources: List[str] = None,
                           limit: int = 100) -> List[Job]:
        """Advanced job search with multiple filters"""
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic query
            query = "SELECT * FROM jobs WHERE 1=1"
            params = []
            
            # Keywords search
            if keywords:
                search_terms = keywords.lower().split()
                for term in search_terms:
                    query += " AND (LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(company_name) LIKE ?)"
                    search_param = f"%{term}%"
                    params.extend([search_param, search_param, search_param])
            
            # Job types filter
            if job_types:
                job_type_placeholders = ','.join(['?' for _ in job_types])
                query += f" AND job_type IN ({job_type_placeholders})"
                params.extend([jt.value for jt in job_types])
            
            # Location filter
            if locations:
                location_conditions = []
                for location in locations:
                    location_conditions.append("location_data LIKE ?")
                    params.append(f"%{location}%")
                query += f" AND ({' OR '.join(location_conditions)})"
            
            # Salary filter
            if salary_min:
                query += " AND salary_data LIKE ?"
                params.append(f'%"min_amount": %{salary_min}%')
            
            # Remote filter
            if remote_only:
                query += " AND location_data LIKE '%\"is_remote\": true%'"
            
            # Date filter
            if posted_after:
                query += " AND scraped_date >= ?"
                params.append(posted_after.isoformat())
            
            # Sources filter
            if sources:
                source_placeholders = ','.join(['?' for _ in sources])
                query += f" AND source IN ({source_placeholders})"
                params.extend(sources)
            
            query += " ORDER BY match_score DESC, scraped_date DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_job(row) for row in rows]
    
    # ===== DATABASE MAINTENANCE =====
    
    def close(self):
        """Close database connections"""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
        self.logger.info("Database connections closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# ===== DATABASE MIGRATION SYSTEM =====

class DatabaseMigrator:
    """Handles database schema migrations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def get_current_version(self) -> int:
        """Get current database schema version"""
        try:
            version = self.db_manager.get_setting('schema_version', 1)
            return int(version)
        except:
            return 1
    
    def migrate_to_version(self, target_version: int):
        """Migrate database to target version"""
        current_version = self.get_current_version()
        
        if current_version >= target_version:
            self.logger.info(f"Database already at version {current_version}")
            return
        
        self.logger.info(f"Migrating database from version {current_version} to {target_version}")
        
        # Run migrations sequentially
        for version in range(current_version + 1, target_version + 1):
            self._run_migration(version)
            self.db_manager.set_setting('schema_version', version)
        
        self.logger.info(f"Migration completed to version {target_version}")
    
    def _run_migration(self, version: int):
        """Run specific migration"""
        migration_methods = {
            2: self._migrate_to_v2,
            3: self._migrate_to_v3,
            # Add more migrations as needed
        }
        
        if version in migration_methods:
            migration_methods[version]()
        else:
            self.logger.warning(f"No migration defined for version {version}")
    
    def _migrate_to_v2(self):
        """Migration to version 2 - Add match_score column"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE jobs ADD COLUMN match_score REAL")
                conn.commit()
                self.logger.info("Added match_score column to jobs table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise
    
    def _migrate_to_v3(self):
        """Migration to version 3 - Add updated_at timestamps"""
        with self.db_manager.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("ALTER TABLE jobs ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                cursor.execute("ALTER TABLE applications ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                conn.commit()
                self.logger.info("Added updated_at timestamps")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise


# ===== UTILITY FUNCTIONS =====

def create_test_database(db_path: str = "test_job_hunter.db") -> DatabaseManager:
    """Create a test database with sample data"""
    db = DatabaseManager(db_path)
    
    # Create sample user profile
    from core.database.models import create_sample_user_profile, create_sample_job
    
    sample_user = create_sample_user_profile()
    db.save_user_profile(sample_user)
    
    # Create sample jobs
    for i in range(5):
        job = create_sample_job()
        job.title = f"Sample Job {i+1}"
        job.company.name = f"Company {i+1}"
        job.match_score = 85.0 - (i * 5)  # Decreasing match scores
        db.save_job(job)
    
    return db


if __name__ == "__main__":
    # Example usage and testing
    print("Testing Database Manager")
    print("=" * 40)
    
    # Create test database
    db = create_test_database("test_example.db")
    
    # Test job operations
    jobs = db.get_jobs(limit=10)
    print(f"Found {len(jobs)} jobs in database")
    
    # Test search
    search_results = db.search_jobs("python developer")
    print(f"Search results: {len(search_results)} jobs found")
    
    # Test analytics
    analytics = db.calculate_current_analytics()
    print(f"Analytics: {analytics.total_jobs_found} total jobs, {analytics.applications_sent} applications")
    
    # Test database stats
    stats = db.get_database_stats()
    print(f"Database stats: {stats}")
    
    # Cleanup
    db.close()
    print("\nDatabase manager test completed!")