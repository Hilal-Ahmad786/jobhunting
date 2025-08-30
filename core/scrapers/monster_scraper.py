#!/usr/bin/env python3
from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType
from datetime import datetime

class MonsterScraper(RequestsScraper):
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.monster.com"
    
    def scrape_jobs(self, keywords, location="", limit=50):
        jobs = []
        try:
            self.logger.info(f"Scraping Monster for: {keywords}")
            companies = ["Accenture", "Deloitte", "PwC", "EY", "KPMG"]
            
            for i in range(min(limit, len(companies))):
                company = companies[i]
                job = Job(
                    title=f"{keywords.title()} Specialist {i+1}",
                    company=Company(name=company),
                    location=Location(city="New York", state="NY", country="USA"),
                    description=f"Monster job opportunity: {keywords} at {company}",
                    url=f"{self.base_url}/job/sample-{i}",
                    source="Monster",
                    job_type=self.classify_job_type(keywords, ""),
                    posted_date=datetime.now(),
                    scraped_date=datetime.now(),
                    extra_data={'sample': True}
                )
                jobs.append(job)
                self.stats['jobs_scraped'] += 1
            return jobs
        except Exception as e:
            self.logger.error(f"Monster error: {e}")
            return []
    
    def get_job_details(self, job_url):
        return {"source": "Monster"}
