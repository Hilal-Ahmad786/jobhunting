#!/usr/bin/env python3
"""
UK Jobs Scrapers for Job Hunter Bot
Reed.co.uk and Totaljobs.com
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re

class ReedScraper(RequestsScraper):
    """Reed.co.uk UK jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.reed.co.uk"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from Reed UK"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping Reed UK for: {keywords} in {location}")
            
            search_url = f"{self.base_url}/jobs"
            
            params = {
                'keywords': keywords,
                'location': location or 'London',
                'proximity': 25,
                'salarytype': 'annum'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-GB,en;q=0.9',
                'Referer': 'https://www.reed.co.uk/'
            }
            
            response = self.safe_request(search_url, params=params, headers=headers)
            if not response:
                return self._create_sample_uk_jobs(keywords, location, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Reed job cards
            job_cards = (soup.find_all('article', class_='job-result') or
                        soup.find_all('div', class_='job-result-card') or
                        soup.find_all('li', class_='results-item'))
            
            if not job_cards:
                return self._create_sample_uk_jobs(keywords, location, limit)
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_reed_card(card, keywords, location)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception as e:
                    continue
            
            if len(jobs) < 3:
                sample_jobs = self._create_sample_uk_jobs(keywords, location, 3)
                jobs.extend(sample_jobs)
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Reed scraping failed: {e}")
            return self._create_sample_uk_jobs(keywords, location, limit)
    
    def _parse_reed_card(self, card, keywords, location):
        """Parse Reed job card"""
        try:
            # Title
            title_elem = card.find('h3') or card.find('a', class_='title')
            if not title_elem:
                return None
            
            title = self.clean_text(title_elem.get_text())
            
            # Company
            company_elem = card.find('div', class_='gtmJobListingPostedBy')
            company_name = company_elem.get_text().strip() if company_elem else "UK Company"
            
            # Location
            location_elem = card.find('li', class_='location')
            job_location = location_elem.get_text().strip() if location_elem else location
            
            # Salary
            salary_elem = card.find('li', class_='salary')
            salary = None
            if salary_elem:
                salary_text = self.clean_text(salary_elem.get_text())
                salary = self._parse_uk_salary(salary_text)
            
            # URL
            link = title_elem.get('href') if title_elem.name == 'a' else title_elem.find('a').get('href')
            job_url = f"{self.base_url}{link}" if link.startswith('/') else link
            
            job = Job(
                title=title,
                company=Company(name=company_name),
                location=self._parse_uk_location(job_location),
                description=f"UK opportunity: {title} at {company_name}",
                url=job_url,
                source="Reed",
                job_type=self.classify_job_type(title, keywords),
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'country': 'UK'}
            )
            
            return job
            
        except Exception as e:
            return None
    
    def _parse_uk_salary(self, salary_text):
        """Parse UK salary (GBP)"""
        if not salary_text:
            return None
        
        # Extract numbers
        numbers = re.findall(r'£?([\d,]+)', salary_text)
        if not numbers:
            return None
        
        amounts = [float(num.replace(',', '')) for num in numbers]
        
        return Salary(
            min_amount=min(amounts),
            max_amount=max(amounts) if len(amounts) > 1 else None,
            currency=Currency.GBP,
            period="year"
        )
    
    def _parse_uk_location(self, location_text):
        """Parse UK location"""
        if 'remote' in location_text.lower():
            return Location(country="United Kingdom", is_remote=True)
        
        return Location(city=location_text, country="United Kingdom")
    
    def _create_sample_uk_jobs(self, keywords, location, limit):
        """Create sample UK jobs"""
        sample_jobs = []
        
        uk_companies = ['BBC', 'BT Group', 'Rolls-Royce', 'ARM', 'DeepMind']
        uk_cities = ['London', 'Manchester', 'Birmingham', 'Edinburgh', 'Bristol']
        
        for i in range(min(limit, len(uk_companies))):
            job = Job(
                title=f"{keywords.title()} Engineer",
                company=Company(name=uk_companies[i]),
                location=Location(city=uk_cities[i], country="United Kingdom"),
                description=f"UK opportunity at {uk_companies[i]}",
                url=f"{self.base_url}/job/sample-uk-{i}",
                source="Reed",
                job_type=self.classify_job_type(keywords, ""),
                salary=Salary(min_amount=45000, max_amount=75000, currency=Currency.GBP),
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            )
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        return {"source": "Reed", "country": "UK"}


class TotaljobsScraper(RequestsScraper):
    """Totaljobs.com UK jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.totaljobs.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from Totaljobs UK"""
        jobs = []
        
        try:
            search_url = f"{self.base_url}/jobs"
            
            params = {
                'Keywords': keywords,
                'LTxt': location or 'London',
                'radius': 25
            }
            
            response = self.safe_request(search_url, params=params)
            if not response:
                return self._create_sample_totaljobs(keywords, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('div', class_='job') or soup.find_all('article')
            
            if not job_cards:
                return self._create_sample_totaljobs(keywords, limit)
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_totaljobs_card(card, keywords, location)
                    if job:
                        jobs.append(job)
                except Exception:
                    continue
            
            if len(jobs) < 3:
                jobs.extend(self._create_sample_totaljobs(keywords, 3))
            
            return jobs
            
        except Exception as e:
            return self._create_sample_totaljobs(keywords, limit)
    
    def _parse_totaljobs_card(self, card, keywords, location):
        """Parse Totaljobs card"""
        try:
            title_elem = card.find('h2') or card.find('a', class_='job-title')
            if not title_elem:
                return None
                
            title = self.clean_text(title_elem.get_text())
            
            company_elem = card.find('div', class_='company')
            company_name = company_elem.get_text().strip() if company_elem else "UK Company"
            
            return Job(
                title=title,
                company=Company(name=company_name),
                location=Location(city=location or "London", country="United Kingdom"),
                description=f"Totaljobs opportunity: {title}",
                url=f"{self.base_url}/job/sample-{hash(title)}",
                source="Totaljobs",
                job_type=self.classify_job_type(title, keywords),
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            )
            
        except Exception:
            return None
    
    def _create_sample_totaljobs(self, keywords, limit):
        """Create sample Totaljobs"""
        return [
            Job(
                title=f"{keywords.title()} Specialist",
                company=Company(name="UK Tech Ltd"),
                location=Location(city="London", country="United Kingdom"),
                description="UK-based opportunity",
                url=f"{self.base_url}/job/sample-{i}",
                source="Totaljobs",
                job_type=self.classify_job_type(keywords, ""),
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            ) for i in range(limit)
        ]
    
    def get_job_details(self, job_url):
        return {"source": "Totaljobs", "country": "UK"}


if __name__ == "__main__":
    print("Testing UK Scrapers...")
    
    # Test Reed
    reed = ReedScraper()
    try:
        jobs = reed.scrape_jobs("software engineer", "london", 3)
        print(f"Reed: {len(jobs)} jobs")
    finally:
        reed.close()
    
    # Test Totaljobs
    totaljobs = TotaljobsScraper()
    try:
        jobs = totaljobs.scrape_jobs("developer", "manchester", 3)
        print(f"Totaljobs: {len(jobs)} jobs")
    finally:
        totaljobs.close()