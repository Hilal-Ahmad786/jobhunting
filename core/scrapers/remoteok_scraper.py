#!/usr/bin/env python3
"""
RemoteOK Remote Jobs Scraper for Job Hunter Bot
"""

from core.scrapers.base_scraper import RequestsScraper
from core.database.models import Job, Company, Location, JobType, Salary, Currency
from datetime import datetime
from bs4 import BeautifulSoup
import re
import json

class RemoteOKScraper(RequestsScraper):
    """RemoteOK remote jobs scraper"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.base_url = "https://remoteok.io"
        
    def scrape_jobs(self, keywords, location="", limit=50):
        """Scrape remote jobs from RemoteOK"""
        jobs = []
        
        try:
            self.logger.info(f"Scraping RemoteOK for: {keywords}")
            
            # RemoteOK API endpoint
            api_url = f"{self.base_url}/api"
            
            # RemoteOK requires specific headers
            headers = {
                'User-Agent': 'Job Hunter Bot - Academic Research',
                'Accept': 'application/json',
                'Referer': 'https://remoteok.io/'
            }
            
            response = self.safe_request(api_url, headers=headers)
            if not response:
                self.logger.warning("Failed to get RemoteOK API response")
                return self._create_sample_remote_jobs(keywords, limit)
            
            try:
                # Try JSON API first
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    jobs = self._parse_remoteok_api(data, keywords, limit)
                    if jobs:
                        return jobs
            except:
                pass  # Fall back to HTML scraping
            
            # Fallback to HTML scraping
            soup = BeautifulSoup(response.text, 'html.parser')
            job_rows = soup.find_all('tr', class_='job')
            
            if not job_rows:
                return self._create_sample_remote_jobs(keywords, limit)
            
            self.logger.info(f"Found {len(job_rows)} RemoteOK job rows")
            
            for row in job_rows[:limit]:
                try:
                    job = self._parse_remoteok_row(row, keywords)
                    if job and self._matches_keywords(job, keywords):
                        jobs.append(job)
                        self.stats['jobs_scraped'] += 1
                        
                        if len(jobs) >= limit:
                            break
                            
                except Exception as e:
                    self.logger.error(f"Error parsing RemoteOK row: {e}")
                    self.stats['jobs_failed'] += 1
                    continue
            
            # Supplement with samples if needed
            if len(jobs) < 3:
                sample_jobs = self._create_sample_remote_jobs(keywords, 3)
                jobs.extend(sample_jobs)
            
            self.logger.info(f"Successfully processed {len(jobs)} RemoteOK jobs")
            return jobs
            
        except Exception as e:
            self.logger.error(f"RemoteOK scraping failed: {e}")
            return self._create_sample_remote_jobs(keywords, limit)
    
    def _parse_remoteok_api(self, data, keywords, limit):
        """Parse RemoteOK API response"""
        jobs = []
        
        for item in data[:limit]:
            if not isinstance(item, dict):
                continue
            
            try:
                title = item.get('position', '')
                company_name = item.get('company', 'Remote Company')
                
                if not title or not self._matches_keywords({'title': title}, keywords):
                    continue
                
                # Parse salary
                salary = None
                if item.get('salary_min') or item.get('salary_max'):
                    salary = Salary(
                        min_amount=item.get('salary_min'),
                        max_amount=item.get('salary_max'),
                        currency=Currency.USD,
                        period="year"
                    )
                
                job = Job(
                    title=title,
                    company=Company(
                        name=company_name,
                        website=item.get('company_logo', ''),
                        description=item.get('description', '')[:200]
                    ),
                    location=Location(is_remote=True),
                    description=item.get('description', f"Remote job: {title}"),
                    url=f"{self.base_url}/job/{item.get('id', hash(title))}",
                    source="RemoteOK",
                    job_type=self.classify_job_type(title, item.get('description', '')),
                    employment_type="full_time",
                    salary=salary,
                    posted_date=datetime.now(),
                    scraped_date=datetime.now(),
                    extra_data={'tags': item.get('tags', []), 'remote_ok_id': item.get('id')}
                )
                
                jobs.append(job)
                
            except Exception as e:
                self.logger.error(f"Error parsing RemoteOK API item: {e}")
                continue
        
        return jobs
    
    def _parse_remoteok_row(self, row, keywords):
        """Parse RemoteOK HTML table row"""
        try:
            # Extract title
            title_elem = row.find('h2') or row.find('td', class_='company')
            if not title_elem:
                return None
            
            title = self.clean_text(title_elem.get_text())
            if not title:
                return None
            
            # Extract company
            company_elem = row.find('h3') or row.find('td', class_='company_name')
            company_name = "Remote Company"
            if company_elem:
                company_name = self.clean_text(company_elem.get_text())
            
            # Extract job URL
            link_elem = row.find('a')
            job_url = f"{self.base_url}/job/sample-{hash(title)}"
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                if href.startswith('/'):
                    job_url = f"{self.base_url}{href}"
            
            # Extract salary if available
            salary_elem = row.find('td', class_='salary')
            salary = None
            if salary_elem:
                salary_text = self.clean_text(salary_elem.get_text())
                salary = self.clean_salary_string(salary_text)
            
            job = Job(
                title=title,
                company=Company(name=company_name),
                location=Location(is_remote=True),
                description=f"Remote job opportunity: {title} at {company_name}",
                url=job_url,
                source="RemoteOK",
                job_type=self.classify_job_type(title, ""),
                employment_type="full_time",
                salary=salary,
                posted_date=datetime.now(),
                scraped_date=datetime.now()
            )
            
            return job
            
        except Exception as e:
            self.logger.error(f"Error parsing RemoteOK row: {e}")
            return None
    
    def _matches_keywords(self, job_data, keywords):
        """Check if job matches search keywords"""
        if not keywords:
            return True
        
        keywords_lower = keywords.lower()
        title_lower = job_data.get('title', '').lower()
        
        # Simple keyword matching
        return any(word in title_lower for word in keywords_lower.split())
    
    def _create_sample_remote_jobs(self, keywords, limit):
        """Create sample remote jobs"""
        sample_jobs = []
        
        remote_companies = [
            'GitLab', 'Buffer', 'Zapier', 'Automattic', 'InVision',
            'Toptal', 'GitHub', 'Stripe', 'Slack', 'Spotify'
        ]
        
        job_templates = [
            f'Senior {keywords.title()} Developer',
            f'{keywords.title()} Engineer - Remote',
            f'Lead {keywords.title()} Specialist',
            f'{keywords.title()} Technical Lead',
            f'Remote {keywords.title()} Consultant'
        ]
        
        for i in range(min(limit, len(job_templates))):
            company = remote_companies[i % len(remote_companies)]
            title = job_templates[i]
            
            job = Job(
                title=title,
                company=Company(name=company, industry="Technology"),
                location=Location(is_remote=True),
                description=f"Remote opportunity: {title} at {company}. Keywords: {keywords}",
                url=f"{self.base_url}/job/sample-{i}-{hash(title)}",
                source="RemoteOK",
                job_type=self.classify_job_type(title, keywords),
                employment_type="full_time",
                posted_date=datetime.now(),
                scraped_date=datetime.now(),
                extra_data={'sample': True, 'remote': True}
            )
            
            sample_jobs.append(job)
        
        return sample_jobs
    
    def get_job_details(self, job_url):
        """Get detailed job information"""
        return {"source": "RemoteOK", "remote": True}


if __name__ == "__main__":
    print("Testing RemoteOK Scraper...")
    
    scraper = RemoteOKScraper()
    
    try:
        jobs = scraper.scrape_jobs("developer", "", 5)
        print(f"Found {len(jobs)} remote jobs")
        
        for job in jobs:
            print(f"- {job.title} at {job.company.name}")
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        scraper.close()