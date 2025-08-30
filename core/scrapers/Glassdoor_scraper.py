#!/usr/bin/env python3
from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime

class GlassdoorScraper(RequestsScraper):
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.glassdoor.com"
    
    def scrape_jobs(self, keywords, location="", limit=50):
        jobs = []
        try:
            self.logger.info(f"Scraping Glassdoor for: {keywords}")
            companies = ["Microsoft", "Google", "Apple", "Amazon", "Meta"]
            
            for i in range(min(limit, len(companies))):
                company = companies[i]
                salary = Salary(min_amount=80000, max_amount=150000, currency=Currency.USD)
                
                job = Job(
                    title=f"{keywords.title()} Engineer {i+1}",
                    company=Company(name=company, description=f"Glassdoor rating: 4.{4+i}/5"),
                    location=Location(city="San Francisco", state="CA", country="USA"),
                    description=f"Glassdoor opportunity: {keywords} at {company}",
                    url=f"{self.base_url}/job/sample-{i}",
                    source="Glassdoor",
                    job_type=self.classify_job_type(keywords, ""),
                    salary=salary,
                    posted_date=datetime.now(),
                    scraped_date=datetime.now(),
                    extra_data={'sample': True, 'company_rating': f"4.{4+i}"}
                )
                jobs.append(job)
                self.stats['jobs_scraped'] += 1
            return jobs
        except Exception as e:
            self.logger.error(f"Glassdoor error: {e}")
            return []
    
    def get_job_details(self, job_url):
        return {"source": "Glassdoor", "company_reviews": True}
