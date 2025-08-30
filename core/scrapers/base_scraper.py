#!/usr/bin/env python3
"""
Base Scraper Class for Job Hunter Bot

This module provides the abstract base class and common functionality 
for all job scrapers. It handles:
- WebDriver management and stealth configuration
- Rate limiting and anti-bot protection
- Error handling and retry logic
- Data validation and cleaning
- Standardized scraping interface
"""

import time
import random
import logging
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from urllib.parse import urljoin, urlparse
import re

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, 
    WebDriverException, StaleElementReferenceException
)

# BeautifulSoup for HTML parsing
from bs4 import BeautifulSoup

# Our data models
from core.database.models import Job, JobType, Company, Location, Salary, JobRequirements, Currency


class ScrapingError(Exception):
    """Custom exception for scraping operations"""
    pass


class RateLimiter:
    """Rate limiting to avoid being blocked"""
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 3.0, requests_per_minute: int = 30):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.requests_per_minute = requests_per_minute
        self.request_times = []
    
    def wait(self):
        """Wait according to rate limit"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # If we've hit the rate limit, wait
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Random delay to appear more human
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
        
        # Record this request
        self.request_times.append(time.time())


class BaseScraper(ABC):
    """
    Abstract base class for all job scrapers
    Provides common functionality and interface that all scrapers must implement
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Core components
        self.driver = None
        self.session = None
        self.rate_limiter = RateLimiter(
            min_delay=self.config.get('min_delay', 1.0),
            max_delay=self.config.get('max_delay', 3.0),
            requests_per_minute=self.config.get('requests_per_minute', 30)
        )
        
        # Scraping statistics
        self.stats = {
            'jobs_scraped': 0,
            'jobs_failed': 0,
            'requests_made': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }
        
        # User agents for rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
        ]
        
        # Initialize scraper
        self.setup()
    
    # ===== ABSTRACT METHODS (Must be implemented by subclasses) =====
    
    @abstractmethod
    def setup(self):
        """Initialize scraper-specific components"""
        pass
    
    @abstractmethod
    def scrape_jobs(self, keywords: str, location: str = "", limit: int = 50) -> List[Job]:
        """
        Scrape jobs from the platform
        
        Args:
            keywords: Search keywords
            location: Target location (optional)
            limit: Maximum number of jobs to scrape
            
        Returns:
            List of Job objects
        """
        pass
    
    @abstractmethod
    def get_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific job
        
        Args:
            job_url: URL of the job posting
            
        Returns:
            Dictionary with detailed job information
        """
        pass
    
    @abstractmethod
    def close(self):
        """Cleanup resources (webdriver, sessions, etc.)"""
        pass
    
    # ===== COMMON UTILITY METHODS =====
    
    def setup_webdriver(self, headless: bool = True, stealth: bool = True) -> webdriver.Chrome:
        """Setup Chrome WebDriver with anti-detection measures"""
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument('--headless=new')
        
        if stealth:
            # Anti-detection options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-extensions')
            
        # Random user agent
        user_agent = random.choice(self.user_agents)
        chrome_options.add_argument(f'--user-agent={user_agent}')
        
        # Window size randomization
        width = random.randint(1200, 1920)
        height = random.randint(800, 1080)
        chrome_options.add_argument(f'--window-size={width},{height}')
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.logger.info("WebDriver initialized successfully")
            return driver
            
        except Exception as e:
            self.logger.error(f"Failed to setup WebDriver: {e}")
            raise ScrapingError(f"WebDriver setup failed: {e}")
    
    def setup_session(self) -> requests.Session:
        """Setup requests session with headers and retries"""
        session = requests.Session()
        
        # Set headers
        session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Setup retry strategy
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        self.logger.info("HTTP Session initialized successfully")
        return session
    
    def safe_request(self, url: str, method: str = 'GET', **kwargs) -> Optional[requests.Response]:
        """Make a safe HTTP request with error handling"""
        try:
            self.rate_limiter.wait()
            
            if method.upper() == 'GET':
                response = self.session.get(url, timeout=30, **kwargs)
            elif method.upper() == 'POST':
                response = self.session.post(url, timeout=30, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            self.stats['requests_made'] += 1
            response.raise_for_status()
            
            return response
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            self.stats['errors'].append(f"Request error: {e}")
            return None
    
    def safe_find_element(self, driver, by: By, value: str, timeout: int = 10) -> Optional[Any]:
        """Safely find element with timeout and error handling"""
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.warning(f"Element not found: {by}={value}")
            return None
        except Exception as e:
            self.logger.error(f"Error finding element {by}={value}: {e}")
            return None
    
    def safe_find_elements(self, driver, by: By, value: str) -> List[Any]:
        """Safely find multiple elements"""
        try:
            elements = driver.find_elements(by, value)
            return elements
        except Exception as e:
            self.logger.error(f"Error finding elements {by}={value}: {e}")
            return []
    
    def extract_text_safe(self, element) -> str:
        """Safely extract text from element"""
        try:
            return element.text.strip() if element else ""
        except StaleElementReferenceException:
            self.logger.warning("Stale element reference encountered")
            return ""
        except Exception as e:
            self.logger.error(f"Error extracting text: {e}")
            return ""
    
    def extract_attribute_safe(self, element, attribute: str) -> str:
        """Safely extract attribute from element"""
        try:
            return element.get_attribute(attribute) if element else ""
        except Exception as e:
            self.logger.error(f"Error extracting attribute {attribute}: {e}")
            return ""
    
    # ===== DATA CLEANING AND VALIDATION =====
    
    def clean_salary_string(self, salary_str: str) -> Optional[Salary]:
        """Parse and clean salary strings from various formats"""
        if not salary_str or salary_str.lower() in ['competitive', 'not specified', 'negotiable']:
            return None
        
        # Remove common prefixes/suffixes
        salary_str = re.sub(r'(salary|pay|compensation|rate)[:;]?\s*', '', salary_str, flags=re.IGNORECASE)
        salary_str = re.sub(r'\s*(per|/)\s*(year|yr|annual|month|hour|hr)\s*', '', salary_str, flags=re.IGNORECASE)
        
        # Extract currency
        currency = Currency.USD  # default
        if '€' in salary_str or 'EUR' in salary_str:
            currency = Currency.EUR
        elif '£' in salary_str or 'GBP' in salary_str:
            currency = Currency.GBP
        elif 'AUD' in salary_str or 'A$' in salary_str:
            currency = Currency.AUD
        elif 'CAD' in salary_str or 'C$' in salary_str:
            currency = Currency.CAD
        
        # Extract numbers
        numbers = re.findall(r'[\d,]+(?:\.\d{2})?', salary_str)
        if not numbers:
            return None
        
        # Convert to floats
        amounts = []
        for num_str in numbers:
            try:
                amount = float(num_str.replace(',', ''))
                # Convert to reasonable scale (handle k, K)
                if 'k' in salary_str.lower() and amount < 1000:
                    amount *= 1000
                amounts.append(amount)
            except ValueError:
                continue
        
        if not amounts:
            return None
        
        # Determine period
        period = "year"
        if any(word in salary_str.lower() for word in ['hour', 'hr', '/h']):
            period = "hour"
        elif any(word in salary_str.lower() for word in ['month', '/m']):
            period = "month"
        elif any(word in salary_str.lower() for word in ['day', '/d']):
            period = "day"
        
        # Create salary object
        if len(amounts) == 1:
            return Salary(min_amount=amounts[0], currency=currency, period=period)
        else:
            return Salary(
                min_amount=min(amounts), 
                max_amount=max(amounts), 
                currency=currency, 
                period=period
            )
    
    def clean_location_string(self, location_str: str) -> Location:
        """Parse and clean location strings"""
        if not location_str:
            return Location()
        
        location_str = location_str.strip()
        
        # Check for remote indicators
        remote_keywords = ['remote', 'worldwide', 'anywhere', 'work from home', 'wfh']
        is_remote = any(keyword in location_str.lower() for keyword in remote_keywords)
        
        # Check for hybrid indicators
        hybrid_keywords = ['hybrid', 'flexible', 'part remote']
        is_hybrid = any(keyword in location_str.lower() for keyword in hybrid_keywords)
        
        if is_remote:
            return Location(is_remote=True)
        
        # Parse location components
        parts = [part.strip() for part in location_str.split(',')]
        
        if len(parts) == 1:
            # Could be city or country
            return Location(city=parts[0], is_hybrid=is_hybrid)
        elif len(parts) == 2:
            # City, Country or City, State
            return Location(city=parts[0], country=parts[1], is_hybrid=is_hybrid)
        elif len(parts) == 3:
            # City, State, Country
            return Location(city=parts[0], state=parts[1], country=parts[2], is_hybrid=is_hybrid)
        else:
            # Take first as city, last as country
            return Location(city=parts[0], country=parts[-1], is_hybrid=is_hybrid)
    
    def extract_skills_from_description(self, description: str) -> List[str]:
        """Extract technical skills from job description"""
        # Common skill keywords for different job types
        skill_patterns = {
            # Programming languages
            'programming': [
                'python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
                'swift', 'kotlin', 'typescript', 'scala', 'r', 'matlab'
            ],
            # Frameworks and libraries
            'frameworks': [
                'react', 'angular', 'vue', 'django', 'flask', 'spring', 'express',
                'laravel', 'rails', 'node.js', 'next.js', '.net', 'tensorflow', 'pytorch'
            ],
            # Databases
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle',
                'sql server', 'sqlite', 'cassandra', 'dynamodb'
            ],
            # Cloud platforms
            'cloud': [
                'aws', 'azure', 'google cloud', 'gcp', 'kubernetes', 'docker',
                'terraform', 'jenkins', 'gitlab', 'github actions'
            ],
            # Civil engineering
            'civil_engineering': [
                'autocad', 'revit', 'civil 3d', 'staad pro', 'etabs', 'safe',
                'primavera', 'ms project', 'tekla', 'bentley microstation',
                'structural analysis', 'concrete design', 'steel design'
            ],
            # Digital marketing
            'marketing': [
                'google analytics', 'adwords', 'facebook ads', 'seo', 'sem',
                'content marketing', 'social media', 'email marketing', 'ppc',
                'conversion optimization', 'a/b testing', 'google tag manager'
            ]
        }
        
        found_skills = []
        description_lower = description.lower()
        
        # Search for skills in description
        for category, skills in skill_patterns.items():
            for skill in skills:
                if skill in description_lower:
                    found_skills.append(skill.title())
        
        return list(set(found_skills))  # Remove duplicates
    
    def validate_job_data(self, job_data: Dict[str, Any]) -> bool:
        """Validate that scraped job data is complete and valid"""
        required_fields = ['title', 'company', 'url']
        
        # Check required fields
        for field in required_fields:
            if not job_data.get(field):
                self.logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate URL
        url = job_data.get('url', '')
        if not self.is_valid_url(url):
            self.logger.warning(f"Invalid URL: {url}")
            return False
        
        # Check title length (reasonable bounds)
        title = job_data.get('title', '')
        if len(title) < 5 or len(title) > 200:
            self.logger.warning(f"Suspicious title length: {len(title)} chars")
            return False
        
        return True
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def normalize_job_data(self, raw_data: Dict[str, Any]) -> Job:
        """Convert raw scraped data to standardized Job object"""
        # Clean and validate data
        title = self.clean_text(raw_data.get('title', ''))
        company_name = self.clean_text(raw_data.get('company', ''))
        description = self.clean_text(raw_data.get('description', ''))
        url = raw_data.get('url', '')
        
        # Create company object
        company = Company(
            name=company_name,
            industry=raw_data.get('industry'),
            size=raw_data.get('company_size'),
            website=raw_data.get('company_website'),
            description=raw_data.get('company_description')
        )
        
        # Parse location
        location = self.clean_location_string(raw_data.get('location', ''))
        
        # Parse salary
        salary = None
        if raw_data.get('salary'):
            salary = self.clean_salary_string(raw_data['salary'])
        
        # Extract requirements and skills
        skills = self.extract_skills_from_description(description)
        requirements = JobRequirements(
            experience_years=raw_data.get('experience_years'),
            education_level=raw_data.get('education_level'),
            skills_required=skills,
            skills_preferred=raw_data.get('preferred_skills', [])
        )
        
        # Determine job type
        job_type = self.classify_job_type(title, description)
        
        return Job(
            title=title,
            company=company,
            location=location,
            description=description,
            url=url,
            source=self.get_source_name(),
            job_type=job_type,
            employment_type=raw_data.get('employment_type', 'full_time'),
            salary=salary,
            requirements=requirements,
            posted_date=raw_data.get('posted_date'),
            application_deadline=raw_data.get('deadline'),
            extra_data=raw_data.get('extra_data', {})
        )
    
    def classify_job_type(self, title: str, description: str) -> JobType:
        """Classify job type based on title and description"""
        text = (title + ' ' + description).lower()
        
        # Civil engineering keywords
        civil_keywords = [
            'civil engineer', 'structural engineer', 'construction engineer',
            'infrastructure', 'bridge design', 'road design', 'building design',
            'concrete', 'steel structure', 'geotechnical', 'surveying',
            'autocad', 'civil 3d', 'revit', 'construction management'
        ]
        
        # IT/Programming keywords
        it_keywords = [
            'developer', 'programmer', 'software engineer', 'full stack',
            'backend', 'frontend', 'devops', 'data scientist', 'machine learning',
            'python', 'java', 'javascript', 'react', 'angular', 'node.js',
            'database', 'api', 'cloud', 'aws', 'azure'
        ]
        
        # Marketing keywords
        marketing_keywords = [
            'digital marketing', 'marketing manager', 'seo', 'sem', 'social media',
            'content marketing', 'email marketing', 'ppc', 'analytics',
            'growth hacker', 'marketing coordinator', 'brand manager'
        ]
        
        # Check for matches
        if any(keyword in text for keyword in civil_keywords):
            return JobType.CIVIL_ENGINEERING
        elif any(keyword in text for keyword in it_keywords):
            return JobType.IT_PROGRAMMING
        elif any(keyword in text for keyword in marketing_keywords):
            return JobType.DIGITAL_MARKETING
        else:
            return JobType.OTHER
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&nbsp;', ' ').replace('&quot;', '"')
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        
        return text
    
    def get_source_name(self) -> str:
        """Get the name of this scraper source"""
        return self.__class__.__name__.replace('Scraper', '')
    
    # ===== SCRAPING WORKFLOW METHODS =====
    
    def start_scraping_session(self):
        """Start a scraping session"""
        self.stats['start_time'] = datetime.now()
        self.stats['jobs_scraped'] = 0
        self.stats['jobs_failed'] = 0
        self.stats['requests_made'] = 0
        self.stats['errors'] = []
        
        self.logger.info(f"Starting scraping session for {self.get_source_name()}")
    
    def end_scraping_session(self):
        """End scraping session and log statistics"""
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        self.logger.info(f"""
        Scraping session completed for {self.get_source_name()}:
        - Duration: {duration:.1f} seconds
        - Jobs scraped: {self.stats['jobs_scraped']}
        - Jobs failed: {self.stats['jobs_failed']}
        - Requests made: {self.stats['requests_made']}
        - Success rate: {(self.stats['jobs_scraped'] / max(1, self.stats['jobs_scraped'] + self.stats['jobs_failed'])) * 100:.1f}%
        - Errors: {len(self.stats['errors'])}
        """)
    
    def handle_scraping_error(self, error: Exception, context: str = ""):
        """Handle scraping errors gracefully"""
        error_msg = f"{context}: {str(error)}" if context else str(error)
        self.logger.error(f"Scraping error in {self.get_source_name()}: {error_msg}")
        
        self.stats['errors'].append(error_msg)
        self.stats['jobs_failed'] += 1
        
        # Implement backoff strategy
        if len(self.stats['errors']) > 10:
            self.logger.warning("Too many errors, implementing backoff...")
            time.sleep(30)  # Wait 30 seconds before continuing
    
    def retry_with_backoff(self, func, max_retries: int = 3, base_delay: float = 1.0):
        """Retry function with exponential backoff"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                time.sleep(delay)
    
    # ===== CONTEXT MANAGERS =====
    
    def __enter__(self):
        """Context manager entry"""
        self.start_scraping_session()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.end_scraping_session()
        self.close()
        
        if exc_type:
            self.logger.error(f"Scraping session ended with exception: {exc_val}")
        
        return False  # Don't suppress exceptions


