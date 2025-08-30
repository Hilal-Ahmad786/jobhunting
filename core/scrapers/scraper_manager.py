#!/usr/bin/env python3
"""
Scraper Manager for Job Hunter Bot

This module coordinates and manages all job scrapers, providing:
- Multi-platform job searching across all sources
- Intelligent scraper scheduling and load balancing
- Duplicate detection and data deduplication
- Error handling and retry mechanisms
- Progress tracking and real-time updates
- Integration with database and CV optimizer
- Performance monitoring and analytics
"""

import asyncio
import threading
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
import hashlib
import json

# Our components
from core.database.models import Job, JobType, SearchQuery, UserProfile
from core.database.database_manager import DatabaseManager
from core.scrapers.base_scraper import BaseScraper, ScrapingError
from core.ai.cv_optimizer import CVOptimizer


class ScrapingStatus(Enum):
    """Scraping operation status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScrapingSession:
    """Information about a scraping session"""
    session_id: str
    search_query: SearchQuery
    scrapers_used: List[str]
    start_time: datetime
    end_time: Optional[datetime] = None
    status: ScrapingStatus = ScrapingStatus.IDLE
    jobs_found: int = 0
    jobs_saved: int = 0
    duplicates_removed: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def duration(self) -> Optional[float]:
        """Get session duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'search_query': self.search_query.to_dict(),
            'scrapers_used': self.scrapers_used,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status.value,
            'jobs_found': self.jobs_found,
            'jobs_saved': self.jobs_saved,
            'duplicates_removed': self.duplicates_removed,
            'errors': self.errors,
            'duration': self.duration
        }


@dataclass
class ScraperConfig:
    """Configuration for individual scrapers"""
    name: str
    class_name: str
    enabled: bool = True
    priority: int = 1  # Higher priority scrapers run first
    max_jobs_per_session: int = 100
    rate_limit_requests_per_minute: int = 30
    timeout_seconds: int = 300  # 5 minutes
    retry_attempts: int = 3
    config_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.config_params is None:
            self.config_params = {}


