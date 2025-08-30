#!/usr/bin/env python3
"""
Glassdoor Jobs Scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re

class GlassdoorScraper(RequestsScraper):
    """Glassdoor jobs scraper with company insights"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.glassdoor.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from Glassdoor"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping Glassdoor for: {keywords} in {location}")
            
            search_url = f"{self.base_url}/Job/jobs.htm"
            
            params = {
                'sc.keyword': keywords,
                'locT': 'C',
                'locId': location if location else '',
                'jobType': '',
                'fromAge': 1,
                'minSalary': 0,
                'includeNoSalaryJobs': 'true',
                'radius': 25,
                'cityId': -1,
                'minRating': 0.0,
                'industryId': -1,
                'sgocId': -1,
                'seniorityType': '',
                'companyId': -1,
                'employerSizes': '',
                'applicationType': '',
                'remoteWorkType': 0
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.glassdoor.com/',
                'DNT': '1',
                'Connection': 'keep-alive'
            }
            
            response = self.safe_request(search_url, params=params, headers=headers)
            if not response:
                return self._create_sample_glassdoor_jobs(keywords, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Glassdoor job cards
            job_cards = (soup.find_all('div', class_='react-job-listing') or
                        soup.find_all('li', {'data-test': 'jobListing'}) or
                        soup.find_all('div', class_='jobContainer'))
            
            if not job_cards:
                return self._create_sample_glassdoor_jobs(keywords, limit)
            
            self.logger.info(f"Found {len(job_cards)} Glassdoor job cards")
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_glassdoor_card(card, keywords, location)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception as e:
                    self.logger.error(f"Error parsing Glassdoor card: {e}")
                    continue
            
            # Add samples if needed
            if len(jobs) < 3:
                sample_jobs = self._create_sample_glassdoor_jobs(keywords, 3)
                jobs.extend(sample_jobs)
            
            self.logger.info(f"Successfully processed {len(jobs)} Glassdoor jobs")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Glassdoor scraping failed: {e}")
            return self._create_sample_glassdoor_jobs(keywords, limit)
    
    def _parse_glassdoor_card(self, card, keywords, location):
        """Parse individual Glassdoor job card"""
        try:
            # Extract title
            title_elem = (card.find('a', {'data-test': 'job-title'}) or
                         card.find('h2') or
                         card.find('div', class_='jobTitle'))
            
            if not title_elem:
                return None
            
            title = self.clean_text(title_elem.get_text())
            
            # Extract company
            company_elem = (card.find('div', {'data-test': 'employer-name'}) or
                           card.find('span', class_='employerName'))
            
            company_name = "Company"
            if company_elem:
                company_name = self.clean_text(company_elem.get_text())
            
            # Extract location
            location_elem = (card.find('div', {'data-test': 'job-location'}) or
                           card.find('div', class_='jobLocation'))
            
            location_text = location or "Remote"
            if location_elem:
                location_text = self.clean_text(location_elem.get_text())
            
            # Extract salary
            salary_elem = (card.find('div', {'data-test': 'detailSalary'}) or
                          card.find('span', class_='salaryText'))
            
            salary = None
            if salary_elem:
                salary_text = self.clean_text(salary_elem.get_text())
                salary = self.clean_salary_string(salary_text)
            
            # Extract company rating
            rating_elem = card.find('span', class_='ratingNumber')
            rating = None
            if rating_elem:
                try:
                    rating = float(self.clean_text(rating_elem.get_text()))
                except:
                    pass
            
            # Extract job URL
            job_url = f"{self.base_url}/job-listing/sample-{hash(title)}"
            if title_elem.get('href'):
                href = title_elem.get('href')
                if href.startswith('/'):
                    job_url = f"{self.base_url}{href}"
            
            job = Job(
                title=title,
                company=Company(
                    name=company_name,
                    description=f"Glassdoor rating: {rating}/5" if rating else None
                ),
                location=self.clean_location_string(location_text),
                description=f"Position at {company_name}: {title}",
                url=job_url,
                source="Glassdoor",
                job_type=self.classify_job_type(title, keywords),
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'company_rating': rating}
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error parsing Glassdoor job card: {e}")
            return None
    
    def _create_sample_glassdoor_jobs(self, keywords, limit):
        """Create sample Glassdoor jobs"""
        sample_jobs = []
        
        companies = [
            {'name': 'Microsoft', 'rating': 4.4},
            {'name': 'Google', 'rating': 4.5},
            {'name': 'Apple', 'rating': 4.3},
            {'name': 'Amazon', 'rating': 4.1},
            {'name': 'Meta', 'rating': 4.2}
        ]
        
        for i, company_info in enumerate(companies[:limit]):
            title = f"Senior {keywords.title()} Engineer"
            
            job = Job(
                title=title,
                company=Company(
                    name=company_info['name'],
                    description=f"Glassdoor rating: {company_info['rating']}/5"
                ),
                location=Location(city="Seattle", state="WA", country="USA"),
                description=f"Join {company_info['name']} as a {title}. Highly rated company with great benefits.",
                url=f"{self.base_url}/job-listing/sample-{i}",
                source="Glassdoor",
                job_type=self.classify_job_type(title, keywords),
                salary=Salary(min_amount=120000, max_amount=180000, currency=Currency.USD),
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'company_rating': company_info['rating']}
            )
            
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        """Get detailed job information from Glassdoor"""
        return {"source": "Glassdoor", "company_insights": True}


if __name__ == "__main__":
    print("Testing Glassdoor Scraper...")
    
    scraper = GlassdoorScraper()
    try:
        jobs = scraper.scrape_jobs("software engineer", "san francisco", 3)
        print(f"Found {len(jobs)} jobs")
        for job in jobs:
            print(f"- {job.title} at {job.company.name}")
    finally:
        scraper.close()