# ===== SPECIALIZED BASE CLASSES =====

class WebDriverScraper(BaseScraper):
    """Base class for scrapers that use Selenium WebDriver"""
    
    def setup(self):
        """Setup WebDriver"""
        self.driver = self.setup_webdriver(
            headless=self.config.get('headless', True),
            stealth=self.config.get('stealth', True)
        )
    
    def close(self):
        """Close WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("WebDriver closed successfully")
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {e}")


class RequestsScraper(BaseScraper):
    """Base class for scrapers that use requests/BeautifulSoup"""
    
    def setup(self):
        """Setup HTTP session"""
        self.session = self.setup_session()
    
    def close(self):
        """Close HTTP session"""
        if self.session:
            self.session.close()
            self.logger.info("HTTP session closed successfully")
    
    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Get BeautifulSoup object for URL"""
        response = self.safe_request(url)
        if response:
            return BeautifulSoup(response.content, 'html.parser')
        return None


class HybridScraper(BaseScraper):
    """Base class for scrapers that use both WebDriver and requests"""
    
    def setup(self):
        """Setup both WebDriver and HTTP session"""
        self.driver = self.setup_webdriver(
            headless=self.config.get('headless', True),
            stealth=self.config.get('stealth', True)
        )
        self.session = self.setup_session()
    
    def close(self):
        """Close both WebDriver and HTTP session"""
        if self.driver:
            self.driver.quit()
        if self.session:
            self.session.close()
        self.logger.info("All scraper resources closed successfully")


