from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType
from datetime import datetime
from bs4 import BeautifulSoup

class IndeedScraper(RequestsScraper):
    def scrape_jobs(self, keywords, location="", limit=50):
        jobs = []
        
        try:
            base_url = "https://www.indeed.com/jobs"
            params = {
                'q': keywords,
                'l': location,
                'limit': min(limit, 50)
            }
            
            response = self.safe_request(base_url, params=params)
            if not response:
                return jobs
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Indeed job cards
            job_cards = soup.find_all('div', class_='job_seen_beacon') or soup.find_all('a', {'data-jk': True})
            
            for card in job_cards[:limit]:
                try:
                    title_elem = card.find('h2') or card.find('span', {'title': True})
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    company_elem = card.find('span', class_='companyName') or card.find('div', class_='companyName')
                    company_name = company_elem.get_text(strip=True) if company_elem else "Unknown"
                    
                    location_elem = card.find('div', class_='companyLocation')
                    location_text = location_elem.get_text(strip=True) if location_elem else location
                    
                    # Get job URL
                    link = card.get('href', '') or card.find('a', href=True)
                    if hasattr(link, 'get'):
                        job_url = f"https://indeed.com{link.get('href', '')}"
                    else:
                        job_url = f"https://indeed.com/viewjob?jk=sample"
                    
                    job = Job(
                        title=title,
                        company=Company(name=company_name),
                        location=self.clean_location_string(location_text),
                        description=f"Indeed job: {title}",
                        url=job_url,
                        source="Indeed",
                        job_type=self.classify_job_type(title, ""),
                        posted_date=datetime.now()
                    )
                    
                    jobs.append(job)
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            self.logger.error(f"Indeed scraping failed: {e}")
        
        return jobs
    
    def get_job_details(self, job_url):
        return {"source": "Indeed"}