class ScraperManager:
    """
    Centralized manager for all job scrapers
    Handles scheduling, coordination, and result aggregation
    """
    
    def __init__(self, 
                 database_manager: DatabaseManager,
                 cv_optimizer: Optional[CVOptimizer] = None):
        
        self.db_manager = database_manager
        self.cv_optimizer = cv_optimizer
        self.logger = logging.getLogger(__name__)
        
        # Scraper registry
        self.scrapers: Dict[str, BaseScraper] = {}
        self.scraper_configs: Dict[str, ScraperConfig] = {}
        
        # Session management
        self.current_session: Optional[ScrapingSession] = None
        self.session_history: List[ScrapingSession] = []
        
        # Thread management
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.is_running = False
        self.should_stop = False
        
        # Progress tracking
        self.progress_callback: Optional[Callable] = None
        self.status_callback: Optional[Callable] = None
        
        # Duplicate detection
        self.job_hashes: Set[str] = set()
        
        # Performance tracking
        self.stats = {
            'total_sessions': 0,
            'total_jobs_found': 0,
            'total_duplicates_removed': 0,
            'average_session_duration': 0.0,
            'scraper_performance': {},
            'error_count': 0
        }
        
        # Initialize default scrapers
        self._setup_default_scrapers()
        
        self.logger.info("Scraper Manager initialized successfully")
    
    def _setup_default_scrapers(self):
        """Setup default scraper configurations"""
        
        # LinkedIn Scraper
        self.register_scraper(ScraperConfig(
            name="LinkedIn",
            class_name="LinkedInScraper",
            priority=1,
            max_jobs_per_session=50,
            rate_limit_requests_per_minute=20,
            config_params={
                'headless': True,
                'stealth': True,
                'min_delay': 2.0,
                'max_delay': 5.0
            }
        ))
        
        # Indeed Scraper
        self.register_scraper(ScraperConfig(
            name="Indeed",
            class_name="IndeedScraper", 
            priority=2,
            max_jobs_per_session=75,
            rate_limit_requests_per_minute=25,
            config_params={
                'headless': True,
                'requests_per_minute': 25
            }
        ))
        
        # Upwork Scraper
        self.register_scraper(ScraperConfig(
            name="Upwork",
            class_name="UpworkScraper",
            priority=3,
            max_jobs_per_session=30,
            rate_limit_requests_per_minute=15,
            config_params={
                'headless': True,
                'login_required': False  # Can be enabled with credentials
            }
        ))
        
        # Remote.co Scraper
        self.register_scraper(ScraperConfig(
            name="RemoteOK",
            class_name="RemoteOKScraper",
            priority=4,
            max_jobs_per_session=40,
            rate_limit_requests_per_minute=20
        ))
        
        # AngelList/Wellfound Scraper
        self.register_scraper(ScraperConfig(
            name="AngelList",
            class_name="AngelListScraper",
            priority=5,
            max_jobs_per_session=25,
            rate_limit_requests_per_minute=15
        ))
    
    def register_scraper(self, config: ScraperConfig):
        """Register a new scraper configuration"""
        self.scraper_configs[config.name] = config
        self.stats['scraper_performance'][config.name] = {
            'jobs_scraped': 0,
            'success_rate': 100.0,
            'average_duration': 0.0,
            'last_run': None,
            'error_count': 0
        }
        
        self.logger.info(f"Registered scraper: {config.name}")
    
    def enable_scraper(self, scraper_name: str, enabled: bool = True):
        """Enable or disable a specific scraper"""
        if scraper_name in self.scraper_configs:
            self.scraper_configs[scraper_name].enabled = enabled
            self.logger.info(f"Scraper {scraper_name} {'enabled' if enabled else 'disabled'}")
        else:
            self.logger.warning(f"Unknown scraper: {scraper_name}")
    
    def search_jobs(self, 
                   search_query: SearchQuery,
                   user_profile: Optional[UserProfile] = None,
                   optimize_cvs: bool = False,
                   specific_scrapers: Optional[List[str]] = None) -> ScrapingSession:
        """
        Main method to search for jobs across multiple platforms
        
        Args:
            search_query: Search parameters
            user_profile: User profile for CV optimization
            optimize_cvs: Whether to generate optimized CVs
            specific_scrapers: List of specific scrapers to use
            
        Returns:
            ScrapingSession with results
        """
        
        session_id = self._generate_session_id()
        
        self.current_session = ScrapingSession(
            session_id=session_id,
            search_query=search_query,
            scrapers_used=[],
            start_time=datetime.now(),
            status=ScrapingStatus.RUNNING
        )
        
        self.logger.info(f"Starting job search session: {session_id}")
        self.logger.info(f"Search query: {search_query.keywords} in {search_query.locations}")
        
        try:
            # Determine which scrapers to use
            scrapers_to_use = self._select_scrapers(search_query, specific_scrapers)
            self.current_session.scrapers_used = list(scrapers_to_use.keys())
            
            # Clear duplicate detection for new session
            self.job_hashes.clear()
            
            # Execute scraping across all selected scrapers
            all_jobs = self._execute_parallel_scraping(scrapers_to_use, search_query)
            
            # Remove duplicates
            unique_jobs = self._deduplicate_jobs(all_jobs)
            
            # Save jobs to database
            saved_job_ids = self._save_jobs_to_database(unique_jobs)
            
            # Generate optimized CVs if requested
            if optimize_cvs and user_profile and self.cv_optimizer and saved_job_ids:
                self._generate_optimized_cvs(user_profile, unique_jobs)
            
            # Update session results
            self.current_session.jobs_found = len(all_jobs)
            self.current_session.jobs_saved = len(unique_jobs)
            self.current_session.duplicates_removed = len(all_jobs) - len(unique_jobs)
            self.current_session.status = ScrapingStatus.COMPLETED
            self.current_session.end_time = datetime.now()
            
            # Update statistics
            self._update_statistics()
            
            # Save session to history
            self.session_history.append(self.current_session)
            
            # Save search query to database
            self.db_manager.save_search_query(
                search_query, 
                len(unique_jobs), 
                self.current_session.duration or 0
            )
            
            self.logger.info(f"Search session completed: {len(unique_jobs)} unique jobs found")
            
            return self.current_session
            
        except Exception as e:
            self.logger.error(f"Search session failed: {e}")
            self.current_session.status = ScrapingStatus.FAILED
            self.current_session.errors.append(str(e))
            self.current_session.end_time = datetime.now()
            
            raise e
        finally:
            self.is_running = False
    
    def _select_scrapers(self, 
                        search_query: SearchQuery,
                        specific_scrapers: Optional[List[str]] = None) -> Dict[str, ScraperConfig]:
        """Select appropriate scrapers based on search criteria"""
        
        selected = {}
        
        if specific_scrapers:
            # Use only specified scrapers
            for scraper_name in specific_scrapers:
                if scraper_name in self.scraper_configs and self.scraper_configs[scraper_name].enabled:
                    selected[scraper_name] = self.scraper_configs[scraper_name]
        else:
            # Select based on job types and preferences
            for name, config in self.scraper_configs.items():
                if not config.enabled:
                    continue
                
                # Job type filtering
                if search_query.job_types:
                    if JobType.FREELANCE in search_query.job_types and name in ['Upwork', 'Fiverr']:
                        selected[name] = config
                    elif JobType.IT_PROGRAMMING in search_query.job_types and name in ['LinkedIn', 'Indeed', 'AngelList']:
                        selected[name] = config
                    elif JobType.CIVIL_ENGINEERING in search_query.job_types and name in ['LinkedIn', 'Indeed']:
                        selected[name] = config
                else:
                    # Use all enabled scrapers
                    selected[name] = config
                
                # Remote-only filtering
                if search_query.remote_only and name in ['RemoteOK', 'WeWorkRemotely']:
                    selected[name] = config
        
        # Sort by priority
        selected = dict(sorted(selected.items(), key=lambda x: x[1].priority))
        
        self.logger.info(f"Selected {len(selected)} scrapers: {list(selected.keys())}")
        return selected
    
    def _execute_parallel_scraping(self, 
                                 scrapers_to_use: Dict[str, ScraperConfig],
                                 search_query: SearchQuery) -> List[Job]:
        """Execute scraping across multiple scrapers in parallel"""
        
        all_jobs = []
        futures = []
        
        self.is_running = True
        
        # Submit scraping tasks to thread pool
        for scraper_name, config in scrapers_to_use.items():
            if self.should_stop:
                break
                
            future = self.executor.submit(
                self._run_single_scraper,
                scraper_name,
                config,
                search_query
            )
            futures.append((scraper_name, future))
        
        # Collect results as they complete
        for scraper_name, future in futures:
            try:
                scraper_jobs = future.result(timeout=scrapers_to_use[scraper_name].timeout_seconds)
                all_jobs.extend(scraper_jobs)
                
                # Update progress
                if self.progress_callback:
                    progress = len([f for _, f in futures if f.done()]) / len(futures) * 100
                    self.progress_callback(progress)
                
                self.logger.info(f"Scraper {scraper_name} completed: {len(scraper_jobs)} jobs")
                
            except Exception as e:
                self.logger.error(f"Scraper {scraper_name} failed: {e}")
                self.current_session.errors.append(f"{scraper_name}: {str(e)}")
                
                # Update scraper performance stats
                self.stats['scraper_performance'][scraper_name]['error_count'] += 1
                continue
        
        return all_jobs
    
    def _run_single_scraper(self, 
                           scraper_name: str,
                           config: ScraperConfig, 
                           search_query: SearchQuery) -> List[Job]:
        """Run a single scraper"""
        
        start_time = time.time()
        jobs = []
        
        try:
            # Update status
            if self.status_callback:
                self.status_callback(f"Scraping {scraper_name}...")
            
            # Create scraper instance
            scraper = self._create_scraper_instance(scraper_name, config)
            
            if not scraper:
                raise ScrapingError(f"Could not create scraper instance: {scraper_name}")
            
            # Determine search parameters
            keywords = search_query.keywords
            location = search_query.locations[0] if search_query.locations else ""
            limit = min(config.max_jobs_per_session, 100)
            
            # Execute scraping
            with scraper:
                jobs = scraper.scrape_jobs(keywords, location, limit)
            
            # Update performance stats
            duration = time.time() - start_time
            self.stats['scraper_performance'][scraper_name]['jobs_scraped'] += len(jobs)
            self.stats['scraper_performance'][scraper_name]['last_run'] = datetime.now()
            self.stats['scraper_performance'][scraper_name]['average_duration'] = duration
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Scraper {scraper_name} error: {e}")
            
            # Update error stats
            self.stats['scraper_performance'][scraper_name]['error_count'] += 1
            self.stats['error_count'] += 1
            
            return []
    
    def _create_scraper_instance(self, scraper_name: str, config: ScraperConfig) -> Optional[BaseScraper]:
        """Create scraper instance dynamically"""
        
        try:
            # Import scraper classes dynamically
            if scraper_name == "LinkedIn":
                from core.scrapers.linkedin_scraper import LinkedInScraper
                return LinkedInScraper(config.config_params)
            elif scraper_name == "Indeed":
                from core.scrapers.indeed_scraper import IndeedScraper
                return IndeedScraper(config.config_params)
            elif scraper_name == "Upwork":
                from core.scrapers.upwork_scraper import UpworkScraper
                return UpworkScraper(config.config_params)
            elif scraper_name == "RemoteOK":
                from core.scrapers.remote_ok_scraper import RemoteOKScraper
                return RemoteOKScraper(config.config_params)
            elif scraper_name == "AngelList":
                from core.scrapers.angellist_scraper import AngelListScraper
                return AngelListScraper(config.config_params)
            else:
                self.logger.warning(f"Unknown scraper type: {scraper_name}")
                return None
                
        except ImportError as e:
            self.logger.error(f"Could not import scraper {scraper_name}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to create scraper {scraper_name}: {e}")
            return None
    
    def _deduplicate_jobs(self, jobs: List[Job]) -> List[Job]:
        """Remove duplicate jobs based on URL and content similarity"""
        
        unique_jobs = []
        seen_urls = set()
        
        for job in jobs:
            # Create job hash for duplicate detection
            job_hash = self._create_job_hash(job)
            
            if job_hash not in self.job_hashes and job.url not in seen_urls:
                unique_jobs.append(job)
                self.job_hashes.add(job_hash)
                seen_urls.add(job.url)
            else:
                self.logger.debug(f"Duplicate job removed: {job.title} at {job.company.name}")
        
        return unique_jobs
    
    def _create_job_hash(self, job: Job) -> str:
        """Create hash for job to detect duplicates"""
        # Use combination of title, company, and location for hash
        hash_content = f"{job.title.lower()}{job.company.name.lower()}{str(job.location).lower()}"
        return hashlib.md5(hash_content.encode()).hexdigest()
    
    def _save_jobs_to_database(self, jobs: List[Job]) -> List[int]:
        """Save jobs to database and return IDs"""
        saved_ids = []
        
        for job in jobs:
            try:
                job_id = self.db_manager.save_job(job)
                saved_ids.append(job_id)
            except Exception as e:
                self.logger.error(f"Failed to save job {job.title}: {e}")
                continue
        
        self.logger.info(f"Saved {len(saved_ids)} jobs to database")
        return saved_ids
    
    def _generate_optimized_cvs(self, user_profile: UserProfile, jobs: List[Job]):
        """Generate optimized CVs for found jobs"""
        
        if not self.cv_optimizer:
            self.logger.warning("CV Optimizer not available")
            return
        
        self.logger.info(f"Generating optimized CVs for {len(jobs)} jobs...")
        
        try:
            from core.ai.cv_optimizer import BulkOptimizer
            bulk_optimizer = BulkOptimizer(self.cv_optimizer)
            
            # Optimize for top jobs (limit to avoid overwhelming)
            top_jobs = sorted(jobs, key=lambda x: x.match_score or 0, reverse=True)[:10]
            
            optimization_results = bulk_optimizer.optimize_for_multiple_jobs(
                user_profile, top_jobs, max_concurrent=3
            )
            
            self.logger.info(f"Generated {len(optimization_results)} optimized CVs")
            
        except Exception as e:
            self.logger.error(f"CV optimization failed: {e}")
    
    def _update_statistics(self):
        """Update scraper manager statistics"""
        self.stats['total_sessions'] += 1
        self.stats['total_jobs_found'] += self.current_session.jobs_found
        self.stats['total_duplicates_removed'] += self.current_session.duplicates_removed
        
        # Calculate average session duration
        if self.session_history:
            durations = [s.duration for s in self.session_history if s.duration]
            if durations:
                self.stats['average_session_duration'] = sum(durations) / len(durations)
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"session_{timestamp}_{len(self.session_history)}"
    
    # ===== CONTROL METHODS =====
    
    def pause_scraping(self):
        """Pause current scraping operation"""
        if self.current_session and self.current_session.status == ScrapingStatus.RUNNING:
            self.current_session.status = ScrapingStatus.PAUSED
            self.logger.info("Scraping paused")
    
    def resume_scraping(self):
        """Resume paused scraping operation"""
        if self.current_session and self.current_session.status == ScrapingStatus.PAUSED:
            self.current_session.status = ScrapingStatus.RUNNING
            self.logger.info("Scraping resumed")
    
    def cancel_scraping(self):
        """Cancel current scraping operation"""
        self.should_stop = True
        if self.current_session:
            self.current_session.status = ScrapingStatus.CANCELLED
            self.current_session.end_time = datetime.now()
        self.logger.info("Scraping cancelled")
    
    def set_progress_callback(self, callback: Callable[[float], None]):
        """Set callback for progress updates"""
        self.progress_callback = callback
    
    def set_status_callback(self, callback: Callable[[str], None]):
        """Set callback for status updates"""
        self.status_callback = callback
    
    # ===== MONITORING AND ANALYTICS =====
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current scraping status"""
        return {
            'is_running': self.is_running,
            'current_session': self.current_session.to_dict() if self.current_session else None,
            'enabled_scrapers': [name for name, config in self.scraper_configs.items() if config.enabled],
            'session_count': len(self.session_history),
            'should_stop': self.should_stop
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'overall_stats': self.stats,
            'scraper_performance': self.stats['scraper_performance'],
            'recent_sessions': [s.to_dict() for s in self.session_history[-5:]],
            'success_rate': self._calculate_success_rate(),
            'jobs_per_hour': self._calculate_jobs_per_hour()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate"""
        if not self.session_history:
            return 100.0
        
        successful = len([s for s in self.session_history if s.status == ScrapingStatus.COMPLETED])
        return (successful / len(self.session_history)) * 100
    
    def _calculate_jobs_per_hour(self) -> float:
        """Calculate jobs found per hour"""
        if not self.session_history:
            return 0.0
        
        total_duration = sum(s.duration for s in self.session_history if s.duration)
        if total_duration == 0:
            return 0.0
        
        total_hours = total_duration / 3600
        return self.stats['total_jobs_found'] / total_hours
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        stats = self.get_performance_stats()
        
        report = f"""
SCRAPER MANAGER PERFORMANCE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERALL STATISTICS:
- Total Sessions: {self.stats['total_sessions']}
- Total Jobs Found: {self.stats['total_jobs_found']}
- Duplicates Removed: {self.stats['total_duplicates_removed']}
- Success Rate: {stats['success_rate']:.1f}%
- Jobs per Hour: {stats['jobs_per_hour']:.1f}
- Average Session Duration: {self.stats['average_session_duration']:.1f}s

SCRAPER PERFORMANCE:
"""
        
        for scraper_name, perf in self.stats['scraper_performance'].items():
            enabled = "✓" if self.scraper_configs[scraper_name].enabled else "✗"
            report += f"""
{enabled} {scraper_name}:
  - Jobs Scraped: {perf['jobs_scraped']}
  - Error Count: {perf['error_count']}
  - Last Run: {perf['last_run'].strftime('%Y-%m-%d %H:%M') if perf['last_run'] else 'Never'}
  - Avg Duration: {perf['average_duration']:.1f}s
"""
        
        report += f"""
RECENT SESSIONS:
"""
        for session in self.session_history[-3:]:
            report += f"""
Session {session.session_id}:
  - Status: {session.status.value}
  - Jobs Found: {session.jobs_found}
  - Jobs Saved: {session.jobs_saved}
  - Duration: {session.duration:.1f}s if {session.duration} else 'N/A'
  - Scrapers Used: {', '.join(session.scrapers_used)}
"""
        
        return report
    
    # ===== SCHEDULED OPERATIONS =====
    
    def schedule_regular_searches(self, 
                                 search_queries: List[SearchQuery],
                                 interval_hours: int = 24,
                                 user_profile: Optional[UserProfile] = None):
        """Schedule regular job searches"""
        
        def run_scheduled_search():
            while True:
                try:
                    for query in search_queries:
                        self.logger.info(f"Running scheduled search: {query.keywords}")
                        self.search_jobs(query, user_profile, optimize_cvs=True)
                        time.sleep(300)  # 5-minute delay between queries
                    
                    self.logger.info(f"Scheduled searches completed. Next run in {interval_hours} hours.")
                    time.sleep(interval_hours * 3600)  # Convert hours to seconds
                    
                except Exception as e:
                    self.logger.error(f"Scheduled search failed: {e}")
                    time.sleep(3600)  # Wait 1 hour before retrying
        
        # Run scheduled searches in background thread
        schedule_thread = threading.Thread(target=run_scheduled_search, daemon=True)
        schedule_thread.start()
        
        self.logger.info(f"Scheduled searches started (interval: {interval_hours}h)")
    
    def cleanup_old_sessions(self, days_to_keep: int = 30):
        """Clean up old session history"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        original_count = len(self.session_history)
        self.session_history = [
            s for s in self.session_history 
            if s.start_time > cutoff_date
        ]
        
        cleaned = original_count - len(self.session_history)
        if cleaned > 0:
            self.logger.info(f"Cleaned up {cleaned} old sessions")
    
    # ===== CONTEXT MANAGER =====
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def close(self):
        """Clean shutdown"""
        self.should_stop = True
        
        if self.current_session and self.current_session.status == ScrapingStatus.RUNNING:
            self.current_session.status = ScrapingStatus.CANCELLED
            self.current_session.end_time = datetime.now()
        
        # Shutdown thread pool
        self.executor.shutdown(wait=True)
        
        # Close all scraper instances
        for scraper in self.scrapers.values():
            try:
                scraper.close()
            except Exception as e:
                self.logger.error(f"Error closing scraper: {e}")
        
        self.logger.info("Scraper Manager closed successfully")


# ===== SPECIALIZED SCRAPER MANAGERS =====

class FreelanceScraperManager(ScraperManager):
    """Specialized manager for freelance platforms"""
    
    def __init__(self, database_manager: DatabaseManager, cv_optimizer: Optional[CVOptimizer] = None):
        super().__init__(database_manager, cv_optimizer)
        
        # Override with freelance-focused scrapers
        self._setup_freelance_scrapers()
    
    def _setup_freelance_scrapers(self):
        """Setup freelance-specific scrapers"""
        
        # Clear default scrapers
        self.scraper_configs.clear()
        
        # Add freelance platforms
        freelance_scrapers = [
            ScraperConfig("Upwork", "UpworkScraper", priority=1, max_jobs_per_session=50),
            ScraperConfig("Fiverr", "FiverrScraper", priority=2, max_jobs_per_session=30),
            ScraperConfig("Freelancer", "FreelancerScraper", priority=3, max_jobs_per_session=40),
            ScraperConfig("Toptal", "ToptalScraper", priority=4, max_jobs_per_session=20),
            ScraperConfig("99designs", "NinetyNineDesignsScraper", priority=5, max_jobs_per_session=25),
            ScraperConfig("PeoplePerHour", "PeoplePerHourScraper", priority=6, max_jobs_per_session=35),
            ScraperConfig("Guru", "GuruScraper", priority=7, max_jobs_per_session=30)
        ]
        
        for config in freelance_scrapers:
            self.register_scraper(config)


class RemoteJobManager(ScraperManager):
    """Specialized manager for remote job platforms"""
    
    def __init__(self, database_manager: DatabaseManager, cv_optimizer: Optional[CVOptimizer] = None):
        super().__init__(database_manager, cv_optimizer)
        
        # Override with remote-focused scrapers
        self._setup_remote_scrapers()
    
    def _setup_remote_scrapers(self):
        """Setup remote job specific scrapers"""
        
        # Clear default scrapers
        self.scraper_configs.clear()
        
        remote_scrapers = [
            ScraperConfig("RemoteOK", "RemoteOKScraper", priority=1, max_jobs_per_session=60),
            ScraperConfig("WeWorkRemotely", "WeWorkRemotelyScraper", priority=2, max_jobs_per_session=40),
            ScraperConfig("Remote.co", "RemoteCoScraper", priority=3, max_jobs_per_session=50),
            ScraperConfig("FlexJobs", "FlexJobsScraper", priority=4, max_jobs_per_session=45),
            ScraperConfig("RemoteBase", "RemoteBaseScraper", priority=5, max_jobs_per_session=30),
            ScraperConfig("NoDesk", "NoDeskScraper", priority=6, max_jobs_per_session=35),
            ScraperConfig("JustRemote", "JustRemoteScraper", priority=7, max_jobs_per_session=40)
        ]
        
        for config in remote_scrapers:
            self.register_scraper(config)


# ===== INTELLIGENT SEARCH COORDINATOR =====

class IntelligentSearchCoordinator:
    """
    Advanced search coordinator that optimizes scraping strategy
    based on user preferences, historical performance, and market conditions
    """
    
    def __init__(self, scraper_manager: ScraperManager, database_manager: DatabaseManager):
        self.scraper_manager = scraper_manager
        self.db_manager = database_manager
        self.logger = logging.getLogger(__name__)
    
    def execute_smart_search(self, 
                           user_profile: UserProfile,
                           target_job_count: int = 100,
                           max_search_time: int = 1800) -> ScrapingSession:
        """
        Execute intelligent job search optimized for user preferences
        
        Args:
            user_profile: User's profile and preferences
            target_job_count: Target number of jobs to find
            max_search_time: Maximum time to spend searching (seconds)
            
        Returns:
            ScrapingSession with optimized results
        """
        
        # Analyze user preferences to create optimal search queries
        search_queries = self._generate_optimal_queries(user_profile)
        
        # Prioritize scrapers based on historical performance for this user
        scraper_priority = self._analyze_scraper_effectiveness(user_profile)
        
        # Execute searches with intelligent coordination
        best_session = None
        jobs_found = 0
        start_time = time.time()
        
        for query in search_queries:
            if jobs_found >= target_job_count or (time.time() - start_time) > max_search_time:
                break
            
            # Select best scrapers for this specific query
            optimal_scrapers = self._select_optimal_scrapers(query, scraper_priority)
            
            session = self.scraper_manager.search_jobs(
                search_query=query,
                user_profile=user_profile,
                optimize_cvs=True,
                specific_scrapers=optimal_scrapers
            )
            
            jobs_found += session.jobs_saved
            best_session = session  # Keep the last session as primary result
        
        self.logger.info(f"Smart search completed: {jobs_found} jobs found in {time.time() - start_time:.1f}s")
        return best_session
    
    def _generate_optimal_queries(self, user_profile: UserProfile) -> List[SearchQuery]:
        """Generate optimal search queries based on user profile"""
        queries = []
        
        # Create queries for each preferred job type
        for job_type in user_profile.preferred_job_types:
            
            # Get job type specific keywords
            if job_type == JobType.CIVIL_ENGINEERING:
                keywords_list = user_profile.keywords_civil or ["civil engineer", "structural engineer"]
            elif job_type == JobType.IT_PROGRAMMING:
                keywords_list = user_profile.keywords_it or ["software developer", "programmer"]
            elif job_type == JobType.FREELANCE:
                keywords_list = user_profile.keywords_freelance or ["freelance", "contractor"]
            else:
                keywords_list = ["job"]
            
            # Create query for each keyword set
            for keywords in keywords_list:
                query = SearchQuery(
                    keywords=keywords,
                    job_types=[job_type],
                    locations=user_profile.preferred_locations[:3],  # Limit to top 3 locations
                    remote_only=(user_profile.remote_preference == 'remote'),
                    salary_min=user_profile.salary_expectations.get(job_type.value, {}).get('min_amount'),
                    sources=[],  # Will be determined by scraper selection
                    date_posted='week'  # Focus on recent jobs
                )
                queries.append(query)
        
        return queries[:5]  # Limit to 5 queries to avoid overwhelming
    
    def _analyze_scraper_effectiveness(self, user_profile: UserProfile) -> Dict[str, float]:
        """Analyze which scrapers work best for this user's profile"""
        
        # Get historical data about applications and responses
        applications = self.db_manager.get_applications(limit=100)
        
        scraper_effectiveness = {}
        
        for scraper_name in self.scraper_manager.scraper_configs.keys():
            # Calculate effectiveness based on:
            # 1. Jobs found from this scraper
            # 2. Applications submitted from jobs found on this scraper
            # 3. Response rates from those applications
            
            # This is a simplified calculation - in reality would be more sophisticated
            base_score = 1.0
            
            # Bonus for scrapers that work well with user's job types
            if JobType.FREELANCE in user_profile.preferred_job_types and 'Upwork' in scraper_name:
                base_score += 0.5
            elif JobType.IT_PROGRAMMING in user_profile.preferred_job_types and scraper_name in ['LinkedIn', 'AngelList']:
                base_score += 0.3
            elif JobType.CIVIL_ENGINEERING in user_profile.preferred_job_types and scraper_name in ['LinkedIn', 'Indeed']:
                base_score += 0.3
            
            scraper_effectiveness[scraper_name] = base_score
        
        return scraper_effectiveness
    
    def _select_optimal_scrapers(self, query: SearchQuery, effectiveness: Dict[str, float]) -> List[str]:
        """Select optimal scrapers for a specific query"""
        
        # Score scrapers for this specific query
        scraper_scores = {}
        
        for scraper_name, base_effectiveness in effectiveness.items():
            score = base_effectiveness
            
            # Job type specific bonuses
            if query.job_types:
                for job_type in query.job_types:
                    if job_type == JobType.FREELANCE and scraper_name in ['Upwork', 'Fiverr', 'Freelancer']:
                        score += 1.0
                    elif job_type == JobType.IT_PROGRAMMING and scraper_name in ['LinkedIn', 'Indeed', 'AngelList']:
                        score += 0.8
                    elif job_type == JobType.CIVIL_ENGINEERING and scraper_name in ['LinkedIn', 'Indeed']:
                        score += 0.8
            
            # Remote preference bonus
            if query.remote_only and scraper_name in ['RemoteOK', 'WeWorkRemotely', 'Remote.co']:
                score += 0.7
            
            # Location specific bonuses
            for location in query.locations:
                if 'australia' in location.lower() and scraper_name in ['Seek', 'CareerOne']:
                    score += 0.5
                elif 'uk' in location.lower() and scraper_name in ['Reed', 'Totaljobs']:
                    score += 0.5
                elif 'germany' in location.lower() and scraper_name in ['StepStone', 'Xing']:
                    score += 0.5
            
            scraper_scores[scraper_name] = score
        
        # Select top 3-5 scrapers
        sorted_scrapers = sorted(scraper_scores.items(), key=lambda x: x[1], reverse=True)
        optimal_scrapers = [name for name, score in sorted_scrapers[:5] if score > 0.5]
        
        return optimal_scrapers


