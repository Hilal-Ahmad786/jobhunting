#!/usr/bin/env python3
"""
Core Data Models for Job Hunter Bot

This module defines all the data structures used throughout the application.
These models represent jobs, applications, user profiles, and other core entities.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json


class JobType(Enum):
    """Job type enumeration"""
    CIVIL_ENGINEERING = "civil"
    IT_PROGRAMMING = "it"
    FREELANCE = "freelance"
    DIGITAL_MARKETING = "marketing"
    OTHER = "other"


class ApplicationStatus(Enum):
    """Application status enumeration"""
    DRAFT = "draft"
    APPLIED = "applied"
    REVIEWED = "reviewed"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    OFFER_RECEIVED = "offer_received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Currency(Enum):
    """Supported currencies"""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"
    NOK = "NOK"
    SEK = "SEK"
    DKK = "DKK"


@dataclass
class Salary:
    """Salary information with currency and range"""
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    currency: Currency = Currency.USD
    period: str = "year"  # year, month, hour, project
    is_negotiable: bool = False
    
    def __str__(self) -> str:
        if self.min_amount and self.max_amount:
            return f"{self.min_amount:,.0f}-{self.max_amount:,.0f} {self.currency.value}/{self.period}"
        elif self.min_amount:
            return f"{self.min_amount:,.0f}+ {self.currency.value}/{self.period}"
        elif self.max_amount:
            return f"Up to {self.max_amount:,.0f} {self.currency.value}/{self.period}"
        else:
            return "Not specified"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'min_amount': self.min_amount,
            'max_amount': self.max_amount,
            'currency': self.currency.value,
            'period': self.period,
            'is_negotiable': self.is_negotiable
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Salary':
        return cls(
            min_amount=data.get('min_amount'),
            max_amount=data.get('max_amount'),
            currency=Currency(data.get('currency', 'USD')),
            period=data.get('period', 'year'),
            is_negotiable=data.get('is_negotiable', False)
        )


@dataclass
class Company:
    """Company information"""
    name: str
    industry: Optional[str] = None
    size: Optional[str] = None  # "1-10", "11-50", "51-200", "201-500", "500+"
    website: Optional[str] = None
    headquarters: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'industry': self.industry,
            'size': self.size,
            'website': self.website,
            'headquarters': self.headquarters,
            'description': self.description,
            'logo_url': self.logo_url
        }


@dataclass 
class Location:
    """Location information with flexibility for remote/hybrid"""
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    is_remote: bool = False
    is_hybrid: bool = False
    timezone: Optional[str] = None
    visa_sponsorship: bool = False
    
    def __str__(self) -> str:
        if self.is_remote:
            return "Remote"
        elif self.is_hybrid:
            return f"Hybrid - {self.city}, {self.country}" if self.city and self.country else "Hybrid"
        elif self.city and self.country:
            if self.state:
                return f"{self.city}, {self.state}, {self.country}"
            return f"{self.city}, {self.country}"
        elif self.country:
            return self.country
        else:
            return "Location not specified"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'city': self.city,
            'state': self.state, 
            'country': self.country,
            'is_remote': self.is_remote,
            'is_hybrid': self.is_hybrid,
            'timezone': self.timezone,
            'visa_sponsorship': self.visa_sponsorship
        }


@dataclass
class JobRequirements:
    """Job requirements and qualifications"""
    experience_years: Optional[int] = None
    education_level: Optional[str] = None  # "bachelor", "master", "phd", "none"
    skills_required: List[str] = field(default_factory=list)
    skills_preferred: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'experience_years': self.experience_years,
            'education_level': self.education_level,
            'skills_required': self.skills_required,
            'skills_preferred': self.skills_preferred,
            'certifications': self.certifications,
            'languages': self.languages
        }


@dataclass
class Job:
    """Main job/project data model"""
    # Basic information
    title: str
    company: Company
    location: Location
    description: str
    url: str
    source: str  # "LinkedIn", "Indeed", "Upwork", etc.
    
    # Classification
    job_type: JobType
    employment_type: str = "full_time"  # full_time, part_time, contract, freelance
    
    # Financial
    salary: Optional[Salary] = None
    
    # Requirements
    requirements: JobRequirements = field(default_factory=JobRequirements)
    
    # Dates and metadata
    posted_date: Optional[datetime] = None
    application_deadline: Optional[datetime] = None
    scraped_date: datetime = field(default_factory=datetime.now)
    
    # Internal tracking
    id: Optional[int] = None
    is_bookmarked: bool = False
    match_score: Optional[float] = None  # AI-calculated match score 0-100
    notes: str = ""
    
    # Additional metadata
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing"""
        # Ensure company is Company object
        if isinstance(self.company, str):
            self.company = Company(name=self.company)
        
        # Ensure location is Location object  
        if isinstance(self.location, str):
            if self.location.lower() in ['remote', 'worldwide']:
                self.location = Location(is_remote=True)
            else:
                parts = self.location.split(', ')
                if len(parts) >= 2:
                    self.location = Location(city=parts[0], country=parts[-1])
                else:
                    self.location = Location(city=self.location)
        
        # Set default salary if string provided
        if isinstance(self.salary, str):
            self.salary = self._parse_salary_string(self.salary)
    
    def _parse_salary_string(self, salary_str: str) -> Optional[Salary]:
        """Parse salary string into Salary object"""
        if not salary_str or salary_str.lower() in ['not specified', 'competitive', '']:
            return None
        
        # This would contain salary parsing logic
        # For now, return a basic salary object
        return Salary()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company.to_dict(),
            'location': self.location.to_dict(),
            'description': self.description,
            'url': self.url,
            'source': self.source,
            'job_type': self.job_type.value,
            'employment_type': self.employment_type,
            'salary': self.salary.to_dict() if self.salary else None,
            'requirements': self.requirements.to_dict(),
            'posted_date': self.posted_date.isoformat() if self.posted_date else None,
            'application_deadline': self.application_deadline.isoformat() if self.application_deadline else None,
            'scraped_date': self.scraped_date.isoformat(),
            'is_bookmarked': self.is_bookmarked,
            'match_score': self.match_score,
            'notes': self.notes,
            'extra_data': self.extra_data
        }
    
    def get_summary(self) -> str:
        """Get a brief summary of the job"""
        location_str = str(self.location)
        salary_str = str(self.salary) if self.salary else "Salary not specified"
        return f"{self.title} at {self.company.name} | {location_str} | {salary_str}"


