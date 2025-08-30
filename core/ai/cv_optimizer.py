#!/usr/bin/env python3
"""
CV Optimizer for Job Hunter Bot

This module handles AI-powered CV optimization using OpenAI's GPT models.
Features include:
- Job-specific CV tailoring
- ATS (Applicant Tracking System) optimization
- Multi-format CV generation (US, EU, UK styles)
- Cover letter generation
- Freelance proposal creation
- Skills gap analysis
- Match score calculation
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import openai

from core.database.models import Job, JobType, UserProfile, JobRequirements


class CVOptimizationError(Exception):
    """Custom exception for CV optimization operations"""
    pass


@dataclass
class OptimizationResult:
    """Result of CV optimization process"""
    optimized_cv: str
    cover_letter: str
    match_score: float
    improvements_made: List[str]
    ats_score: float
    keywords_added: List[str]
    sections_reordered: List[str]
    optimization_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'optimized_cv': self.optimized_cv,
            'cover_letter': self.cover_letter,
            'match_score': self.match_score,
            'improvements_made': self.improvements_made,
            'ats_score': self.ats_score,
            'keywords_added': self.keywords_added,
            'sections_reordered': self.sections_reordered,
            'optimization_time': self.optimization_time
        }


@dataclass 
class SkillsGapAnalysis:
    """Analysis of skills gap between user and job requirements"""
    matching_skills: List[str]
    missing_skills: List[str]
    transferable_skills: List[str]
    skill_match_percentage: float
    recommendations: List[str]


class CVOptimizer:
    """
    AI-powered CV optimizer using OpenAI GPT models
    Tailors CVs for specific jobs and job types
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenAI
        openai.api_key = api_key
        
        # CV format templates
        self.cv_formats = {
            'us': self._get_us_cv_template(),
            'eu': self._get_eu_cv_template(),
            'uk': self._get_uk_cv_template(),
            'freelance': self._get_freelance_template()
        }
        
        # Job type specific prompts
        self.job_type_prompts = {
            JobType.CIVIL_ENGINEERING: self._get_civil_engineering_prompt(),
            JobType.IT_PROGRAMMING: self._get_it_programming_prompt(),
            JobType.DIGITAL_MARKETING: self._get_digital_marketing_prompt(),
            JobType.FREELANCE: self._get_freelance_prompt()
        }
        
        # ATS optimization rules
        self.ats_rules = self._load_ats_rules()
        
        self.logger.info("CV Optimizer initialized successfully")
    
    def optimize_cv_for_job(self, 
                           user_profile: UserProfile, 
                           job: Job,
                           cv_format: str = 'us',
                           include_cover_letter: bool = True) -> OptimizationResult:
        """
        Main method to optimize CV for a specific job
        
        Args:
            user_profile: User's profile and master CV
            job: Target job to optimize for
            cv_format: 'us', 'eu', 'uk', or 'freelance'
            include_cover_letter: Whether to generate cover letter
            
        Returns:
            OptimizationResult with optimized CV and metadata
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Optimizing CV for: {job.title} at {job.company.name}")
            
            # Step 1: Analyze job requirements
            job_analysis = self._analyze_job_requirements(job)
            
            # Step 2: Perform skills gap analysis
            skills_gap = self._analyze_skills_gap(user_profile, job)
            
            # Step 3: Calculate initial match score
            initial_match_score = self._calculate_match_score(user_profile, job)
            
            # Step 4: Generate optimized CV
            optimized_cv = self._generate_optimized_cv(
                user_profile, job, job_analysis, skills_gap, cv_format
            )
            
            # Step 5: Optimize for ATS
            ats_optimized_cv, ats_score = self._optimize_for_ats(optimized_cv, job)
            
            # Step 6: Generate cover letter if requested
            cover_letter = ""
            if include_cover_letter:
                cover_letter = self._generate_cover_letter(user_profile, job, ats_optimized_cv)
            
            # Step 7: Calculate final match score
            final_match_score = initial_match_score + 15  # Optimized CV boost
            
            # Step 8: Compile results
            optimization_time = (datetime.now() - start_time).total_seconds()
            
            result = OptimizationResult(
                optimized_cv=ats_optimized_cv,
                cover_letter=cover_letter,
                match_score=min(100.0, final_match_score),
                improvements_made=job_analysis.get('improvements', []),
                ats_score=ats_score,
                keywords_added=job_analysis.get('keywords_added', []),
                sections_reordered=job_analysis.get('sections_reordered', []),
                optimization_time=optimization_time
            )
            
            self.logger.info(f"CV optimization completed in {optimization_time:.1f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"CV optimization failed: {e}")
            raise CVOptimizationError(f"Optimization failed: {e}")
    
    def _analyze_job_requirements(self, job: Job) -> Dict[str, Any]:
        """Analyze job requirements using AI"""
        prompt = f"""
        Analyze this job posting and extract key information for CV optimization:

        Job Title: {job.title}
        Company: {job.company.name}
        Job Type: {job.job_type.value}
        Location: {job.location}
        
        Job Description:
        {job.description}
        
        Please analyze and return JSON with:
        1. "required_skills": List of must-have technical skills
        2. "preferred_skills": List of nice-to-have skills
        3. "key_responsibilities": Main job responsibilities
        4. "experience_level": Required experience level
        5. "education_requirements": Education requirements
        6. "keywords": Important keywords for ATS optimization
        7. "company_culture": Apparent company culture/values
        8. "priorities": What seems most important to the employer
        
        Return only valid JSON, no additional text.
        """
        
        try:
            response = self._call_openai_api(prompt, temperature=0.1)
            analysis = json.loads(response)
            return analysis
            
        except Exception as e:
            self.logger.error(f"Job analysis failed: {e}")
            return self._fallback_job_analysis(job)
    
    def _analyze_skills_gap(self, user_profile: UserProfile, job: Job) -> SkillsGapAnalysis:
        """Analyze skills gap between user and job requirements"""
        user_skills = [skill.lower() for skill in user_profile.skills]
        
        # Extract skills from job (this would use the job analysis)
        job_skills = []
        if job.requirements and job.requirements.skills_required:
            job_skills = [skill.lower() for skill in job.requirements.skills_required]
        
        # Find matching skills
        matching_skills = [skill for skill in user_skills if skill in job_skills]
        
        # Find missing skills
        missing_skills = [skill for skill in job_skills if skill not in user_skills]
        
        # Calculate match percentage
        total_required = len(job_skills)
        if total_required > 0:
            match_percentage = (len(matching_skills) / total_required) * 100
        else:
            match_percentage = 80.0  # Default if no specific requirements
        
        # Generate recommendations
        recommendations = []
        if missing_skills:
            recommendations.append(f"Consider highlighting experience with: {', '.join(missing_skills[:3])}")
        if match_percentage < 70:
            recommendations.append("Focus on transferable skills and relevant projects")
        
        return SkillsGapAnalysis(
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            transferable_skills=[],  # Would be calculated with more sophisticated logic
            skill_match_percentage=match_percentage,
            recommendations=recommendations
        )
    
    def _calculate_match_score(self, user_profile: UserProfile, job: Job) -> float:
        """Calculate how well user matches the job"""
        score = 0.0
        
        # Skills matching (40% of score)
        if job.requirements and job.requirements.skills_required:
            user_skills_lower = [s.lower() for s in user_profile.skills]
            required_skills_lower = [s.lower() for s in job.requirements.skills_required]
            
            matching_skills = len([s for s in required_skills_lower if s in user_skills_lower])
            total_required = len(required_skills_lower)
            
            if total_required > 0:
                skills_score = (matching_skills / total_required) * 40
                score += skills_score
        else:
            score += 30  # Default if no specific skills listed
        
        # Experience level matching (25% of score)
        if job.requirements and job.requirements.experience_years:
            required_exp = job.requirements.experience_years
            user_exp = user_profile.experience_years
            
            if user_exp >= required_exp:
                exp_score = 25
            elif user_exp >= required_exp * 0.75:
                exp_score = 20
            elif user_exp >= required_exp * 0.5:
                exp_score = 15
            else:
                exp_score = 10
            
            score += exp_score
        else:
            score += 20  # Default if no experience specified
        
        # Job type preference (20% of score)
        if job.job_type in user_profile.preferred_job_types:
            score += 20
        elif job.job_type == JobType.FREELANCE and JobType.IT_PROGRAMMING in user_profile.preferred_job_types:
            score += 15  # Freelance IT work
        else:
            score += 10
        
        # Location preference (15% of score)
        if job.location.is_remote:
            score += 15 if user_profile.remote_preference in ['remote', 'hybrid'] else 10
        else:
            location_str = str(job.location)
            if any(loc in location_str for loc in user_profile.preferred_locations):
                score += 15
            else:
                score += 5
        
        return min(100.0, score)
    
    def _generate_optimized_cv(self, 
                              user_profile: UserProfile,
                              job: Job,
                              job_analysis: Dict[str, Any],
                              skills_gap: SkillsGapAnalysis,
                              cv_format: str) -> str:
        """Generate optimized CV using AI"""
        
        # Get base CV template
        base_cv = user_profile.get_cv_template("default") or self._create_basic_cv(user_profile)
        cv_template = self.cv_formats.get(cv_format, self.cv_formats['us'])
        
        # Get job type specific prompt
        job_type_prompt = self.job_type_prompts.get(job.job_type, "")
        
        optimization_prompt = f"""
        You are an expert CV optimizer. Please optimize this CV for the following job:

        JOB INFORMATION:
        Title: {job.title}
        Company: {job.company.name}
        Job Type: {job.job_type.value}
        Location: {job.location}
        
        Job Description:
        {job.description[:2000]}  # Limit description length
        
        JOB ANALYSIS:
        {json.dumps(job_analysis, indent=2)}
        
        SKILLS GAP ANALYSIS:
        - Matching Skills: {', '.join(skills_gap.matching_skills)}
        - Missing Skills: {', '.join(skills_gap.missing_skills)}
        - Match Percentage: {skills_gap.skill_match_percentage:.1f}%
        
        CURRENT CV:
        {base_cv}
        
        OPTIMIZATION INSTRUCTIONS:
        {job_type_prompt}
        
        CV FORMAT TEMPLATE:
        {cv_template}
        
        SPECIFIC REQUIREMENTS:
        1. Reorder sections to prioritize most relevant experience
        2. Incorporate keywords from job description naturally
        3. Quantify achievements with specific metrics where possible
        4. Highlight matching skills prominently
        5. Address missing skills through transferable experience
        6. Optimize for ATS parsing (clear headings, standard format)
        7. Keep CV to 1-2 pages maximum
        8. Use action verbs and professional language
        9. Ensure consistency in formatting and style
        10. Make the CV compelling and results-focused
        
        Return the optimized CV that maximizes the candidate's chances for this specific position.
        """
        
        try:
            optimized_cv = self._call_openai_api(optimization_prompt, temperature=0.3)
            return optimized_cv
            
        except Exception as e:
            self.logger.error(f"CV optimization failed: {e}")
            return base_cv  # Return original CV if optimization fails
    
    def _optimize_for_ats(self, cv_content: str, job: Job) -> Tuple[str, float]:
        """Optimize CV for Applicant Tracking Systems"""
        
        ats_prompt = f"""
        You are an ATS (Applicant Tracking System) optimization expert. 
        Please optimize this CV to score highly in ATS systems for this job:
        
        Job Title: {job.title}
        Job Type: {job.job_type.value}
        
        Key Requirements to Match:
        {job.description[:1000]}
        
        CURRENT CV:
        {cv_content}
        
        ATS OPTIMIZATION RULES:
        1. Use standard section headings (Experience, Education, Skills, etc.)
        2. Include exact keyword matches from job description
        3. Use simple, clean formatting without complex layouts
        4. Avoid graphics, tables, or unusual formatting
        5. Use standard fonts and bullet points
        6. Include relevant keywords in context, not just lists
        7. Use both acronyms and full forms (e.g., "AI" and "Artificial Intelligence")
        8. Ensure contact information is clearly formatted
        9. Use chronological order for work experience
        10. Include measurable achievements with numbers/percentages
        
        Return the ATS-optimized CV. Focus on keyword optimization while maintaining readability.
        """
        
        try:
            ats_optimized_cv = self._call_openai_api(ats_prompt, temperature=0.2)
            
            # Calculate ATS score
            ats_score = self._calculate_ats_score(ats_optimized_cv, job)
            
            return ats_optimized_cv, ats_score
            
        except Exception as e:
            self.logger.error(f"ATS optimization failed: {e}")
            return cv_content, 70.0  # Return original with default score
    
    def _generate_cover_letter(self, user_profile: UserProfile, job: Job, optimized_cv: str) -> str:
        """Generate personalized cover letter"""
        
        cover_letter_prompt = f"""
        Write a compelling, personalized cover letter for this job application:
        
        JOB INFORMATION:
        Title: {job.title}
        Company: {job.company.name}
        Job Type: {job.job_type.value}
        Company Industry: {job.company.industry or 'Not specified'}
        
        Job Description (first 1500 chars):
        {job.description[:1500]}
        
        CANDIDATE INFORMATION:
        Name: {user_profile.name}
        Current Title: {user_profile.current_title}
        Experience: {user_profile.experience_years} years
        Key Skills: {', '.join(user_profile.skills[:10])}
        
        COVER LETTER REQUIREMENTS:
        1. Address the hiring manager professionally
        2. Open with enthusiasm for the specific role and company
        3. Highlight 2-3 most relevant experiences that match job requirements
        4. Include specific achievements with quantifiable results
        5. Show knowledge of the company/industry when possible
        6. Explain why you're interested in this specific opportunity
        7. Close with a strong call-to-action
        8. Keep it to 3-4 paragraphs, maximum 400 words
        9. Professional but engaging tone
        10. Customize for the specific job, not generic
        
        Write a cover letter that makes the candidate stand out while staying professional.
        """
        
        try:
            cover_letter = self._call_openai_api(cover_letter_prompt, temperature=0.4)
            return cover_letter
            
        except Exception as e:
            self.logger.error(f"Cover letter generation failed: {e}")
            return self._generate_fallback_cover_letter(user_profile, job)
    
    def generate_freelance_proposal(self, user_profile: UserProfile, project: Job) -> str:
        """Generate freelance project proposal"""
        
        proposal_prompt = f"""
        Write a winning freelance proposal for this project:
        
        PROJECT INFORMATION:
        Title: {project.title}
        Client: {project.company.name}
        Project Type: {project.job_type.value}
        Budget: {project.salary if project.salary else 'Not specified'}
        
        Project Description:
        {project.description}
        
        FREELANCER INFORMATION:
        Name: {user_profile.name}
        Experience: {user_profile.experience_years} years
        Skills: {', '.join(user_profile.skills)}
        Portfolio: {user_profile.portfolio_url or 'Available upon request'}
        
        PROPOSAL REQUIREMENTS:
        1. Personalized greeting addressing the client's needs
        2. Demonstrate understanding of the project requirements
        3. Highlight relevant experience and past similar projects
        4. Provide a clear project timeline and deliverables
        5. Suggest competitive pricing strategy
        6. Include portfolio examples or case studies
        7. Address potential concerns proactively
        8. Professional but approachable tone
        9. Clear next steps and availability
        10. Keep it concise but comprehensive (300-500 words)
        
        Write a proposal that wins the project by showing expertise and value.
        """
        
        try:
            proposal = self._call_openai_api(proposal_prompt, temperature=0.4)
            return proposal
            
        except Exception as e:
            self.logger.error(f"Proposal generation failed: {e}")
            return self._generate_fallback_proposal(user_profile, project)
    
    def _calculate_ats_score(self, cv_content: str, job: Job) -> float:
        """Calculate ATS compatibility score"""
        score = 100.0
        
        # Check for ATS-friendly elements
        cv_lower = cv_content.lower()
        
        # Standard section headings
        standard_headings = ['experience', 'education', 'skills', 'contact']
        found_headings = sum(1 for heading in standard_headings if heading in cv_lower)
        if found_headings < 3:
            score -= 20
        
        # Keyword density
        if job.description:
            job_keywords = re.findall(r'\b\w+\b', job.description.lower())
            cv_keywords = re.findall(r'\b\w+\b', cv_lower)
            
            keyword_matches = len(set(job_keywords) & set(cv_keywords))
            total_job_keywords = len(set(job_keywords))
            
            if total_job_keywords > 0:
                keyword_score = (keyword_matches / total_job_keywords) * 30
                score = score - 30 + keyword_score
        
        # Format compliance
        if 'http://' in cv_content or 'https://' in cv_content:
            score -= 5  # URLs can confuse some ATS systems
        
        if len(re.findall(r'[^\x00-\x7F]', cv_content)) > 10:
            score -= 10  # Too many special characters
        
        return max(0.0, min(100.0, score))
    
    def _call_openai_api(self, prompt: str, temperature: float = 0.3, max_tokens: int = 2000) -> str:
        """Make API call to OpenAI"""
        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert CV writer and career consultant with 15+ years of experience helping people land their dream jobs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"OpenAI API call failed: {e}")
            raise CVOptimizationError(f"AI service unavailable: {e}")
    
    def _create_basic_cv(self, user_profile: UserProfile) -> str:
        """Create basic CV from user profile if no template exists"""
        cv = f"""
{user_profile.name}
{user_profile.email} | {user_profile.phone or 'Phone: TBD'}
{user_profile.linkedin_url or ''} | {user_profile.portfolio_url or ''}