# ===== REAL-TIME JOB MONITORING =====

class JobAlertSystem:
    """Real-time job monitoring and alert system"""
    
    def __init__(self, scraper_manager: ScraperManager, user_profile: UserProfile):
        self.scraper_manager = scraper_manager
        self.user_profile = user_profile
        self.logger = logging.getLogger(__name__)
        
        # Alert configuration
        self.alert_keywords = user_profile.notification_keywords
        self.check_interval = 3600  # Check every hour
        self.is_monitoring = False
        
        # Notification callbacks
        self.email_callback: Optional[Callable] = None
        self.desktop_callback: Optional[Callable] = None
    
    def start_monitoring(self):
        """Start real-time job monitoring"""
        self.is_monitoring = True
        
        def monitor_loop():
            while self.is_monitoring:
                try:
                    # Run focused searches for alert keywords
                    for keyword in self.alert_keywords:
                        query = SearchQuery(
                            keywords=keyword,
                            job_types=self.user_profile.preferred_job_types,
                            remote_only=(self.user_profile.remote_preference == 'remote'),
                            date_posted='today'  # Only today's jobs
                        )
                        
                        session = self.scraper_manager.search_jobs(query)
                        
                        if session.jobs_saved > 0:
                            self._send_job_alerts(session.jobs_saved, keyword)
                    
                    # Wait before next check
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Job monitoring error: {e}")
                    time.sleep(300)  # Wait 5 minutes on error
        
        # Start monitoring in background
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        
        self.logger.info("Job monitoring started")
    
    def stop_monitoring(self):
        """Stop job monitoring"""
        self.is_monitoring = False
        self.logger.info("Job monitoring stopped")
    
    def _send_job_alerts(self, job_count: int, keyword: str):
        """Send job alerts via configured channels"""
        message = f"🚨 Job Alert: {job_count} new jobs found for '{keyword}'"
        
        # Desktop notification
        if self.user_profile.desktop_notifications and self.desktop_callback:
            self.desktop_callback(message)
        
        # Email notification  
        if self.user_profile.email_notifications and self.email_callback:
            self.email_callback(message, self.user_profile.email)
        
        self.logger.info(f"Job alert sent: {message}")


