#!/usr/bin/env python3
"""
Dice tech jobs scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup

class DiceScraper(RequestsScraper):
    """Dice tech jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.dice.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from Dice tech jobs scraper"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping DiceScraper for: {keywords}")
            
            # Create sample jobs for now - replace with real scraping logic
            for i in range(min(limit, 3)):
                job = Job(
                    title=f"{keywords.title()} Position {i+1}",
                    company=Company(name=f"Company {i+1}"),
                    location=Location(is_remote=True),
                    description=f"Sample job from DiceScraper: {keywords}",
                    url=f"{self.base_url}/job/sample-{i}",
                    source="Dice",
                    job_type=self.classify_job_type(keywords, ""),
                    posted_date=datetime.now(),
                    scraped_date=datetime.now(),
                    extra_data={'sample': True}
                )
                jobs.append(job)
                self.stats['jobs_scraped'] += 1
            
            self.logger.info(f"Created {len(jobs)} sample jobs from DiceScraper")
            return jobs
            
        except Exception as e:
            self.logger.error(f"DiceScraper scraping failed: {e}")
            return []
    
    def get_job_details(self, job_url):
        """Get detailed job information"""
        return {"source": "Dice", "sample": True}


if __name__ == "__main__":
    print("Testing DiceScraper...")
    scraper = DiceScraper()
    try:
        jobs = scraper.scrape_jobs("test", "", 2)
        print(f"Found {len(jobs)} jobs")
    finally:
        scraper.close()
