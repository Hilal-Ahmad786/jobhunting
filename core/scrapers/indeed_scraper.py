#!/usr/bin/env python3
"""
Enhanced Indeed Scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re
import time

class IndeedScraper(RequestsScraper):
    """Enhanced Indeed job scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.indeed.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape jobs from Indeed"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping Indeed for: {keywords} in {location}")
            
            # Indeed search URL
            search_url = f"{self.base_url}/jobs"
            
            params = {
                'q': keywords,
                'l': location,
                'limit': min(limit, 50),
                'sort': 'date'
            }
            
            # Make request
            response = self.safe_request(search_url, params=params)
            if not response:
                self.logger.warning("Failed to get Indeed response")
                return []
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find job cards - Indeed has various card formats
            job_cards = (soup.find_all('div', class_='job_seen_beacon') or 
                        soup.find_all('div', class_='result') or
                        soup.find_all('a', {'data-jk': True}))
            
            self.logger.info(f"Found {len(job_cards)} job cards on Indeed")
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_job_card(card, keywords, location)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception as e:
                    self.logger.error(f"Error parsing Indeed job card: {e}")
                    self.stats['jobs_failed'] += 1
                    continue
            
            self.logger.info(f"Successfully scraped {len(jobs)} jobs from Indeed")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Indeed scraping failed: {e}")
            return []
    
    def _parse_job_card(self, card, keywords, location):
        """Parse individual Indeed job card"""
        try:
            # Extract title - Indeed has multiple possible selectors
            title_elem = (card.find('h2', class_='jobTitle') or
                         card.find('a', {'data-jk': True}) or
                         card.find('h2') or
                         card.find('span', {'title': True}))
            
            if not title_elem:
                return None
            
            # Get title text
            if title_elem.name == 'a':
                title = self.clean_text(title_elem.get('title', '') or title_elem.get_text())
            else:
                title_link = title_elem.find('a')
                if title_link:
                    title = self.clean_text(title_link.get_text())
                else:
                    title = self.clean_text(title_elem.get_text())
            
            if not title:
                return None
            
            # Extract company
            company_elem = (card.find('span', class_='companyName') or
                           card.find('div', class_='companyName') or
                           card.find('a', {'data-testid': 'company-name'}))
            
            company_name = "Unknown Company"
            if company_elem:
                # Company might be inside a link
                company_link = company_elem.find('a')
                if company_link:
                    company_name = self.clean_text(company_link.get_text())
                else:
                    company_name = self.clean_text(company_elem.get_text())
            
            # Extract location
            location_elem = (card.find('div', class_='companyLocation') or
                           card.find('span', class_='locationsContainer'))
            
            location_text = location or "Remote"
            if location_elem:
                location_text = self.clean_text(location_elem.get_text())
            
            # Extract salary if available
            salary_elem = card.find('span', class_='salaryText')
            salary = None
            if salary_elem:
                salary_text = self.clean_text(salary_elem.get_text())
                salary = self.clean_salary_string(salary_text)
            
            # Extract job snippet/description
            snippet_elem = (card.find('div', class_='job-snippet') or
                           card.find('div', class_='summary'))
            
            description = f"Indeed job: {title} at {company_name}"
            if snippet_elem:
                snippet = self.clean_text(snippet_elem.get_text())
                description += f"\n\n{snippet}"
            
            # Extract job URL
            job_url = f"{self.base_url}/viewjob?jk=sample-{hash(title + company_name)}"
            
            # Try to get real job URL
            link_elem = card.find('a', {'data-jk': True})
            if link_elem:
                job_id = link_elem.get('data-jk')
                if job_id:
                    job_url = f"{self.base_url}/viewjob?jk={job_id}"
            else:
                # Alternative: look for any href with /viewjob
                all_links = card.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if '/viewjob' in href:
                        if href.startswith('http'):
                            job_url = href
                        else:
                            job_url = f"{self.base_url}{href}"
                        break
            
            # Create job object
            job = Job(
                title=title,
                company=Company(name=company_name),
                location=self.clean_location_string(location_text),
                description=description,
                url=job_url,
                source="Indeed",
                salary=salary,
                job_type=self.classify_job_type(title, description),
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
            self.logger.error(f"Error parsing Indeed job card: {e}")
            return None
    
    def get_job_details(self, job_url):
        """Get detailed job information from Indeed"""
        try:
            response = self.safe_request(job_url)
            if not response:
                return {"source": "Indeed", "error": "Could not fetch details"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract full job description
            description_elem = (soup.find('div', class_='jobsearch-jobDescriptionText') or
                              soup.find('div', id='jobDescriptionText'))
            
            full_description = ""
            if description_elem:
                full_description = self.clean_text(description_elem.get_text())
            
            # Extract job requirements
            requirements = []
            req_sections = soup.find_all('div', class_='jobsearch-ReqAndQualSection')
            for section in req_sections:
                section_text = self.clean_text(section.get_text())
                if section_text:
                    requirements.append(section_text)
            
            # Extract company info
            company_info = {}
            company_section = soup.find('div', class_='jobsearch-CompanyInfoContainer')
            if company_section:
                company_info['description'] = self.clean_text(company_section.get_text())
            
            return {
                "source": "Indeed",
                "full_description": full_description,
                "requirements": requirements,
                "company_info": company_info,
                "scraped_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Indeed job details: {e}")
            return {"source": "Indeed", "error": str(e)}


# Test the scraper
if __name__ == "__main__":
    print("Testing Indeed Scraper...")
    
    scraper = IndeedScraper()
    
    try:
        jobs = scraper.scrape_jobs("software engineer", "new york", 5)
        print(f"Found {len(jobs)} jobs")
        
        for job in jobs:
            print(f"- {job.title} at {job.company.name}")
            if job.salary:
                print(f"  Salary: {job.salary}")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        scraper.close()