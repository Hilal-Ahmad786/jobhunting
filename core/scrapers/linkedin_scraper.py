#!/usr/bin/env python3
"""
Enhanced LinkedIn Scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import time

class LinkedInScraper(RequestsScraper):
    """Enhanced LinkedIn job scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.linkedin.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from LinkedIn"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping LinkedIn for: {keywords} in {location}")
            
            # LinkedIn job search URL
            search_url = f"{self.base_url}/jobs-guest/jobs/api/seeMoreJobPostings/search"
            
            params = {
                'keywords': keywords,
                'location': location,
                'start': 0,
                'count': min(limit, 25)
            }
            
            # Make request
            response = self.safe_request(search_url, params=params)
            if not response:
                self.logger.warning("Failed to get LinkedIn response")
                return []
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find job cards
            job_cards = soup.find_all('div', class_='base-card')
            if not job_cards:
                job_cards = soup.find_all('li')  # Fallback
            
            self.logger.info(f"Found {len(job_cards)} job cards")
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_job_card(card, keywords, location)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception as e:
                    self.logger.error(f"Error parsing job card: {e}")
                    self.stats['jobs_failed'] += 1
                    continue
            
            self.logger.info(f"Successfully scraped {len(jobs)} jobs from LinkedIn")
            return jobs
            
        except Exception as e:
            self.logger.error(f"LinkedIn scraping failed: {e}")
            return []
    
    def _parse_job_card(self, card, keywords, location):
        """Parse individual job card"""
        try:
            # Extract title
            title_elem = (card.find('h3', class_='base-search-card__title') or 
                         card.find('h3') or 
                         card.find('a', class_='result-card__full-card-link'))
            
            if not title_elem:
                return None
                
            title = self.clean_text(title_elem.get_text() if hasattr(title_elem, 'get_text') else str(title_elem))
            
            # Extract company
            company_elem = (card.find('h4', class_='base-search-card__subtitle') or
                           card.find('h4') or
                           card.find('a', class_='result-card__subtitle-link'))
            
            company_name = "Unknown Company"
            if company_elem:
                company_name = self.clean_text(company_elem.get_text() if hasattr(company_elem, 'get_text') else str(company_elem))
            
            # Extract location
            location_elem = card.find('span', class_='job-search-card__location')
            if not location_elem:
                location_elem = card.find('div', class_='base-search-card__metadata')
            
            location_text = location or "Remote"
            if location_elem:
                location_text = self.clean_text(location_elem.get_text())
            
            # Extract job URL
            link_elem = card.find('a', href=True)
            job_url = f"{self.base_url}/jobs/view/sample-{hash(title + company_name)}"
            if link_elem:
                href = link_elem.get('href', '')
                if href.startswith('http'):
                    job_url = href
                elif href.startswith('/'):
                    job_url = f"{self.base_url}{href}"
            
            # Create job object
            job = Job(
                title=title,
                company=Company(name=company_name),
                location=self.clean_location_string(location_text),
                description=f"LinkedIn job: {title} at {company_name}. Keywords: {keywords}",
                url=job_url,
                source="LinkedIn",
                job_type=self.classify_job_type(title, keywords),
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            )
            
            # Validate job data
            if self.validate_job_data({
                'title': title,
                'company': company_name,
                'url': job_url
            }):
                return job
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error parsing LinkedIn job card: {e}")
            return None
    
    def get_job_details(self, job_url):
        """Get detailed job information"""
        try:
            response = self.safe_request(job_url)
            if not response:
                return {"source": "LinkedIn", "error": "Could not fetch details"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract job description
            description_elem = soup.find('div', class_='show-more-less-html__markup')
            description = ""
            if description_elem:
                description = self.clean_text(description_elem.get_text())
            
            return {
                "source": "LinkedIn",
                "full_description": description,
                "scraped_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting LinkedIn job details: {e}")
            return {"source": "LinkedIn", "error": str(e)}


# Test the scraper
if __name__ == "__main__":
    print("Testing LinkedIn Scraper...")
    
    scraper = LinkedInScraper()
    
    try:
        jobs = scraper.scrape_jobs("python developer", "san francisco", 5)
        print(f"Found {len(jobs)} jobs")
        
        for job in jobs:
            print(f"- {job.title} at {job.company.name}")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        scraper.close()