PROFESSIONAL SUMMARY
{user_profile.current_title or 'Professional'} with {user_profile.experience_years} years of experience.

SKILLS
{', '.join(user_profile.skills)}

EXPERIENCE
{user_profile.current_title or 'Current Position'}
• Add your work experience here

EDUCATION
{user_profile.education[0]['degree'] if user_profile.education else 'Add your education here'}

CERTIFICATIONS
{', '.join(user_profile.certifications) if user_profile.certifications else 'Add certifications here'}
        """
        
        return cv.strip()
    
    # ===== CV FORMAT TEMPLATES =====
    
    def _get_us_cv_template(self) -> str:
        return """
US CV Format Guidelines:
- Start with contact information
- Professional summary (2-3 lines)
- Core competencies/skills section
- Professional experience (reverse chronological)
- Education
- Additional sections (certifications, projects, etc.)
- Use action verbs and quantified achievements
- 1-2 pages maximum
- No photo or personal information
        """
    
    def _get_eu_cv_template(self) -> str:
        return """
EU CV Format Guidelines:
- Contact information with photo (optional)
- Professional profile/summary
- Work experience (reverse chronological with detailed descriptions)
- Education and training
- Skills (languages, technical, soft skills)
- Additional information (hobbies, volunteering)
- Can be 2-3 pages
- More detailed than US format
        """
    
    def _get_uk_cv_template(self) -> str:
        return """
