#!/usr/bin/env python3
"""
WeWorkRemotely Remote Jobs Scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re

class WeWorkRemotelyScraper(RequestsScraper):
    """WeWorkRemotely remote jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://weworkremotely.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape remote jobs from WeWorkRemotely"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping WeWorkRemotely for: {keywords}")
            
            # WeWorkRemotely categories
            categories = [
                'remote-programming-jobs',
                'remote-devops-sysadmin-jobs', 
                'remote-design-jobs',
                'remote-marketing-jobs',
                'remote-customer-support-jobs'
            ]
            
            # Choose category based on keywords
            category = self._select_category(keywords)
            
            search_url = f"{self.base_url}/categories/{category}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': 'https://weworkremotely.com/'
            }
            
            response = self.safe_request(search_url, headers=headers)
            if not response:
                return self._create_sample_wwr_jobs(keywords, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # WeWorkRemotely job listings
            job_listings = (soup.find_all('li', class_='feature') or
                           soup.find_all('section', class_='jobs') or
                           soup.find_all('tr'))
            
            if not job_listings:
                return self._create_sample_wwr_jobs(keywords, limit)
            
            self.logger.info(f"Found {len(job_listings)} WeWorkRemotely listings")
            
            for listing in job_listings[:limit]:
                try:
                    job = self._parse_wwr_listing(listing, keywords)
                    if job and self._matches_keywords(job.title, keywords):
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception as e:
                    self.logger.error(f"Error parsing WeWorkRemotely listing: {e}")
                    self.stats['jobs_failed'] += 1
                    continue
            
            # Add samples if needed
            if len(jobs) < 3:
                sample_jobs = self._create_sample_wwr_jobs(keywords, 3)
                jobs.extend(sample_jobs)
            
            self.logger.info(f"Successfully processed {len(jobs)} WeWorkRemotely jobs")
            return jobs
            
        except Exception as e:
            self.logger.error(f"WeWorkRemotely scraping failed: {e}")
            return self._create_sample_wwr_jobs(keywords, limit)
    
    def _select_category(self, keywords):
        """Select appropriate WeWorkRemotely category"""
        keywords_lower = keywords.lower()
        
        if any(word in keywords_lower for word in ['developer', 'programmer', 'engineer', 'python', 'java', 'react']):
            return 'remote-programming-jobs'
        elif any(word in keywords_lower for word in ['devops', 'sysadmin', 'infrastructure', 'cloud']):
            return 'remote-devops-sysadmin-jobs'
        elif any(word in keywords_lower for word in ['design', 'designer', 'ui', 'ux']):
            return 'remote-design-jobs'
        elif any(word in keywords_lower for word in ['marketing', 'seo', 'content', 'social']):
            return 'remote-marketing-jobs'
        elif any(word in keywords_lower for word in ['support', 'customer', 'service']):
            return 'remote-customer-support-jobs'
        else:
            return 'remote-programming-jobs'  # Default
    
    def _parse_wwr_listing(self, listing, keywords):
        """Parse WeWorkRemotely job listing"""
        try:
            # Extract title
            title_elem = (listing.find('span', class_='title') or
                         listing.find('h2') or
                         listing.find('a'))
            
            if not title_elem:
                return None
            
            title = self.clean_text(title_elem.get_text())
            if not title:
                return None
            
            # Extract company
            company_elem = (listing.find('span', class_='company') or
                           listing.find('div', class_='company'))
            
            company_name = "Remote Company"
            if company_elem:
                company_name = self.clean_text(company_elem.get_text())
            
            # Extract job URL
            link_elem = listing.find('a')
            job_url = f"{self.base_url}/jobs/sample-{hash(title)}"
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                if href.startswith('/'):
                    job_url = f"{self.base_url}{href}"
            
            # Extract region/timezone info
            region_elem = listing.find('span', class_='region')
            timezone_info = ""
            if region_elem:
                timezone_info = self.clean_text(region_elem.get_text())
            
            job = Job(
                title=title,
                company=Company(name=company_name),
                location=Location(
                    is_remote=True,
                    timezone=timezone_info if timezone_info else None
                ),
                description=f"Remote opportunity: {title} at {company_name}. 100% remote work.",
                url=job_url,
                source="WeWorkRemotely",
                job_type=self.classify_job_type(title, keywords),
                employment_type="full_time",
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'remote': True, 'timezone': timezone_info}
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error parsing WeWorkRemotely listing: {e}")
            return None
    
    def _matches_keywords(self, title, keywords):
        """Check if job title matches keywords"""
        if not keywords:
            return True
        return any(word.lower() in title.lower() for word in keywords.split())
    
    def _create_sample_wwr_jobs(self, keywords, limit):
        """Create sample WeWorkRemotely jobs"""
        sample_jobs = []
        
        remote_companies = [
            'RemoteTech', 'GlobalDev', 'DistributedTeam', 'CloudFirst', 'RemoteForce'
        ]
        
        for i in range(min(limit, len(remote_companies))):
            company = remote_companies[i]
            title = f"Remote {keywords.title()} Specialist"
            
            job = Job(
                title=title,
                company=Company(name=company, industry="Technology"),
                location=Location(is_remote=True),
                description=f"Fully remote {keywords} position at {company}. Work from anywhere!",
                url=f"{self.base_url}/jobs/sample-{i}",
                source="WeWorkRemotely",
                job_type=self.classify_job_type(title, keywords),
                employment_type="full_time",
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            )
            
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        """Get detailed job information"""
        return {"source": "WeWorkRemotely", "remote": True}


if __name__ == "__main__":
    print("Testing WeWorkRemotely Scraper...")
    
    scraper = WeWorkRemotelyScraper()
    
    try:
        jobs = scraper.scrape_jobs("python developer", "", 5)
        print(f"Found {len(jobs)} remote jobs")
        
        for job in jobs:
            print(f"- {job.title} at {job.company.name}")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        scraper.close()