@dataclass
class Application:
    """Job application tracking"""
    job_id: int
    job: Optional[Job] = None  # Will be populated when needed
    
    # Application materials
    cv_version: str = "default"
    cover_letter: str = ""
    portfolio_links: List[str] = field(default_factory=list)
    
    # Status tracking
    status: ApplicationStatus = ApplicationStatus.DRAFT
    applied_date: Optional[datetime] = None
    response_date: Optional[datetime] = None
    
    # Communication history
    communications: List[Dict[str, Any]] = field(default_factory=list)
    
    # Interview information
    interview_dates: List[datetime] = field(default_factory=list)
    interview_notes: str = ""
    
    # Outcome
    offer_details: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[str] = None
    
    # Internal tracking
    id: Optional[int] = None
    created_date: datetime = field(default_factory=datetime.now)
    updated_date: datetime = field(default_factory=datetime.now)
    
    def add_communication(self, comm_type: str, content: str, date: datetime = None):
        """Add a communication record"""
        if date is None:
            date = datetime.now()
        
        self.communications.append({
            'type': comm_type,  # 'email', 'phone', 'interview', 'follow_up'
            'content': content,
            'date': date.isoformat(),
        })
        self.updated_date = datetime.now()
    
    def update_status(self, new_status: ApplicationStatus, notes: str = ""):
        """Update application status"""
        self.status = new_status
        self.updated_date = datetime.now()
        
        if notes:
            self.add_communication('status_update', f"Status changed to {new_status.value}: {notes}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'cv_version': self.cv_version,
            'cover_letter': self.cover_letter,
            'portfolio_links': json.dumps(self.portfolio_links),
            'status': self.status.value,
            'applied_date': self.applied_date.isoformat() if self.applied_date else None,
            'response_date': self.response_date.isoformat() if self.response_date else None,
            'communications': json.dumps(self.communications),
            'interview_dates': json.dumps([d.isoformat() for d in self.interview_dates]),
            'interview_notes': self.interview_notes,
            'offer_details': json.dumps(self.offer_details) if self.offer_details else None,
            'rejection_reason': self.rejection_reason,
            'created_date': self.created_date.isoformat(),
            'updated_date': self.updated_date.isoformat()
        }