UK CV Format Guidelines:
- Personal details (no photo unless specifically requested)
- Personal profile/statement
- Key skills and competencies
- Employment history (reverse chronological)
- Education and qualifications
- Additional sections (interests, references available on request)
- 2 pages maximum typically
- Professional tone throughout
        """
    
    def _get_freelance_template(self) -> str:
        return """
Freelance Profile Guidelines:
- Professional headline/tagline
- Brief personal introduction
- Core services and expertise
- Portfolio highlights and case studies
- Client testimonials or success stories
- Technical skills and tools
- Pricing structure or rate information
- Availability and contact information
- Focus on results and client value
        """
    
    # ===== JOB TYPE SPECIFIC PROMPTS =====
    
    def _get_civil_engineering_prompt(self) -> str:
        return """
        For Civil Engineering positions, emphasize:
        - Specific project experience and scale (budget, timeline, team size)
        - Technical software proficiency (AutoCAD, Civil 3D, Revit, etc.)
        - Professional certifications (PE, EIT, etc.) 
        - Regulatory compliance and building codes knowledge
        - Project management and team leadership
        - Safety record and compliance
        - Quantifiable project outcomes and success metrics
        """
    
    def _get_it_programming_prompt(self) -> str:
        return """
        For IT/Programming positions, emphasize:
        - Programming languages and technical stack matching job requirements
        - Specific projects with technologies, scale, and outcomes
        - Code quality practices (testing, documentation, version control)
        - Agile/Scrum experience and methodologies
        - Performance improvements and optimization achievements
        - Open source contributions or personal projects
        - Problem-solving abilities and technical leadership
        """
    
    def _get_digital_marketing_prompt(self) -> str:
        return """
        For Digital Marketing positions, emphasize:
        - Campaign performance metrics (ROI, conversion rates, growth)
        - Platform expertise (Google Ads, Facebook, LinkedIn, etc.)
        - Analytics and data-driven decision making
        - Content creation and brand management
        - A/B testing and optimization experience
        - Budget management and cost efficiency
        - Cross-functional collaboration and communication skills
        """
    
    def _get_freelance_prompt(self) -> str:
        return """
        For Freelance projects, emphasize:
        - Relevant portfolio pieces and case studies
        - Client satisfaction and testimonials
        - Quick turnaround and reliable communication
        - Competitive pricing and value proposition
        - Specific deliverables and project outcomes
        - Availability and project timeline
        - Technical expertise and tool proficiency
        """
    
    def _load_ats_rules(self) -> Dict[str, Any]:
        """Load ATS optimization rules"""
        return {
            'preferred_sections': [
                'Contact Information',
                'Professional Summary', 
                'Work Experience',
                'Education',
                'Skills',
                'Certifications'
            ],
            'avoid_elements': [
                'tables', 'text boxes', 'headers/footers',
                'graphics', 'fancy formatting', 'multiple columns'
            ],
            'keyword_density': {
                'min': 1,  # Minimum keyword occurrences
                'max': 5,  # Maximum to avoid keyword stuffing
                'context_required': True  # Keywords should be in context
            }
        }
    
    def _fallback_job_analysis(self, job: Job) -> Dict[str, Any]:
        """Fallback job analysis if AI fails"""
        return {
            'required_skills': job.requirements.skills_required if job.requirements else [],
            'preferred_skills': job.requirements.skills_preferred if job.requirements else [],
            'key_responsibilities': ['Responsibilities as listed in job description'],
            'experience_level': job.requirements.experience_years if job.requirements else None,
            'education_requirements': job.requirements.education_level if job.requirements else None,
            'keywords': re.findall(r'\b\w+\b', job.title.lower()),
            'company_culture': 'Professional environment',
            'priorities': ['Technical expertise', 'Communication skills', 'Team collaboration']
        }
    
    def _generate_fallback_cover_letter(self, user_profile: UserProfile, job: Job) -> str:
        """Generate basic cover letter if AI fails"""
        return f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job.title} position at {job.company.name}. With {user_profile.experience_years} years of experience as a {user_profile.current_title}, I am confident that my skills and background make me an excellent fit for this role.

My expertise in {', '.join(user_profile.skills[:3])} aligns well with your requirements. I am particularly excited about the opportunity to contribute to {job.company.name}'s mission and would welcome the chance to discuss how I can add value to your team.

Thank you for your consideration. I look forward to hearing from you.

Best regards,
{user_profile.name}"""
    
    def _generate_fallback_proposal(self, user_profile: UserProfile, project: Job) -> str:
        """Generate basic freelance proposal if AI fails"""
        return f"""Hello,

I'm {user_profile.name}, a {user_profile.current_title} with {user_profile.experience_years} years of experience. I'm very interested in your {project.title} project.

My relevant skills include:
{chr(10).join(f'• {skill}' for skill in user_profile.skills[:5])}

I can deliver high-quality work within your timeline and budget. Please feel free to review my portfolio at {user_profile.portfolio_url or 'available upon request'}.

I'd love to discuss your project in more detail. When would be a good time for a brief call?

Best regards,
{user_profile.name}"""


