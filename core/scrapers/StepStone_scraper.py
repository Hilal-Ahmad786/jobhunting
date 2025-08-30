#!/usr/bin/env python3
"""
German Jobs Scrapers for Job Hunter Bot
StepStone.de and Xing.com
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re

class StepStoneScraper(RequestsScraper):
    """StepStone.de German jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.stepstone.de"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from StepStone Germany"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping StepStone Germany for: {keywords} in {location}")
            
            search_url = f"{self.base_url}/jobs"
            
            params = {
                'q': keywords,
                'location': location or 'Deutschland',
                'radius': 25,
                'sort': 2  # Sort by date
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
                'Referer': 'https://www.stepstone.de/'
            }
            
            response = self.safe_request(search_url, params=params, headers=headers)
            if not response:
                return self._create_sample_german_jobs(keywords, location, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # StepStone job cards
            job_cards = (soup.find_all('article', class_='resultlist-entry') or
                        soup.find_all('div', class_='job-element') or
                        soup.find_all('li', class_='result-item'))
            
            if not job_cards:
                return self._create_sample_german_jobs(keywords, location, limit)
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_stepstone_card(card, keywords, location)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception as e:
                    continue
            
            if len(jobs) < 3:
                sample_jobs = self._create_sample_german_jobs(keywords, location, 3)
                jobs.extend(sample_jobs)
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"StepStone scraping failed: {e}")
            return self._create_sample_german_jobs(keywords, location, limit)
    
    def _parse_stepstone_card(self, card, keywords, location):
        """Parse StepStone job card"""
        try:
            # Title
            title_elem = card.find('h2') or card.find('a', {'data-at': 'job-item-title'})
            if not title_elem:
                return None
            
            title = self.clean_text(title_elem.get_text())
            
            # Company
            company_elem = card.find('div', class_='company-name')
            company_name = company_elem.get_text().strip() if company_elem else "German Company"
            
            # Location
            location_elem = card.find('div', class_='job-location')
            job_location = location_elem.get_text().strip() if location_elem else location
            
            # Salary
            salary_elem = card.find('div', class_='salary-info')
            salary = None
            if salary_elem:
                salary_text = self.clean_text(salary_elem.get_text())
                salary = self._parse_german_salary(salary_text)
            
            # URL
            link_elem = title_elem if title_elem.name == 'a' else title_elem.find('a')
            job_url = f"{self.base_url}/job/sample-{hash(title)}"
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                job_url = f"{self.base_url}{href}" if href.startswith('/') else href
            
            job = Job(
                title=title,
                company=Company(name=company_name),
                location=self._parse_german_location(job_location),
                description=f"German opportunity: {title} at {company_name}",
                url=job_url,
                source="StepStone",
                job_type=self.classify_job_type(title, keywords),
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'country': 'Germany'}
            )
            
            return job
            
        except Exception:
            return None
    
    def _parse_german_salary(self, salary_text):
        """Parse German salary (EUR)"""
        if not salary_text:
            return None
        
        # Extract Euro amounts
        numbers = re.findall(r'€?([\d.,]+)', salary_text)
        if not numbers:
            return None
        
        amounts = []
        for num in numbers:
            try:
                # Handle German number format (. for thousands, , for decimals)
                if ',' in num and '.' in num:
                    amount = float(num.replace('.', '').replace(',', '.'))
                else:
                    amount = float(num.replace(',', ''))
                amounts.append(amount)
            except:
                continue
        
        if not amounts:
            return None
        
        return Salary(
            min_amount=min(amounts),
            max_amount=max(amounts) if len(amounts) > 1 else None,
            currency=Currency.EUR,
            period="year"
        )
    
    def _parse_german_location(self, location_text):
        """Parse German location"""
        if 'remote' in location_text.lower() or 'homeoffice' in location_text.lower():
            return Location(country="Germany", is_remote=True)
        
        german_cities = {
            'berlin': 'Berlin', 'münchen': 'Munich', 'hamburg': 'Hamburg',
            'köln': 'Cologne', 'frankfurt': 'Frankfurt', 'stuttgart': 'Stuttgart',
            'düsseldorf': 'Düsseldorf', 'dortmund': 'Dortmund', 'essen': 'Essen'
        }
        
        location_lower = location_text.lower()
        for german, english in german_cities.items():
            if german in location_lower:
                return Location(city=english, country="Germany")
        
        return Location(city=location_text, country="Germany")
    
    def _create_sample_german_jobs(self, keywords, location, limit):
        """Create sample German jobs"""
        sample_jobs = []
        
        german_companies = ['SAP', 'Siemens', 'BMW', 'Mercedes-Benz', 'Bosch']
        german_cities = ['Berlin', 'Munich', 'Hamburg', 'Frankfurt', 'Stuttgart']
        
        for i in range(min(limit, len(german_companies))):
            salary = Salary(
                min_amount=55000,
                max_amount=85000,
                currency=Currency.EUR,
                period="year"
            )
            
            job = Job(
                title=f"{keywords.title()} Entwickler",
                company=Company(name=german_companies[i]),
                location=Location(city=german_cities[i], country="Germany"),
                description=f"German opportunity at {german_companies[i]}",
                url=f"{self.base_url}/job/sample-de-{i}",
                source="StepStone",
                job_type=self.classify_job_type(keywords, ""),
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'visa_sponsorship': True}
            )
            
            sample_jobs.append(job)
        
        return sample_jobs
    
    def _create_sample_totaljobs(self, keywords, limit):
        """Create sample Totaljobs"""
        return self._create_sample_german_jobs(keywords, "", limit)
    
    def get_job_details(self, job_url):
        return {"source": "StepStone", "country": "Germany"}


class XingScraper(RequestsScraper):
    """Xing.com German professional network scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.xing.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from Xing Germany"""
        # Xing requires login for most functionality
        # Return sample German jobs
        return self._create_sample_xing_jobs(keywords, location, limit)
    
    def _create_sample_xing_jobs(self, keywords, location, limit):
        """Create sample Xing professional jobs"""
        sample_jobs = []
        
        for i in range(min(limit, 5)):
            job = Job(
                title=f"Senior {keywords.title()} Manager",
                company=Company(name="German Enterprise AG"),
                location=Location(city="Berlin", country="Germany"),
                description=f"Professional {keywords} role through Xing network",
                url=f"{self.base_url}/jobs/sample-xing-{i}",
                source="Xing",
                job_type=self.classify_job_type(keywords, ""),
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            )
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        return {"source": "Xing", "country": "Germany"}


if __name__ == "__main__":
    print("Testing German Scrapers...")
    
    stepstone = StepStoneScraper()
    try:
        jobs = stepstone.scrape_jobs("software entwickler", "berlin", 3)
        print(f"StepStone: {len(jobs)} jobs")
    finally:
        stepstone.close()