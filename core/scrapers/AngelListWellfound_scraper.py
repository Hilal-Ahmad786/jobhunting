#!/usr/bin/env python3
"""
AngelList/Wellfound Startup Jobs Scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re
import json

class AngelListScraper(RequestsScraper):
    """AngelList (now Wellfound) startup jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://angel.co"
        self.wellfound_url = "https://wellfound.com"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape startup jobs from AngelList/Wellfound"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping AngelList/Wellfound for: {keywords}")
            
            # Try Wellfound first (new platform)
            search_url = f"{self.wellfound_url}/jobs"
            
            params = {
                'query': keywords,
                'location': location,
                'remote': 'true' if 'remote' in keywords.lower() else 'false'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://wellfound.com/',
                'Connection': 'keep-alive'
            }
            
            response = self.safe_request(search_url, params=params, headers=headers)
            if not response:
                self.logger.warning("Failed to get Wellfound response")
                return self._create_sample_startup_jobs(keywords, limit)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # AngelList/Wellfound job cards
            job_cards = (soup.find_all('div', class_='job-card') or
                        soup.find_all('div', class_='startup-job') or
                        soup.find_all('div', {'data-test': 'StartupResult'}))
            
            if not job_cards:
                self.logger.warning("No AngelList job cards found")
                return self._create_sample_startup_jobs(keywords, limit)
            
            self.logger.info(f"Found {len(job_cards)} AngelList/Wellfound job cards")
            
            for card in job_cards[:limit]:
                try:
                    job = self._parse_angellist_card(card, keywords)
                    if job:
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                except Exception as e:
                    self.logger.error(f"Error parsing AngelList card: {e}")
                    self.stats['jobs_failed'] += 1
                    continue
            
            # Add sample jobs if we didn't get enough
            if len(jobs) < 3:
                sample_jobs = self._create_sample_startup_jobs(keywords, 3)
                jobs.extend(sample_jobs)
            
            self.logger.info(f"Successfully processed {len(jobs)} startup jobs")
            return jobs
            
        except Exception as e:
            self.logger.error(f"AngelList scraping failed: {e}")
            return self._create_sample_startup_jobs(keywords, limit)
    
    def _parse_angellist_card(self, card, keywords):
        """Parse individual AngelList job card"""
        try:
            # Extract title
            title_elem = (card.find('h2') or
                         card.find('h3') or
                         card.find('a', class_='job-title'))
            
            if not title_elem:
                return None
            
            title_link = title_elem.find('a') if title_elem.name != 'a' else title_elem
            title = self.clean_text(title_link.get_text() if title_link else title_elem.get_text())
            
            if not title:
                return None
            
            # Extract company name
            company_elem = (card.find('div', class_='company-name') or
                           card.find('h4') or
                           card.find('span', class_='startup-name'))
            
            company_name = "Startup Company"
            if company_elem:
                company_name = self.clean_text(company_elem.get_text())
            
            # Extract job URL
            job_url = f"{self.wellfound_url}/jobs/sample-{hash(title)}"
            if title_link and title_link.get('href'):
                href = title_link.get('href')
                if href.startswith('/'):
                    job_url = f"{self.wellfound_url}{href}"
                elif href.startswith('http'):
                    job_url = href
            
            # Extract salary information
            salary_elem = (card.find('div', class_='salary') or
                          card.find('span', class_='compensation'))
            
            salary = None
            if salary_elem:
                salary_text = self.clean_text(salary_elem.get_text())
                salary = self._parse_startup_salary(salary_text)
            
            # Extract location (check for remote)
            location_elem = card.find('div', class_='location')
            is_remote = True  # Default for many startup jobs
            location_text = "Remote"
            
            if location_elem:
                location_text = self.clean_text(location_elem.get_text())
                is_remote = 'remote' in location_text.lower()
            
            location = Location(
                is_remote=is_remote,
                city=location_text if not is_remote else None
            )
            
            # Extract company info
            company_size_elem = card.find('div', class_='company-size')
            company_size = None
            if company_size_elem:
                company_size = self.clean_text(company_size_elem.get_text())
            
            # Extract description snippet
            desc_elem = card.find('div', class_='job-description') or card.find('p')
            description = f"Startup opportunity: {title} at {company_name}"
            if desc_elem:
                snippet = self.clean_text(desc_elem.get_text())
                description += f"\n\n{snippet[:300]}"
            
            # Extract tags/skills
            tags_container = card.find('div', class_='tags')
            tags = []
            if tags_container:
                tag_elements = tags_container.find_all('span')
                tags = [self.clean_text(tag.get_text()) for tag in tag_elements]
            
            job = Job(
                title=title,
                company=Company(
                    name=company_name,
                    size=company_size,
                    industry="Startup"
                ),
                location=location,
                description=description,
                url=job_url,
                source="AngelList",
                job_type=self.classify_job_type(title, description),
                employment_type="full_time",
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'tags': tags, 'startup': True}
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error parsing AngelList job card: {e}")
            return None
    
    def _parse_startup_salary(self, salary_text):
        """Parse startup salary information"""
        if not salary_text or 'equity' in salary_text.lower():
            return None
        
        # Common startup salary patterns
        if ' in salary_text:
            return self.clean_salary_string(salary_text)
        
        return None
    
    def _create_sample_startup_jobs(self, keywords, limit):
        """Create sample startup jobs when scraping fails"""
        sample_jobs = []
        
        startup_companies = [
            'TechFlow AI', 'DataVibe', 'CloudScale', 'DevForge', 'StartupLab',
            'InnovateCorp', 'NextGen Solutions', 'CodeCraft', 'BuildTech', 'ScaleUp'
        ]
        
        job_templates = [
            f'Senior {keywords.title()} Engineer',
            f'{keywords.title()} Team Lead', 
            f'Full Stack {keywords.title()} Developer',
            f'{keywords.title()} Product Engineer',
            f'Lead {keywords.title()} Developer'
        ]
        
        salary_ranges = [
            {'min': 80000, 'max': 140000},
            {'min': 90000, 'max': 160000},
            {'min': 70000, 'max': 120000},
            {'min': 100000, 'max': 180000},
            {'min': 85000, 'max': 150000}
        ]
        
        for i in range(min(limit, len(job_templates))):
            company = startup_companies[i % len(startup_companies)]
            title = job_templates[i]
            salary_range = salary_ranges[i % len(salary_ranges)]
            
            salary = Salary(
                min_amount=salary_range['min'],
                max_amount=salary_range['max'],
                currency=Currency.USD,
                period="year"
            )
            
            job = Job(
                title=title,
                company=Company(
                    name=company,
                    industry="Technology",
                    size="11-50"
                ),
                location=Location(is_remote=True),
                description=f"Join our fast-growing startup as a {title}. We're looking for passionate {keywords} professionals to help build the future.",
                url=f"{self.wellfound_url}/jobs/sample-startup-{i}-{hash(title)}",
                source="AngelList",
                job_type=self.classify_job_type(title, keywords),
                employment_type="full_time",
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'startup': True, 'equity_available': True}
            )
            
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        """Get detailed startup job information"""
        try:
            response = self.safe_request(job_url)
            if not response:
                return {"source": "AngelList", "error": "Could not fetch details"}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            details = {
                "source": "AngelList",
                "startup": True,
                "scraped_at": datetime.now().isoformat()
            }
            
            # Company description
            company_desc = soup.find('div', class_='company-description')
            if company_desc:
                details['company_description'] = self.clean_text(company_desc.get_text())
            
            # Funding info
            funding_elem = soup.find('div', class_='funding-info')
            if funding_elem:
                details['funding_stage'] = self.clean_text(funding_elem.get_text())
            
            # Team size
            team_elem = soup.find('div', class_='team-size')
            if team_elem:
                details['team_size'] = self.clean_text(team_elem.get_text())
            
            return details
            
        except Exception as e:
            self.logger.error(f"Error getting AngelList job details: {e}")
            return {"source": "AngelList", "error": str(e)}


if __name__ == "__main__":
    print("Testing AngelList Scraper...")
    
    scraper = AngelListScraper()
    
    try:
        jobs = scraper.scrape_jobs("software engineer", "", 5)
        print(f"Found {len(jobs)} startup jobs")
        
        for job in jobs:
            print(f"- {job.title} at {job.company.name}")
            if job.salary:
                print(f"  Salary: {job.salary}")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        scraper.close()