# ===== SPECIALIZED OPTIMIZERS =====

class CivilEngineeringOptimizer(CVOptimizer):
    """Specialized optimizer for civil engineering positions"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        
        # Civil engineering specific keywords
        self.civil_keywords = [
            'structural analysis', 'concrete design', 'steel design', 'foundation design',
            'seismic design', 'building codes', 'project management', 'construction management',
            'autocad', 'civil 3d', 'revit', 'staad pro', 'etabs', 'safe', 'primavera',
            'geotechnical engineering', 'transportation engineering', 'water resources',
            'environmental engineering', 'surveying', 'gis'
        ]
    
    def optimize_for_civil_role(self, user_profile: UserProfile, job: Job) -> OptimizationResult:
        """Specialized optimization for civil engineering roles"""
        
        # Add civil-specific enhancements
        enhanced_prompt = f"""
        Additional Civil Engineering Focus:
        - Emphasize PE license status and professional registrations
        - Highlight major infrastructure projects (bridges, buildings, roads)
        - Include project values, timelines, and team sizes managed
        - Mention regulatory compliance and safety achievements
        - Showcase technical software proficiency with specific versions
        - Include continuing education and professional development
        - Highlight cross-disciplinary collaboration (architects, contractors, etc.)
        
        Project Portfolio Emphasis:
        - Detail specific engineering challenges solved
        - Quantify structural improvements or cost savings achieved
        - Mention awards or recognition received
        - Include diverse project types to show versatility
        """
        
        return super().optimize_cv_for_job(user_profile, job, cv_format='us')


class ITOptimizer(CVOptimizer):
    """Specialized optimizer for IT/Programming positions"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        
        # IT specific considerations
        self.tech_stack_categories = {
            'languages': ['python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust'],
            'frameworks': ['react', 'angular', 'vue', 'django', 'flask', 'spring', 'express', 'laravel'],
            'databases': ['postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch'],
            'cloud': ['aws', 'azure', 'gcp', 'kubernetes', 'docker', 'terraform'],
            'tools': ['git', 'jenkins', 'jira', 'confluence', 'slack', 'figma']
        }
    
    def optimize_for_tech_role(self, user_profile: UserProfile, job: Job) -> OptimizationResult:
        """Specialized optimization for IT/Programming roles"""
        
        # Analyze tech stack requirements
        tech_requirements = self._analyze_tech_stack(job.description)
        
        enhanced_prompt = f"""
        Additional IT/Programming Focus:
        - Match specific programming languages and frameworks mentioned
        - Highlight relevant technical projects with code repositories
        - Emphasize problem-solving and analytical thinking
        - Include performance metrics (page load times, user growth, etc.)
        - Showcase continuous learning and technology adaptation
        - Mention agile methodologies and development practices
        - Include open source contributions or personal projects
        
        Technical Stack Analysis:
        {json.dumps(tech_requirements, indent=2)}
        
        GitHub/Portfolio Integration:
        - Reference specific repositories or live projects
        - Highlight code quality and documentation practices
        - Include technical blog posts or contributions
        """
        
        return super().optimize_cv_for_job(user_profile, job, cv_format='us')
    
    def _analyze_tech_stack(self, description: str) -> Dict[str, List[str]]:
        """Analyze technical requirements from job description"""
        desc_lower = description.lower()
        found_stack = {}
        
        for category, technologies in self.tech_stack_categories.items():
            found = [tech for tech in technologies if tech in desc_lower]
            if found:
                found_stack[category] = found
        
        return found_stack


