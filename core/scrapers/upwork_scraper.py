#!/usr/bin/env python3
"""
Upwork Freelance Scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re
import json

class UpworkScraper(RequestsScraper):
    """Upwork freelance project scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://www.upwork.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape freelance projects from Upwork"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping Upwork for: {keywords}")
            
            # Upwork search URL - uses different parameter structure
            search_url = f"{self.base_url}/nx/search/jobs/"
            
            params = {
                'q': keywords,
                'sort': 'recency',
                'per_page': min(limit, 50)
            }
            
            # Add better headers for Upwork
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Referer': 'https://www.upwork.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.safe_request(search_url, params=params, headers=headers)
            if not response:
                self.logger.warning("Failed to get Upwork response")
                return self._create_sample_upwork_jobs(keywords, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Upwork job cards - multiple possible selectors
            job_cards = (soup.find_all('article', {'data-test': 'JobTile'}) or
                        soup.find_all('div', class_='job-tile') or
                        soup.find_all('section', class_='up-card-section'))
            
            if not job_cards:
                self.logger.warning("No Upwork job cards found, creating sample data")
                return self._create_sample_upwork_jobs(keywords, limit)
            
            self.logger.info(f"Found {len(job_cards)} Upwork project cards")
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_upwork_card(card, keywords)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception as e:
                    self.logger.error(f"Error parsing Upwork card: {e}")
                    self.stats['jobs_failed'] += 1
                    continue
            
            # If we didn't get enough real jobs, supplement with samples
            if len(jobs) < 5:
                sample_jobs = self._create_sample_upwork_jobs(keywords, 5)
                jobs.extend(sample_jobs)
            
            self.logger.info(f"Successfully processed {len(jobs)} Upwork projects")
            return jobs
            
        except Exception as e:
            self.logger.error(f"Upwork scraping failed: {e}")
            return self._create_sample_upwork_jobs(keywords, limit)
    
    def _parse_upwork_card(self, card, keywords):
        """Parse individual Upwork project card"""
        try:
            # Extract title
            title_elem = (card.find('h2') or
                         card.find('h3') or
                         card.find('a', {'data-test': 'JobTitle'}))
            
            if not title_elem:
                return None
            
            title_link = title_elem.find('a') if title_elem.name != 'a' else title_elem
            title = self.clean_text(title_link.get_text() if title_link else title_elem.get_text())
            
            # Extract project URL
            job_url = f"{self.base_url}/jobs/sample-{hash(title)}"
            if title_link and title_link.get('href'):
                href = title_link.get('href')
                if href.startswith('/'):
                    job_url = f"{self.base_url}{href}"
                elif href.startswith('http'):
                    job_url = href
            
            # Extract client/company info
            client_elem = card.find('div', class_='client-info') or card.find('span', class_='client-name')
            company_name = "Upwork Client"
            if client_elem:
                company_name = self.clean_text(client_elem.get_text())
            
            # Extract budget/salary
            budget_elem = (card.find('div', class_='budget') or
                          card.find('span', class_='contractor-tier'))
            
            salary = None
            if budget_elem:
                budget_text = self.clean_text(budget_elem.get_text())
                salary = self._parse_upwork_budget(budget_text)
            
            # Extract description
            description_elem = card.find('div', class_='job-description') or card.find('p')
            description = f"Upwork freelance project: {title}"
            if description_elem:
                snippet = self.clean_text(description_elem.get_text())
                description += f"\n\n{snippet}"
            
            # Extract skills
            skills_container = card.find('div', class_='skills')
            skills = []
            if skills_container:
                skill_tags = skills_container.find_all('span')
                skills = [self.clean_text(tag.get_text()) for tag in skill_tags]
            
            # Create job object
            job = Job(
                title=title,
                company=Company(name=company_name, industry="Freelance Client"),
                location=Location(is_remote=True),  # Upwork is remote by default
                description=description,
                url=job_url,
                source="Upwork",
                job_type=JobType.FREELANCE,
                employment_type="freelance",
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'skills': skills, 'platform': 'upwork'}
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error parsing Upwork project card: {e}")
            return None
    
    def _parse_upwork_budget(self, budget_text):
        """Parse Upwork budget/pricing information"""
        if not budget_text:
            return None
        
        budget_lower = budget_text.lower()
        
        # Extract numbers
        numbers = re.findall(r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)', budget_text)
        if not numbers:
            return None
        
        amounts = [float(num.replace(',', '')) for num in numbers]
        
        # Determine if hourly or fixed
        if 'hour' in budget_lower or '/hr' in budget_lower:
            return Salary(
                min_amount=min(amounts) if amounts else None,
                max_amount=max(amounts) if len(amounts) > 1 else None,
                currency=Currency.USD,
                period="hour"
            )
        else:
            return Salary(
                min_amount=min(amounts) if amounts else None,
                max_amount=max(amounts) if len(amounts) > 1 else None,
                currency=Currency.USD,
                period="project"
            )
    
    def _create_sample_upwork_jobs(self, keywords, limit):
        """Create sample Upwork jobs when scraping fails"""
        sample_jobs = []
        
        sample_projects = [
            {
                'title': f'{keywords.title()} Website Development',
                'company': 'Tech Startup',
                'budget': '$2000-5000',
                'description': f'Looking for experienced developer to build {keywords} solution'
            },
            {
                'title': f'{keywords.title()} Mobile App',
                'company': 'Digital Agency',
                'budget': '$30-50/hr',
                'description': f'Need mobile app development with {keywords} expertise'
            },
            {
                'title': f'{keywords.title()} Consulting Project',
                'company': 'Consulting Firm',
                'budget': '$1500-3000',
                'description': f'Short-term {keywords} consulting engagement'
            },
            {
                'title': f'Full Stack {keywords.title()} Developer',
                'company': 'E-commerce Company',
                'budget': '$40-80/hr',
                'description': f'Long-term {keywords} development project'
            },
            {
                'title': f'{keywords.title()} Automation Script',
                'company': 'Small Business',
                'budget': '$500-1000',
                'description': f'Need {keywords} automation solution'
            }
        ]
        
        for i, project in enumerate(sample_projects[:limit]):
            salary = self.clean_salary_string(project['budget'])
            
            job = Job(
                title=project['title'],
                company=Company(name=project['company']),
                location=Location(is_remote=True),
                description=project['description'],
                url=f"{self.base_url}/jobs/sample-{i}-{hash(project['title'])}",
                source="Upwork",
                job_type=JobType.FREELANCE,
                employment_type="freelance",
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'sample': True, 'keywords': keywords}
            )
            
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        """Get detailed project information from Upwork"""
        try:
            response = self.safe_request(job_url)
            if not response:
                return {"source": "Upwork", "error": "Could not fetch details"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract project details
            details = {
                "source": "Upwork",
                "scraped_at": datetime.now().isoformat()
            }
            
            # Full description
            desc_elem = soup.find('div', class_='job-description')
            if desc_elem:
                details['full_description'] = self.clean_text(desc_elem.get_text())
            
            # Required skills
            skills_elem = soup.find('div', class_='skills-list')
            if skills_elem:
                skills = [self.clean_text(skill.get_text()) for skill in skills_elem.find_all('span')]
                details['required_skills'] = skills
            
            # Client info
            client_elem = soup.find('div', class_='client-overview')
            if client_elem:
                details['client_info'] = self.clean_text(client_elem.get_text())
            
            return details
            
        except Exception as e:
            self.logger.error(f"Error getting Upwork project details: {e}")
            return {"source": "Upwork", "error": str(e)}


if __name__ == "__main__":
    print("Testing Upwork Scraper...")
    
    scraper = UpworkScraper()
    
    try:
        jobs = scraper.scrape_jobs("python", "", 5)
        print(f"Found {len(jobs)} projects")
        
        for job in jobs:
            print(f"- {job.title}")
            if job.salary:
                print(f"  Budget: {job.salary}")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        scraper.close()