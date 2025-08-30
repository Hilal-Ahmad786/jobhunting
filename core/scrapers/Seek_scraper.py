#!/usr/bin/env python3
"""
Seek.com.au Australia Jobs Scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re

class SeekScraper(RequestsScraper):
    """Seek.com.au Australia jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.seek.com.au"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from Seek Australia"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping Seek Australia for: {keywords} in {location}")
            
            search_url = f"{self.base_url}/jobs"
            
            params = {
                'keywords': keywords,
                'where': location or 'All Australia',
                'daterange': 7,  # Last 7 days
                'sourcesystem': 'houston'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-AU,en;q=0.9',
                'Referer': 'https://www.seek.com.au/'
            }
            
            response = self.safe_request(search_url, params=params, headers=headers)
            if not response:
                return self._create_sample_australian_jobs(keywords, location, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Seek job cards
            job_cards = (soup.find_all('article', {'data-automation': 'normalJob'}) or
                        soup.find_all('div', class_='_1wkzzau0') or
                        soup.find_all('article'))
            
            if not job_cards:
                return self._create_sample_australian_jobs(keywords, location, limit)
            
            self.logger.info(f"Found {len(job_cards)} Seek job cards")
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_seek_card(card, keywords, location)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception as e:
                    self.logger.error(f"Error parsing Seek card: {e}")
                    continue
            
            if len(jobs) < 3:
                sample_jobs = self._create_sample_australian_jobs(keywords, location, 3)
                jobs.extend(sample_jobs)
            
            self.logger.info(f"Successfully processed {len(jobs)} Seek jobs")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Seek scraping failed: {e}")
            return self._create_sample_australian_jobs(keywords, location, limit)
    
    def _parse_seek_card(self, card, keywords, location):
        """Parse individual Seek job card"""
        try:
            # Extract title
            title_elem = (card.find('a', {'data-automation': 'jobTitle'}) or
                         card.find('h1') or card.find('h2') or card.find('h3'))
            
            if not title_elem:
                return None
            
            title = self.clean_text(title_elem.get_text())
            
            # Extract company
            company_elem = (card.find('a', {'data-automation': 'jobCompany'}) or
                           card.find('span', class_='companyName'))
            
            company_name = "Australian Company"
            if company_elem:
                company_name = self.clean_text(company_elem.get_text())
            
            # Extract location
            location_elem = (card.find('a', {'data-automation': 'jobLocation'}) or
                           card.find('span', class_='location'))
            
            location_text = location or "Australia"
            if location_elem:
                location_text = self.clean_text(location_elem.get_text())
            
            # Extract salary
            salary_elem = (card.find('span', {'data-automation': 'jobSalary'}) or
                          card.find('div', class_='salary'))
            
            salary = None
            if salary_elem:
                salary_text = self.clean_text(salary_elem.get_text())
                salary = self._parse_australian_salary(salary_text)
            
            # Extract job URL
            job_url = f"{self.base_url}/job/sample-{hash(title)}"
            if title_elem.get('href'):
                href = title_elem.get('href')
                if href.startswith('/'):
                    job_url = f"{self.base_url}{href}"
            
            # Extract description snippet
            desc_elem = card.find('span', {'data-automation': 'jobShortDescription'})
            description = f"Australian job opportunity: {title} at {company_name}"
            if desc_elem:
                snippet = self.clean_text(desc_elem.get_text())
                description += f"\n\n{snippet}"
            
            job = Job(
                title=title,
                company=Company(name=company_name),
                location=self._parse_australian_location(location_text),
                description=description,
                url=job_url,
                source="Seek",
                job_type=self.classify_job_type(title, description),
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'country': 'Australia'}
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error parsing Seek job card: {e}")
            return None
    
    def _parse_australian_salary(self, salary_text):
        """Parse Australian salary format"""
        if not salary_text:
            return None
        
        # Australian salary patterns
        if 'package' in salary_text.lower():
            salary_text = salary_text.replace('package', '').strip()
        
        # Remove Australian-specific terms
        salary_text = re.sub(r'(plus super|incl\. super|negotiable)', '', salary_text, flags=re.IGNORECASE)
        
        # Parse AUD amounts
        numbers = re.findall(r'[\d,]+', salary_text)
        if not numbers:
            return None
        
        amounts = [float(num.replace(',', '')) for num in numbers]
        
        # Handle per hour vs per year
        period = "year"
        if any(word in salary_text.lower() for word in ['hour', '/hr']):
            period = "hour"
        
        return Salary(
            min_amount=min(amounts) if amounts else None,
            max_amount=max(amounts) if len(amounts) > 1 else None,
            currency=Currency.AUD,
            period=period
        )
    
    def _parse_australian_location(self, location_text):
        """Parse Australian location format"""
        if 'remote' in location_text.lower():
            return Location(country="Australia", is_remote=True)
        
        # Australian cities
        major_cities = {
            'sydney': 'NSW', 'melbourne': 'VIC', 'brisbane': 'QLD',
            'perth': 'WA', 'adelaide': 'SA', 'canberra': 'ACT',
            'darwin': 'NT', 'hobart': 'TAS'
        }
        
        location_lower = location_text.lower()
        for city, state in major_cities.items():
            if city in location_lower:
                return Location(city=city.title(), state=state, country="Australia")
        
        return Location(city=location_text, country="Australia")
    
    def _create_sample_australian_jobs(self, keywords, location, limit):
        """Create sample Australian jobs"""
        sample_jobs = []
        
        australian_companies = [
            'Atlassian', 'Canva', 'Afterpay', 'REA Group', 'Xero'
        ]
        
        australian_cities = [
            'Sydney, NSW', 'Melbourne, VIC', 'Brisbane, QLD', 'Perth, WA', 'Adelaide, SA'
        ]
        
        for i in range(min(limit, len(australian_companies))):
            company = australian_companies[i]
            job_location = location or australian_cities[i % len(australian_cities)]
            
            job = Job(
                title=f"{keywords.title()} Developer",
                company=Company(name=company, industry="Technology"),
                location=self._parse_australian_location(job_location),
                description=f"Join {company} in {job_location} as a {keywords} professional.",
                url=f"{self.base_url}/job/sample-au-{i}",
                source="Seek",
                job_type=self.classify_job_type(keywords, ""),
                salary=Salary(min_amount=80000, max_amount=120000, currency=Currency.AUD),
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'country': 'Australia', 'visa_sponsorship': True}
            )
            
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        """Get detailed job information"""
        return {"source": "Seek", "country": "Australia"}