class FreelanceOptimizer(CVOptimizer):
    """Specialized optimizer for freelance proposals"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
    
    def create_winning_proposal(self, user_profile: UserProfile, project: Job) -> Dict[str, str]:
        """Create a comprehensive freelance proposal package"""
        
        # Generate main proposal
        proposal = self.generate_freelance_proposal(user_profile, project)
        
        # Generate pricing strategy
        pricing_prompt = f"""
        Create a competitive pricing strategy for this freelance project:
        
        Project: {project.title}
        Client Budget: {project.salary if project.salary else 'Not specified'}
        Project Description: {project.description[:1000]}
        
        Freelancer Experience: {user_profile.experience_years} years
        Relevant Skills: {', '.join(user_profile.skills[:8])}
        
        Provide:
        1. Recommended pricing approach (hourly vs fixed)
        2. Competitive rate justification
        3. Value propositions that justify the rate
        4. Payment terms suggestions
        5. Scope clarification questions
        
        Keep it brief and strategic.
        """
        
        try:
            pricing_strategy = self._call_openai_api(pricing_prompt, temperature=0.3)
        except:
            pricing_strategy = "Competitive rates based on project scope and timeline."
        
        # Generate project timeline
        timeline_prompt = f"""
        Create a realistic project timeline for this freelance project:
        
        Project: {project.title}
        Description: {project.description[:800]}
        
        Consider:
        1. Project discovery and planning phase
        2. Development/implementation milestones
        3. Review and revision cycles
        4. Final delivery and handover
        5. Buffer time for unexpected issues
        
        Provide a clear timeline with milestones.
        """
        
        try:
            timeline = self._call_openai_api(timeline_prompt, temperature=0.3)
        except:
            timeline = "Timeline will be determined based on project requirements during our initial discussion."
        
        return {
            'proposal': proposal,
            'pricing_strategy': pricing_strategy,
            'timeline': timeline
        }


# ===== BULK OPTIMIZATION TOOLS =====

class BulkOptimizer:
    """Handle optimization for multiple jobs at once"""
    
    def __init__(self, cv_optimizer: CVOptimizer):
        self.optimizer = cv_optimizer
        self.logger = logging.getLogger(__name__)
    
    def optimize_for_multiple_jobs(self, 
                                 user_profile: UserProfile,
                                 jobs: List[Job],
                                 max_concurrent: int = 5) -> Dict[int, OptimizationResult]:
        """Optimize CV for multiple jobs"""
        results = {}
        
        self.logger.info(f"Starting bulk optimization for {len(jobs)} jobs")
        
        for i, job in enumerate(jobs):
            try:
                self.logger.info(f"Optimizing CV {i+1}/{len(jobs)}: {job.title}")
                
                result = self.optimizer.optimize_cv_for_job(
                    user_profile=user_profile,
                    job=job,
                    cv_format='us',
                    include_cover_letter=True
                )
                
                results[job.id] = result
                
                # Small delay between optimizations to avoid rate limiting
                if i < len(jobs) - 1:
                    time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"Failed to optimize for job {job.id}: {e}")
                continue
        
        self.logger.info(f"Bulk optimization completed: {len(results)} successful")
        return results
    
    def generate_optimization_report(self, 
                                   optimization_results: Dict[int, OptimizationResult]) -> str:
        """Generate summary report of bulk optimization"""
        
        total_jobs = len(optimization_results)
        avg_match_score = sum(r.match_score for r in optimization_results.values()) / total_jobs
        avg_ats_score = sum(r.ats_score for r in optimization_results.values()) / total_jobs
        
        # Count improvements
        all_improvements = []
        for result in optimization_results.values():
            all_improvements.extend(result.improvements_made)
        
        improvement_counts = {}
        for improvement in all_improvements:
            improvement_counts[improvement] = improvement_counts.get(improvement, 0) + 1
        
        report = f"""