# ===== USAGE EXAMPLES =====

def example_basic_usage():
    """Example of basic scraper manager usage"""
    print("Scraper Manager Example Usage")
    print("=" * 40)
    
    # Initialize components
    db_manager = DatabaseManager("test_scraper_manager.db")
    
    # Note: CV Optimizer requires OpenAI API key
    # cv_optimizer = CVOptimizer("your-api-key-here")
    cv_optimizer = None  # For this example
    
    # Create scraper manager
    with ScraperManager(db_manager, cv_optimizer) as manager:
        
        # Create search query
        search_query = SearchQuery(
            keywords="Python Developer",
            job_types=[JobType.IT_PROGRAMMING],
            locations=["San Francisco", "Remote"],
            remote_only=False,
            salary_min=80000,
            date_posted="week"
        )
        
        # Set up progress tracking
        def progress_callback(progress: float):
            print(f"Progress: {progress:.1f}%")
        
        def status_callback(status: str):
            print(f"Status: {status}")
        
        manager.set_progress_callback(progress_callback)
        manager.set_status_callback(status_callback)
        
        print(f"Searching for: {search_query.keywords}")
        print(f"Job types: {[jt.value for jt in search_query.job_types]}")
        print(f"Locations: {search_query.locations}")
        
        # Execute search (would normally find real jobs)
        try:
            session = manager.search_jobs(search_query)
            
            print(f"\nSearch Results:")
            print(f"Session ID: {session.session_id}")
            print(f"Status: {session.status.value}")
            print(f"Jobs Found: {session.jobs_found}")
            print(f"Jobs Saved: {session.jobs_saved}")
            print(f"Duplicates Removed: {session.duplicates_removed}")
            print(f"Duration: {session.duration:.1f}s")
            print(f"Scrapers Used: {', '.join(session.scrapers_used)}")
            
        except Exception as e:
            print(f"Search failed: {e}")
        
        # Show performance stats
        print("\nPerformance Statistics:")
        stats = manager.get_performance_stats()
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Jobs per Hour: {stats['jobs_per_hour']:.1f}")