@dataclass
class UserProfile:
    """User profile and preferences"""
    # Personal information
    name: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    
    # Professional information
    current_title: Optional[str] = None
    experience_years: int = 0
    skills: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    education: List[Dict[str, str]] = field(default_factory=list)
    
    # CV versions
    cv_templates: Dict[str, str] = field(default_factory=dict)  # name -> content
    
    # Job preferences
    preferred_job_types: List[JobType] = field(default_factory=list)
    preferred_locations: List[str] = field(default_factory=list)
    salary_expectations: Dict[str, Salary] = field(default_factory=dict)  # job_type -> salary
    remote_preference: str = "hybrid"  # remote, on_site, hybrid, no_preference
    
    # Search preferences
    keywords_civil: List[str] = field(default_factory=list)
    keywords_it: List[str] = field(default_factory=list)
    keywords_freelance: List[str] = field(default_factory=list)
    
    # Automation settings
    auto_apply_enabled: bool = False
    auto_apply_filters: Dict[str, Any] = field(default_factory=dict)
    
    # Notification preferences
    email_notifications: bool = True
    desktop_notifications: bool = True
    notification_keywords: List[str] = field(default_factory=list)
    
    # API keys and integrations
    openai_api_key: Optional[str] = None
    other_api_keys: Dict[str, str] = field(default_factory=dict)
    
    def add_cv_template(self, name: str, content: str):
        """Add a CV template"""
        self.cv_templates[name] = content
    
    def get_cv_template(self, name: str = "default") -> str:
        """Get CV template by name"""
        return self.cv_templates.get(name, "")
    
    def add_skill(self, skill: str):
        """Add a skill"""
        if skill not in self.skills:
            self.skills.append(skill)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'linkedin_url': self.linkedin_url,
            'portfolio_url': self.portfolio_url,
            'current_title': self.current_title,
            'experience_years': self.experience_years,
            'skills': json.dumps(self.skills),
            'certifications': json.dumps(self.certifications),
            'education': json.dumps(self.education),
            'cv_templates': json.dumps(self.cv_templates),
            'preferred_job_types': json.dumps([jt.value for jt in self.preferred_job_types]),
            'preferred_locations': json.dumps(self.preferred_locations),
            'salary_expectations': json.dumps({k: v.to_dict() for k, v in self.salary_expectations.items()}),
            'remote_preference': self.remote_preference,
            'keywords_civil': json.dumps(self.keywords_civil),
            'keywords_it': json.dumps(self.keywords_it),
            'keywords_freelance': json.dumps(self.keywords_freelance),
            'auto_apply_enabled': self.auto_apply_enabled,
            'auto_apply_filters': json.dumps(self.auto_apply_filters),
            'email_notifications': self.email_notifications,
            'desktop_notifications': self.desktop_notifications,
            'notification_keywords': json.dumps(self.notification_keywords),
            'openai_api_key': self.openai_api_key,
            'other_api_keys': json.dumps(self.other_api_keys)
        }


@dataclass
class SearchQuery:
    """Search query configuration"""
    keywords: str
    job_types: List[JobType] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    remote_only: bool = False
    salary_min: Optional[float] = None
    salary_currency: Currency = Currency.USD
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    sources: List[str] = field(default_factory=list)  # Specific sources to search
    date_posted: Optional[str] = None  # "today", "week", "month"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'keywords': self.keywords,
            'job_types': [jt.value for jt in self.job_types],
            'locations': self.locations,
            'remote_only': self.remote_only,
            'salary_min': self.salary_min,
            'salary_currency': self.salary_currency.value,
            'experience_min': self.experience_min,
            'experience_max': self.experience_max,
            'sources': self.sources,
            'date_posted': self.date_posted
        }