BULK CV OPTIMIZATION REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUMMARY:
- Total Jobs Optimized: {total_jobs}
- Average Match Score: {avg_match_score:.1f}%
- Average ATS Score: {avg_ats_score:.1f}%

COMMON IMPROVEMENTS MADE:
"""
        
        for improvement, count in sorted(improvement_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_jobs) * 100
            report += f"- {improvement}: {count} jobs ({percentage:.1f}%)\n"
        
        report += f"""
RECOMMENDATIONS:
- Focus on jobs with match scores above {avg_match_score:.0f}%
- Consider additional training for commonly missing skills
- Update master CV template with most frequent optimizations
        """
        
        return report


# ===== UTILITY FUNCTIONS =====

def test_cv_optimizer():
    """Test CV optimizer functionality"""
    print("Testing CV Optimizer")
    print("=" * 40)
    
    # Note: This requires a valid OpenAI API key
    # For testing without API key, we'll simulate the process
    
    from core.database.models import create_sample_job, create_sample_user_profile
    
    # Create test data
    user_profile = create_sample_user_profile()
    job = create_sample_job()
    
    print(f"User: {user_profile.name}")
    print(f"Job: {job.title} at {job.company.name}")
    print(f"Job Type: {job.job_type.value}")
    
    # Test without actual API call
    print("\nSimulating CV optimization process...")
    print("1. ✓ Analyzing job requirements")
    print("2. ✓ Performing skills gap analysis")
    print("3. ✓ Calculating match score")
    print("4. ✓ Generating optimized CV")
    print("5. ✓ Optimizing for ATS")
    print("6. ✓ Creating cover letter")
    
    print("\nCV Optimization would complete here with actual API key.")
    print("Expected outputs:")
    print("- Optimized CV tailored to job requirements")
    print("- Personalized cover letter")
    print("- ATS compatibility score")
    print("- Match score improvement")
    

def create_optimizer_with_config(api_key: str, job_type: JobType = None) -> CVOptimizer:
    """Factory function to create appropriate optimizer"""
    
    if job_type == JobType.CIVIL_ENGINEERING:
        return CivilEngineeringOptimizer(api_key)
    elif job_type == JobType.IT_PROGRAMMING:
        return ITOptimizer(api_key)
    elif job_type == JobType.FREELANCE:
        return FreelanceOptimizer(api_key)
    else:
        return CVOptimizer(api_key)


if __name__ == "__main__":
    test_cv_optimizer()