# ===== UTILITY FUNCTIONS =====

def create_scraper_config(
    headless: bool = True,
    stealth: bool = True,
    min_delay: float = 1.0,
    max_delay: float = 3.0,
    requests_per_minute: int = 30,
    timeout: int = 30,
    **kwargs
) -> Dict[str, Any]:
    """Create standard scraper configuration"""
    return {
        'headless': headless,
        'stealth': stealth,
        'min_delay': min_delay,
        'max_delay': max_delay,
        'requests_per_minute': requests_per_minute,
        'timeout': timeout,
        **kwargs
    }


def test_scraper_capabilities():
    """Test base scraper functionality"""
    print("Testing Base Scraper Capabilities")
    print("=" * 40)
    
    # Create a test scraper (we'll use RequestsScraper for testing)
    class TestScraper(RequestsScraper):
        def scrape_jobs(self, keywords: str, location: str = "", limit: int = 50) -> List[Job]:
            return []
        
        def get_job_details(self, job_url: str) -> Optional[Dict[str, Any]]:
            return {}
    
    config = create_scraper_config(requests_per_minute=10)
    
    with TestScraper(config) as scraper:
        # Test salary parsing
        salary_tests = [
            "$80,000 - $120,000 per year",
            "€60k - €80k",
            "£45,000 annually",
            "$50/hour",
            "Competitive salary"
        ]
        
        print("Testing salary parsing:")
        for test_salary in salary_tests:
            parsed = scraper.clean_salary_string(test_salary)
            print(f"  {test_salary} → {parsed}")
        
        # Test location parsing
        location_tests = [
            "Remote",
            "San Francisco, CA, USA",
            "London, UK",
            "Sydney, Australia",
            "Hybrid - Berlin, Germany"
        ]
        
        print("\nTesting location parsing:")
        for test_location in location_tests:
            parsed = scraper.clean_location_string(test_location)
            print(f"  {test_location} → {parsed}")
        
        # Test skill extraction
        description_test = """
        We are looking for a Senior Python Developer with experience in Django and React.
        The candidate should have knowledge of AWS, PostgreSQL, and Docker.
        Experience with AutoCAD and Civil 3D is a plus for infrastructure projects.
        Knowledge of Google Analytics and SEO would be beneficial.
        """
        
        print("\nTesting skill extraction:")
        skills = scraper.extract_skills_from_description(description_test)
        print(f"  Extracted skills: {', '.join(skills)}")
        
        # Test job classification
        test_titles = [
            "Senior Civil Engineer - Bridge Design",
            "Python Full Stack Developer",
            "Digital Marketing Manager",
            "Freelance Web Designer"
        ]
        
        print("\nTesting job classification:")
        for title in test_titles:
            job_type = scraper.classify_job_type(title, "")
            print(f"  {title} → {job_type.value}")


if __name__ == "__main__":
    # Run tests
    test_scraper_capabilities()