def example_advanced_usage():
    """Example of advanced scraper manager features"""
    print("Advanced Scraper Manager Example")
    print("=" * 40)
    
    # Initialize with full setup
    db_manager = DatabaseManager("advanced_test.db")
    
    # Create sample user profile
    from core.database.models import create_sample_user_profile
    user_profile = create_sample_user_profile()
    
    # Initialize intelligent coordinator
    with ScraperManager(db_manager) as manager:
        coordinator = IntelligentSearchCoordinator(manager, db_manager)
        
        print("Executing intelligent job search...")
        
        # This would run an optimized search strategy
        try:
            session = coordinator.execute_smart_search(
                user_profile=user_profile,
                target_job_count=50,
                max_search_time=600  # 10 minutes max
            )
            
            print(f"Smart search completed:")
            print(f"Jobs found: {session.jobs_found}")
            print(f"Jobs saved: {session.jobs_saved}")
            
        except Exception as e:
            print(f"Smart search simulation: {e}")
        
        # Generate performance report
        print("\nGenerating performance report...")
        report = manager.generate_performance_report()
        print(report[:500] + "..." if len(report) > 500 else report)
        
        # Example of job alert system
        print("\nSetting up job alerts...")
        alert_system = JobAlertSystem(manager, user_profile)
        
        print("Job alert system configured for:")
        print(f"- Keywords: {user_profile.notification_keywords}")
        print(f"- Email notifications: {user_profile.email_notifications}")
        print(f"- Desktop notifications: {user_profile.desktop_notifications}")


