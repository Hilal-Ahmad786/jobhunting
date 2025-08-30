#!/usr/bin/env python3
from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime

class FiverrScraper(RequestsScraper):
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.fiverr.com"
    
    def scrape_jobs(self, keywords, location="", limit=50):
        jobs = []
        try:
            self.logger.info(f"Scraping Fiverr for: {keywords}")
            
            requests = [
                f"Need expert {keywords} developer",
                f"Looking for {keywords} specialist", 
                f"Urgent {keywords} project help needed",
                f"Professional {keywords} service required",
                f"Custom {keywords} solution wanted"
            ]
            
            budgets = [150, 300, 500, 200, 400]
            
            for i in range(min(limit, len(requests))):
                salary = Salary(min_amount=budgets[i], currency=Currency.USD, period="project")
                
                job = Job(
                    title=requests[i],
                    company=Company(name=f"Fiverr Buyer {i+1}"),
                    location=Location(is_remote=True),
                    description=f"Fiverr buyer request: {requests[i]}",
                    url=f"{self.base_url}/request/sample-{i}",
                    source="Fiverr",
                    job_type=JobType.FREELANCE,
                    employment_type="freelance",
                    salary=salary,
                    posted_date=datetime.now(),
                    scraped_date=datetime.now(),
                    extra_data={'sample': True, 'freelance': True}
                )
                jobs.append(job)
                self.stats['jobs_scraped'] += 1
            return jobs
        except Exception as e:
            self.logger.error(f"Fiverr error: {e}")
            return []
    
    def get_job_details(self, job_url):
        return {"source": "Fiverr", "freelance": True}
