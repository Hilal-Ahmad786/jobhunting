#!/usr/bin/env python3
"""
Reed UK jobs scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup

class ReedScraper(RequestsScraper):
    """Reed UK jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.reed.co.uk"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from Reed UK jobs scraper"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping ReedScraper for: {keywords}")
            
            # Create sample jobs for now - replace with real scraping logic
            for i in range(min(limit, 3)):
                job = Job(
                    title=f"{keywords.title()} Position {i+1}",
                    company=Company(name=f"Company {i+1}"),
                    location=Location(is_remote=True),
                    description=f"Sample job from ReedScraper: {keywords}",
                    url=f"{self.base_url}/job/sample-{i}",
                    source="Reed",
                    job_type=self.classify_job_type(keywords, ""),
                    posted_date=datetime.now(),
                    scraped_date=datetime.now(),
                    extra_data={'sample': True}
                )
                jobs.append(job)
                self.stats['jobs_scraped'] += 1
            
            self.logger.info(f"Created {len(jobs)} sample jobs from ReedScraper")
            return jobs
            
        except Exception as e:
            self.logger.error(f"ReedScraper scraping failed: {e}")
            return []
    
    def get_job_details(self, job_url):
        """Get detailed job information"""
        return {"source": "Reed", "sample": True}


if __name__ == "__main__":
    print("Testing ReedScraper...")
    scraper = ReedScraper()
    try:
        jobs = scraper.scrape_jobs("test", "", 2)
        print(f"Found {len(jobs)} jobs")
    finally:
        scraper.close()
