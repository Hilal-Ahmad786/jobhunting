#!/usr/bin/env python3
"""
RemoteOK remote jobs scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup

class RemoteOKScraper(RequestsScraper):
    """RemoteOK remote jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://remoteok.io"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from RemoteOK remote jobs scraper"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping RemoteOKScraper for: {keywords}")
            
            # Create sample jobs for now - replace with real scraping logic
            for i in range(min(limit, 3)):
                job = Job(
                    title=f"{keywords.title()} Position {i+1}",
                    company=Company(name=f"Company {i+1}"),
                    location=Location(is_remote=True),
                    description=f"Sample job from RemoteOKScraper: {keywords}",
                    url=f"{self.base_url}/job/sample-{i}",
                    source="RemoteOK",
                    job_type=self.classify_job_type(keywords, ""),
                    posted_date=datetime.now(),
                    scraped_date=datetime.now(),
                    extra_data={'sample': True}
                )
                jobs.append(job)
                self.stats['jobs_scraped'] += 1
            
            self.logger.info(f"Created {len(jobs)} sample jobs from RemoteOKScraper")
            return jobs
            
        except Exception as e:
            self.logger.error(f"RemoteOKScraper scraping failed: {e}")
            return []
    
    def get_job_details(self, job_url):
        """Get detailed job information"""
        return {"source": "RemoteOK", "sample": True}


if __name__ == "__main__":
    print("Testing RemoteOKScraper...")
    scraper = RemoteOKScraper()
    try:
        jobs = scraper.scrape_jobs("test", "", 2)
        print(f"Found {len(jobs)} jobs")
    finally:
        scraper.close()