# ===== INTEGRATION HELPERS =====

def create_production_scraper_manager(db_path: str = "data/job_hunter.db",
                                    openai_api_key: str = None) -> ScraperManager:
    """Create production-ready scraper manager"""
    
    # Initialize database
    db_manager = DatabaseManager(db_path)
    
    # Initialize CV optimizer if API key provided
    cv_optimizer = None
    if openai_api_key:
        from core.ai.cv_optimizer import CVOptimizer
        cv_optimizer = CVOptimizer(openai_api_key)
    
    # Create and configure scraper manager
    manager = ScraperManager(db_manager, cv_optimizer)
    
    # Production settings
    for scraper_name, config in manager.scraper_configs.items():
        config.timeout_seconds = 600  # 10 minutes max per scraper
        config.retry_attempts = 3
        config.config_params.update({
            'headless': True,
            'stealth': True,
            'min_delay': 2.0,
            'max_delay': 5.0
        })
    
    return manager


def setup_automated_job_hunting(user_profile: UserProfile,
                               db_manager: DatabaseManager,
                               cv_optimizer: CVOptimizer) -> tuple[ScraperManager, JobAlertSystem]:
    """Setup complete automated job hunting system"""
    
    # Create scraper manager
    scraper_manager = ScraperManager(db_manager, cv_optimizer)
    
    # Setup job alerts
    alert_system = JobAlertSystem(scraper_manager, user_profile)
    
    # Configure search queries based on user profile
    search_queries = []
    for job_type in user_profile.preferred_job_types:
        if job_type == JobType.IT_PROGRAMMING:
            keywords_list = user_profile.keywords_it or ["software developer"]
        elif job_type == JobType.CIVIL_ENGINEERING:
            keywords_list = user_profile.keywords_civil or ["civil engineer"]
        else:
            keywords_list = ["remote work"]
        
        for keywords in keywords_list[:2]:  # Limit queries
            query = SearchQuery(
                keywords=keywords,
                job_types=[job_type],
                locations=user_profile.preferred_locations,
                remote_only=(user_profile.remote_preference == 'remote')
            )
            search_queries.append(query)
    
    # Schedule regular searches (every 24 hours)
    scraper_manager.schedule_regular_searches(
        search_queries=search_queries,
        interval_hours=24,
        user_profile=user_profile
    )
    
    # Start real-time monitoring
    alert_system.start_monitoring()
    
    return scraper_manager, alert_system


if __name__ == "__main__":
    # Run examples
    print("Running Scraper Manager Examples...")
    print("=" * 50)
    
    try:
        example_basic_usage()
        print("\n" + "=" * 50)
        example_advanced_usage()
    except Exception as e:
        print(f"Example execution error: {e}")
    
    print("\nScraper Manager examples completed!")