@dataclass
class Analytics:
    """Analytics and statistics"""
    total_jobs_found: int = 0
    jobs_by_type: Dict[str, int] = field(default_factory=dict)
    jobs_by_source: Dict[str, int] = field(default_factory=dict)
    applications_sent: int = 0
    responses_received: int = 0
    interviews_scheduled: int = 0
    offers_received: int = 0
    
    # Calculated metrics
    response_rate: float = 0.0
    interview_rate: float = 0.0
    offer_rate: float = 0.0
    
    # Time-based metrics
    avg_application_time: Optional[float] = None  # minutes
    avg_response_time: Optional[float] = None  # days
    
    def calculate_rates(self):
        """Calculate success rates"""
        if self.applications_sent > 0:
            self.response_rate = (self.responses_received / self.applications_sent) * 100
            self.interview_rate = (self.interviews_scheduled / self.applications_sent) * 100
            self.offer_rate = (self.offers_received / self.applications_sent) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_jobs_found': self.total_jobs_found,
            'jobs_by_type': self.jobs_by_type,
            'jobs_by_source': self.jobs_by_source,
            'applications_sent': self.applications_sent,
            'responses_received': self.responses_received,
            'interviews_scheduled': self.interviews_scheduled,
            'offers_received': self.offers_received,
            'response_rate': self.response_rate,
            'interview_rate': self.interview_rate,
            'offer_rate': self.offer_rate,
            'avg_application_time': self.avg_application_time,
            'avg_response_time': self.avg_response_time
        }


# Utility functions for model operations
def create_sample_job() -> Job:
    """Create a sample job for testing"""
    company = Company(
        name="Tech Solutions Inc.",
        industry="Technology",
        size="51-200",
        website="https://techsolutions.com"
    )
    
    location = Location(
        city="San Francisco",
        state="CA", 
        country="USA",
        is_remote=False,
        visa_sponsorship=True
    )
    
    salary = Salary(
        min_amount=80000,
        max_amount=120000,
        currency=Currency.USD,
        period="year"
    )
    
    requirements = JobRequirements(
        experience_years=3,
        education_level="bachelor",
        skills_required=["Python", "Django", "PostgreSQL"],
        skills_preferred=["React", "AWS", "Docker"]
    )
    
    return Job(
        title="Senior Python Developer",
        company=company,
        location=location,
        description="We are looking for an experienced Python developer...",
        url="https://example.com/job/123",
        source="LinkedIn",
        job_type=JobType.IT_PROGRAMMING,
        employment_type="full_time",
        salary=salary,
        requirements=requirements,
        posted_date=datetime.now()
    )


def create_sample_user_profile() -> UserProfile:
    """Create a sample user profile for testing"""
    return UserProfile(
        name="John Doe",
        email="john.doe@email.com",
        current_title="Software Developer",
        experience_years=5,
        skills=["Python", "JavaScript", "React", "Node.js", "PostgreSQL"],
        preferred_job_types=[JobType.IT_PROGRAMMING],
        preferred_locations=["Remote", "San Francisco", "New York"],
        remote_preference="hybrid",
        keywords_it=["python developer", "full stack developer", "software engineer"],
        keywords_civil=["structural engineer", "civil engineer"],
        keywords_freelance=["web development", "python automation"]
    )


if __name__ == "__main__":
    # Example usage and testing
    print("Testing Job Hunter Bot Data Models")
    print("=" * 40)
    
    # Create sample job
    job = create_sample_job()
    print(f"Sample Job: {job.get_summary()}")
    print(f"Job Type: {job.job_type.value}")
    print(f"Location: {job.location}")
    print(f"Salary: {job.salary}")
    
    # Create sample user profile
    user = create_sample_user_profile()
    print(f"\nUser: {user.name}")
    print(f"Skills: {', '.join(user.skills)}")
    print(f"Preferred Job Types: {[jt.value for jt in user.preferred_job_types]}")
    
    # Create sample application
    app = Application(
        job_id=1,
        job=job,
        cv_version="IT Optimized",
        cover_letter="Dear Hiring Manager..."
    )
    app.update_status(ApplicationStatus.APPLIED, "Applied through company website")
    print(f"\nApplication Status: {app.status.value}")
    print(f"Communications: {len(app.communications)}")