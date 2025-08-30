from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re

class LinkedInScraper(RequestsScraper):
    def scrape_jobs(self, keywords, location="", limit=50):
        jobs = []
        
        try:
            # LinkedIn public job search URL
            base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
            params = {
                'keywords': keywords,
                'location': location,
                'start': 0,
                'count': min(limit, 25)
            }
            
            response = self.safe_request(base_url, params=params)
            if not response:
                return jobs
            
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('li')
            
            for card in job_cards[:limit]:
                try:
                    title_elem = card.find('h3')
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    company_elem = card.find('h4')
                    company_name = company_elem.get_text(strip=True) if company_elem else "Unknown Company"
                    
                    location_elem = card.find('span', class_='job-search-card__location')
                    location_text = location_elem.get_text(strip=True) if location_elem else location
                    
                    link_elem = card.find('a')
                    job_url = link_elem.get('href', '') if link_elem else ''
                    
                    job = Job(
                        title=title,
                        company=Company(name=company_name),
                        location=self.clean_location_string(location_text),
                        description=f"LinkedIn job: {title}",
                        url=job_url,
                        source="LinkedIn",
                        job_type=self.classify_job_type(title, ""),
                        posted_date=datetime.now()
                    )
                    
                    jobs.append(job)
                    
                except Exception as e:
                    self.logger.error(f"Error processing job card: {e}")
                    continue
            
        except Exception as e:
            self.logger.error(f"LinkedIn scraping failed: {e}")
        
        return jobs
    
    def get_job_details(self, job_url):
        return {"source": "LinkedIn"}
