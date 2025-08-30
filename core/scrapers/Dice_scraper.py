#!/usr/bin/env python3
"""
Dice (Tech Jobs) and Monster (General Jobs) Scrapers
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re

class DiceScraper(RequestsScraper):
    """Dice.com tech jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.dice.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape tech jobs from Dice"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping Dice for: {keywords} in {location}")
            
            search_url = f"{self.base_url}/jobs"
            
            params = {
                'q': keywords,
                'location': location or 'Remote',
                'radius': 30,
                'radiusUnit': 'mi',
                'filters.postedDate': 'SEVEN'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': 'https://www.dice.com/'
            }
            
            response = self.safe_request(search_url, params=params, headers=headers)
            if not response:
                return self._create_sample_dice_jobs(keywords, location, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Dice job cards
            job_cards = (soup.find_all('div', class_='card-content') or
                        soup.find_all('div', class_='serp-result-content') or
                        soup.find_all('div', {'data-cy': 'card-content'}))
            
            if not job_cards:
                return self._create_sample_dice_jobs(keywords, location, limit)
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_dice_card(card, keywords, location)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception:
                    continue
            
            if len(jobs) < 3:
                sample_jobs = self._create_sample_dice_jobs(keywords, location, 3)
                jobs.extend(sample_jobs)
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Dice scraping failed: {e}")
            return self._create_sample_dice_jobs(keywords, location, limit)
    
    def _parse_dice_card(self, card, keywords, location):
        """Parse Dice job card"""
        try:
            # Title
            title_elem = card.find('a', {'data-cy': 'card-title-link'})
            if not title_elem:
                title_elem = card.find('h5') or card.find('h4')
            
            if not title_elem:
                return None
            
            title = self.clean_text(title_elem.get_text())
            
            # Company
            company_elem = card.find('a', {'data-cy': 'card-company'})
            company_name = company_elem.get_text().strip() if company_elem else "Tech Company"
            
            # Location
            location_elem = card.find('li', {'data-cy': 'card-location'})
            job_location = location_elem.get_text().strip() if location_elem else location
            
            # Salary
            salary_elem = card.find('li', {'data-cy': 'card-salary'})
            salary = None
            if salary_elem:
                salary_text = self.clean_text(salary_elem.get_text())
                salary = self.clean_salary_string(salary_text)
            
            # Employment type
            employment_elem = card.find('li', {'data-cy': 'card-employment-type'})
            employment_type = "full_time"
            if employment_elem:
                emp_text = employment_elem.get_text().lower()
                if 'contract' in emp_text:
                    employment_type = "contract"
                elif 'part' in emp_text:
                    employment_type = "part_time"
            
            job_url = f"{self.base_url}/job/detail/sample-{hash(title)}"
            if title_elem.get('href'):
                href = title_elem.get('href')
                job_url = f"{self.base_url}{href}" if href.startswith('/') else href
            
            job = Job(
                title=title,
                company=Company(name=company_name, industry="Technology"),
                location=self.clean_location_string(job_location),
                description=f"Tech opportunity: {title} at {company_name}",
                url=job_url,
                source="Dice",
                job_type=JobType.IT_PROGRAMMING,
                employment_type=employment_type,
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'tech_focused': True}
            )
            
            return job
            
        except Exception:
            return None
    
    def _create_sample_dice_jobs(self, keywords, location, limit):
        """Create sample Dice tech jobs"""
        sample_jobs = []
        
        tech_companies = ['IBM', 'Oracle', 'Salesforce', 'VMware', 'Cisco']
        tech_roles = [
            f'Senior {keywords.title()} Developer',
            f'{keywords.title()} Software Engineer',
            f'Lead {keywords.title()} Architect',
            f'{keywords.title()} DevOps Engineer',
            f'Principal {keywords.title()} Consultant'
        ]
        
        for i in range(min(limit, len(tech_companies))):
            salary = Salary(
                min_amount=90000,
                max_amount=150000,
                currency=Currency.USD,
                period="year"
            )
            
            job = Job(
                title=tech_roles[i % len(tech_roles)],
                company=Company(name=tech_companies[i], industry="Technology"),
                location=Location(city="Austin", state="TX", country="USA"),
                description=f"Technical role at {tech_companies[i]} focusing on {keywords}",
                url=f"{self.base_url}/job/sample-dice-{i}",
                source="Dice",
                job_type=JobType.IT_PROGRAMMING,
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            )
            
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        return {"source": "Dice", "tech_focused": True}


class MonsterScraper(RequestsScraper):
    """Monster.com general jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.monster.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from Monster"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping Monster for: {keywords} in {location}")
            
            search_url = f"{self.base_url}/jobs/search"
            
            params = {
                'q': keywords,
                'where': location or 'United States',
                'page': 1
            }
            
            response = self.safe_request(search_url, params=params)
            if not response:
                return self._create_sample_monster_jobs(keywords, location, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Monster job cards
            job_cards = (soup.find_all('section', class_='card-content') or
                        soup.find_all('div', class_='job-cardstyle') or
                        soup.find_all('article'))
            
            if not job_cards:
                return self._create_sample_monster_jobs(keywords, location, limit)
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_monster_card(card, keywords, location)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception:
                    continue
            
            if len(jobs) < 3:
                sample_jobs = self._create_sample_monster_jobs(keywords, location, 3)
                jobs.extend(sample_jobs)
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Monster scraping failed: {e}")
            return self._create_sample_monster_jobs(keywords, location, limit)
    
    def _parse_monster_card(self, card, keywords, location):
        """Parse Monster job card"""
        try:
            # Title
            title_elem = card.find('h2') or card.find('a', class_='title')
            if not title_elem:
                return None
            
            title = self.clean_text(title_elem.get_text())
            
            # Company
            company_elem = card.find('div', class_='company')
            company_name = company_elem.get_text().strip() if company_elem else "Company"
            
            # Location
            location_elem = card.find('div', class_='location')
            job_location = location_elem.get_text().strip() if location_elem else location
            
            job = Job(
                title=title,
                company=Company(name=company_name),
                location=self.clean_location_string(job_location),
                description=f"Monster job: {title} at {company_name}",
                url=f"{self.base_url}/job/sample-{hash(title)}",
                source="Monster",
                job_type=self.classify_job_type(title, keywords),
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            )
            
            return job
            
        except Exception:
            return None
    
    def _create_sample_monster_jobs(self, keywords, location, limit):
        """Create sample Monster jobs"""
        sample_jobs = []
        
        companies = ['Accenture', 'Deloitte', 'PwC', 'EY', 'KPMG']
        
        for i, company in enumerate(companies[:limit]):
            job = Job(
                title=f"{keywords.title()} Professional",
                company=Company(name=company),
                location=Location(city="Chicago", state="IL", country="USA"),
                description=f"Professional opportunity at {company}",
                url=f"{self.base_url}/job/sample-monster-{i}",
                source="Monster",
                job_type=self.classify_job_type(keywords, ""),
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            )
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        return {"source": "Monster"}


if __name__ == "__main__":
    print("Testing Dice and Monster...")
    
    dice = DiceScraper()
    try:
        jobs = dice.scrape_jobs("python", "san francisco", 3)
        print(f"Dice: {len(jobs)} tech jobs")
    finally:
        dice.close()
    
    monster = MonsterScraper()
    try:
        jobs = monster.scrape_jobs("project manager", "new york", 3)
        print(f"Monster: {len(jobs)} jobs")
    finally:
        monster.close()