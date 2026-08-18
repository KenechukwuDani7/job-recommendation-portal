"""Populate the database with a realistic vacancy corpus and test graduates.

A recommender scored against five vacancies produces embarrassing output in a
demonstration. This command builds a corpus large enough for TF-IDF weighting
to behave sensibly and for the evaluation in section 4.6.2 to mean something.
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import EmployerProfile, GraduateProfile, User
from jobs.models import Application, Interaction, Job

COMPANIES = [
    ("Andela", "Technology"), ("Flutterwave", "Financial Technology"),
    ("Paystack", "Financial Technology"), ("Interswitch", "Financial Technology"),
    ("Kuda Bank", "Banking"), ("Access Bank", "Banking"),
    ("Guaranty Trust Bank", "Banking"), ("Zenith Bank", "Banking"),
    ("First Bank of Nigeria", "Banking"), ("MTN Nigeria", "Telecommunications"),
    ("Airtel Nigeria", "Telecommunications"), ("Globacom", "Telecommunications"),
    ("Dangote Group", "Manufacturing"), ("Nigerian Breweries", "Manufacturing"),
    ("Nestle Nigeria", "Manufacturing"), ("Unilever Nigeria", "Manufacturing"),
    ("Jumia Nigeria", "E-Commerce"), ("Konga", "E-Commerce"),
    ("PricewaterhouseCoopers", "Professional Services"),
    ("KPMG Nigeria", "Professional Services"), ("Deloitte Nigeria", "Professional Services"),
    ("Nigerian National Petroleum Company", "Oil and Gas"),
    ("Seplat Energy", "Oil and Gas"), ("TotalEnergies Nigeria", "Oil and Gas"),
    ("Julius Berger Nigeria", "Construction"), ("Lafarge Africa", "Construction"),
    ("Reckitt Benckiser", "Consumer Goods"), ("Chi Limited", "Consumer Goods"),
    ("Sterling Bank", "Banking"), ("Wema Bank", "Banking"),
    ("SystemSpecs", "Technology"), ("Softcom", "Technology"),
    ("Cowrywise", "Financial Technology"), ("PiggyVest", "Financial Technology"),
    ("Helium Health", "Health Technology"), ("Reliance Health", "Health Technology"),
    ("British Council Nigeria", "Education"),
    ("Nigerian Bottling Company", "Manufacturing"),
]

# (title, required skills, description body, field tag)
TEMPLATES = [
    ("Junior Backend Developer", "Python, Django, SQL, REST APIs, Git",
     "build and maintain server-side application logic, design and consume REST APIs, and work with relational databases",
     "computer science"),
    ("Frontend Developer", "HTML, CSS, JavaScript, React, Git",
     "implement responsive user interfaces, translate designs into working pages, and integrate with backend services",
     "computer science"),
    ("Software Engineer (Graduate Trainee)", "Java, Python, Data Structures, Algorithms, Git",
     "participate in a structured graduate programme covering software design, development and testing",
     "computer science"),
    ("Data Analyst", "SQL, Excel, Python, Power BI, Statistics",
     "analyse business data, build dashboards and reports, and present findings to stakeholders",
     "computer science"),
    ("Data Scientist (Entry Level)", "Python, Machine Learning, Pandas, Statistics, SQL",
     "build predictive models, carry out exploratory data analysis, and communicate insights to the business",
     "computer science"),
    ("Mobile Application Developer", "Flutter, Dart, Android, REST APIs, Git",
     "develop and maintain cross-platform mobile applications and integrate them with backend services",
     "computer science"),
    ("Quality Assurance Engineer", "Manual Testing, Test Cases, Selenium, Bug Tracking",
     "design and execute test plans, log defects, and verify fixes before release",
     "computer science"),
    ("IT Support Officer", "Networking, Hardware, Troubleshooting, Windows, Customer Support",
     "provide first-line technical support, maintain workstations, and resolve network issues",
     "computer science"),
    ("Cybersecurity Analyst (Entry Level)", "Network Security, Linux, Incident Response, Firewalls",
     "monitor security alerts, investigate incidents, and support the hardening of company systems",
     "computer science"),
    ("Accountant", "Accounting, Financial Reporting, Excel, Taxation, Reconciliation",
     "prepare financial statements, reconcile accounts, and support statutory reporting",
     "accounting"),
    ("Audit Associate", "Auditing, Accounting, Excel, Financial Analysis, Attention to Detail",
     "carry out audit fieldwork, test controls, and prepare audit working papers",
     "accounting"),
    ("Finance Officer", "Financial Analysis, Budgeting, Excel, Accounting, Reporting",
     "support budget preparation, monitor expenditure, and prepare management accounts",
     "accounting"),
    ("Tax Analyst", "Taxation, Accounting, Compliance, Excel, Financial Reporting",
     "prepare tax computations, file statutory returns, and support tax compliance reviews",
     "accounting"),
    ("Marketing Executive", "Marketing, Communication, Social Media, Content Creation, Analytics",
     "plan and execute marketing campaigns, manage social channels, and report on campaign performance",
     "marketing"),
    ("Digital Marketing Officer", "SEO, Social Media, Google Analytics, Content Marketing, Copywriting",
     "run digital campaigns, optimise web content for search, and track acquisition metrics",
     "marketing"),
    ("Brand Manager (Graduate)", "Branding, Marketing, Communication, Market Research, Presentation",
     "support brand planning, coordinate campaigns, and monitor competitor activity",
     "marketing"),
    ("Sales Representative", "Sales, Negotiation, Communication, Customer Relationship Management",
     "develop new business, manage a client portfolio, and meet monthly sales targets",
     "marketing"),
    ("Human Resources Officer", "Recruitment, Employee Relations, HR Policies, Communication, Record Keeping",
     "coordinate recruitment, maintain employee records, and support HR operations",
     "human resource management"),
    ("Recruitment Officer", "Recruitment, Interviewing, Communication, Applicant Tracking, Onboarding",
     "manage the end-to-end recruitment cycle from sourcing through to onboarding",
     "human resource management"),
    ("Civil Engineer (Graduate)", "AutoCAD, Structural Analysis, Project Management, Site Supervision",
     "support site supervision, prepare technical drawings, and monitor construction quality",
     "civil engineering"),
    ("Site Engineer", "Site Supervision, AutoCAD, Quality Control, Construction, Safety",
     "supervise daily site activities, enforce safety standards, and report on project progress",
     "civil engineering"),
    ("Mechanical Engineer (Trainee)", "Mechanical Design, AutoCAD, Maintenance, Troubleshooting",
     "assist with equipment maintenance, carry out inspections, and support plant reliability",
     "mechanical engineering"),
    ("Maintenance Engineer", "Preventive Maintenance, Mechanical Systems, Troubleshooting, Safety",
     "plan and execute preventive maintenance schedules and respond to equipment breakdowns",
     "mechanical engineering"),
    ("Electrical Engineer (Graduate)", "Electrical Design, AutoCAD, Power Systems, Maintenance",
     "support the design and maintenance of electrical installations and power distribution systems",
     "electrical engineering"),
    ("Instrumentation Engineer", "Instrumentation, Control Systems, PLC, Calibration, Safety",
     "install, calibrate and maintain instrumentation and control equipment",
     "electrical engineering"),
    ("Business Analyst", "Requirements Gathering, Documentation, SQL, Excel, Stakeholder Management",
     "gather and document business requirements and support the delivery of process improvements",
     "business administration"),
    ("Operations Officer", "Operations, Process Improvement, Excel, Reporting, Coordination",
     "coordinate daily operations, monitor service levels, and prepare operational reports",
     "business administration"),
    ("Customer Service Representative", "Customer Support, Communication, Problem Solving, CRM",
     "handle customer enquiries across channels and resolve complaints within agreed service levels",
     "business administration"),
    ("Graduate Management Trainee", "Leadership, Communication, Analysis, Teamwork, Presentation",
     "rotate through core business functions on a structured graduate development programme",
     "business administration"),
    ("Supply Chain Officer", "Logistics, Inventory Management, Procurement, Excel, Coordination",
     "coordinate inbound and outbound logistics and maintain accurate inventory records",
     "business administration"),
    ("Laboratory Scientist", "Laboratory Techniques, Sample Analysis, Quality Control, Record Keeping",
     "carry out laboratory analyses, maintain equipment, and document results accurately",
     "biochemistry"),
    ("Quality Control Officer", "Quality Control, Laboratory Analysis, Documentation, Standards Compliance",
     "test incoming materials and finished products against defined quality standards",
     "biochemistry"),
    ("Research Assistant", "Research, Data Collection, Analysis, Report Writing, Statistics",
     "support ongoing research projects through data collection, analysis and reporting",
     "biochemistry"),
    ("Content Writer", "Writing, Editing, Research, SEO, Communication",
     "produce written content for digital channels and edit material for clarity and accuracy",
     "mass communication"),
    ("Communications Officer", "Communication, Public Relations, Writing, Media Relations, Social Media",
     "draft press material, manage media relationships, and support internal communication",
     "mass communication"),
    ("Graphic Designer", "Adobe Photoshop, Illustrator, Design, Branding, Creativity",
     "design visual assets for digital and print channels in line with brand guidelines",
     "mass communication"),
    ("Legal Officer", "Legal Research, Contract Review, Compliance, Drafting, Attention to Detail",
     "review contracts, conduct legal research, and support regulatory compliance",
     "law"),
    ("Teacher (Secondary School)", "Teaching, Lesson Planning, Classroom Management, Communication",
     "plan and deliver lessons, assess student progress, and maintain classroom discipline",
     "education"),
    ("Economist / Research Analyst", "Economic Analysis, Statistics, Excel, Research, Report Writing",
     "analyse economic data, prepare briefing notes, and support policy research",
     "economics"),
]

LOCATIONS = ["Lagos", "Abuja", "Port Harcourt", "Ibadan", "Enugu", "Kano", "Remote", "Benin City"]
LOCATION_WEIGHTS = [40, 18, 8, 6, 5, 4, 15, 4]
JOB_TYPES = ["full_time", "full_time", "full_time", "internship", "nysc", "contract", "part_time"]
EXPERIENCE = ["entry", "entry", "entry", "junior", "junior", "mid"]

FIRST_NAMES = ["Chidi", "Amaka", "Tunde", "Ngozi", "Emeka", "Funmi", "Ibrahim", "Zainab",
               "Obinna", "Blessing", "Yusuf", "Chioma", "Segun", "Aisha", "Kelechi",
               "Damilola", "Uche", "Halima", "Bayo", "Ifeoma", "Musa", "Temitope",
               "Nnamdi", "Fatima", "Olamide", "Grace", "Suleiman", "Adaeze", "Femi", "Rukayat"]
LAST_NAMES = ["Okafor", "Adeyemi", "Bello", "Eze", "Ogunleye", "Ibrahim", "Nwosu", "Balogun",
              "Umeh", "Lawal", "Chukwu", "Adebayo", "Musa", "Okonkwo", "Yusuf",
              "Oyelaran", "Nnaji", "Abubakar", "Afolabi", "Obi"]

INSTITUTIONS = ["University of Nigeria, Nsukka", "University of Lagos", "Ahmadu Bello University",
                "Obafemi Awolowo University", "University of Ibadan", "Covenant University",
                "Federal University of Technology, Owerri", "University of Benin",
                "Nnamdi Azikiwe University", "Bayero University Kano"]

CLASSES = ["first", "2:1", "2:1", "2:1", "2:2", "2:2", "hnd"]

# Field of study -> (degree, plausible skill sets for a graduate of that field)
FIELD_PROFILES = {
    "computer science": ("BSc Computer Science", [
        "Python, Django, SQL, Git, REST APIs, Problem Solving",
        "JavaScript, React, HTML, CSS, Git, Responsive Design",
        "Java, Data Structures, Algorithms, SQL, Object Oriented Programming",
        "Python, Machine Learning, Pandas, Statistics, SQL, Data Analysis",
        "Networking, Linux, Troubleshooting, Hardware, Customer Support"]),
    "accounting": ("BSc Accounting", [
        "Accounting, Excel, Financial Reporting, Taxation, Reconciliation",
        "Auditing, Accounting, Financial Analysis, Excel, Attention to Detail",
        "Accounting, Budgeting, Excel, Reporting, Financial Analysis"]),
    "marketing": ("BSc Marketing", [
        "Marketing, Social Media, Communication, Content Creation, Analytics",
        "SEO, Digital Marketing, Google Analytics, Copywriting, Social Media",
        "Sales, Negotiation, Communication, Customer Relationship Management"]),
    "business administration": ("BSc Business Administration", [
        "Requirements Gathering, Excel, Documentation, Stakeholder Management, SQL",
        "Operations, Coordination, Excel, Reporting, Process Improvement",
        "Customer Support, Communication, Problem Solving, CRM, Teamwork"]),
    "civil engineering": ("BEng Civil Engineering", [
        "AutoCAD, Structural Analysis, Site Supervision, Project Management",
        "Construction, Quality Control, AutoCAD, Safety, Site Supervision"]),
    "mechanical engineering": ("BEng Mechanical Engineering", [
        "Mechanical Design, AutoCAD, Maintenance, Troubleshooting, Safety",
        "Preventive Maintenance, Mechanical Systems, Troubleshooting, Safety"]),
    "electrical engineering": ("BEng Electrical Engineering", [
        "Electrical Design, AutoCAD, Power Systems, Maintenance",
        "Instrumentation, Control Systems, PLC, Calibration, Safety"]),
    "human resource management": ("BSc Human Resource Management", [
        "Recruitment, Employee Relations, Communication, HR Policies, Onboarding",
        "Recruitment, Interviewing, Applicant Tracking, Communication, Record Keeping"]),
    "biochemistry": ("BSc Biochemistry", [
        "Laboratory Techniques, Sample Analysis, Quality Control, Record Keeping",
        "Research, Data Collection, Analysis, Report Writing, Statistics"]),
    "mass communication": ("BSc Mass Communication", [
        "Writing, Editing, Research, SEO, Communication",
        "Public Relations, Media Relations, Writing, Social Media, Communication",
        "Adobe Photoshop, Illustrator, Design, Branding, Creativity"]),
    "economics": ("BSc Economics", [
        "Economic Analysis, Statistics, Excel, Research, Report Writing"]),
    "law": ("LLB Law", [
        "Legal Research, Contract Review, Compliance, Drafting, Attention to Detail"]),
    "education": ("BEd Education", [
        "Teaching, Lesson Planning, Classroom Management, Communication"]),
}

DESCRIPTION = (
    "{company} is seeking a {title} to join its {industry} team in {location}. "
    "The successful candidate will {body}. "
    "This is a {job_type} role suited to an {experience} level candidate. "
    "Applicants should hold a relevant degree and demonstrate strong analytical and "
    "communication skills. Experience with {skills} will be an advantage. "
    "{company} offers a supportive working environment and clear opportunities for "
    "professional development."
)


class Command(BaseCommand):
    help = "Seed the database with employers, vacancies, graduate profiles and interactions."

    def add_arguments(self, parser):
        parser.add_argument("--jobs", type=int, default=150)
        parser.add_argument("--graduates", type=int, default=30)
        parser.add_argument("--flush", action="store_true",
                            help="Delete existing non-superuser data first.")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)  # reproducible corpus so evaluation runs are repeatable

        if options["flush"]:
            Interaction.objects.all().delete()
            Application.objects.all().delete()
            Job.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write("Existing seed data removed.")

        employers = self._create_employers()
        jobs = self._create_jobs(employers, options["jobs"])
        graduates = self._create_graduates(options["graduates"])
        self._create_interactions(graduates, jobs)

        self.stdout.write(self.style.SUCCESS(
            "Seeded {} employers, {} vacancies, {} graduates, {} interactions, "
            "{} applications.".format(
                len(employers), len(jobs), len(graduates),
                Interaction.objects.count(), Application.objects.count())
        ))
        first = graduates[0].user.email if graduates else "none"
        self.stdout.write("Test graduate login: {} / testpass123".format(first))

    def _create_employers(self):
        employers = []
        for name, industry in COMPANIES:
            slug = name.lower().replace(" ", "").replace(",", "")[:20]
            email = "hr@{}.com".format(slug)
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"username": email,
                          "full_name": "{} Recruitment".format(name),
                          "role": User.EMPLOYER},
            )
            if created:
                user.set_password("testpass123")
                user.save()
            profile, _ = EmployerProfile.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": name,
                    "industry": industry,
                    "description": "{} is a leading organisation in the {} sector in "
                                   "Nigeria.".format(name, industry.lower()),
                },
            )
            employers.append(profile)
        return employers

    def _create_jobs(self, employers, count):
        jobs = []
        for i in range(count):
            title, skills, body, field = TEMPLATES[i % len(TEMPLATES)]
            employer = random.choice(employers)
            location = random.choices(LOCATIONS, weights=LOCATION_WEIGHTS, k=1)[0]
            job_type = random.choice(JOB_TYPES)
            experience = random.choice(EXPERIENCE)
            salary_min = random.choice([120, 150, 200, 250, 300, 400, 450]) * 1000
            salary_max = salary_min + random.choice([100, 150, 200, 250]) * 1000
            posted = timezone.now() - timedelta(days=random.randint(0, 45),
                                                hours=random.randint(0, 23))
            disclose = random.random() > 0.2
            job = Job.objects.create(
                employer=employer,
                title=title,
                description=DESCRIPTION.format(
                    company=employer.company_name, title=title,
                    industry=employer.industry.lower(), location=location,
                    body=body, job_type=job_type.replace("_", " "),
                    experience=experience, skills=skills),
                required_skills=skills,
                location=location,
                job_type=job_type,
                experience_level=experience,
                salary_min=salary_min if disclose else None,
                salary_max=salary_max if disclose else None,
                date_posted=posted,
                deadline=(posted + timedelta(days=random.randint(20, 60))).date(),
            )
            job.seed_field = field
            jobs.append(job)
        return jobs

    def _create_graduates(self, count):
        graduates = []
        fields = list(FIELD_PROFILES.keys())
        used = set()
        for i in range(count):
            first = FIRST_NAMES[i % len(FIRST_NAMES)]
            last = LAST_NAMES[i % len(LAST_NAMES)]
            email = "{}.{}@example.com".format(first.lower(), last.lower())
            n = 1
            while email in used:
                n += 1
                email = "{}.{}{}@example.com".format(first.lower(), last.lower(), n)
            used.add(email)

            field = fields[i % len(fields)]
            degree, skill_options = FIELD_PROFILES[field]
            user, created = User.objects.get_or_create(
                email=email,
                defaults={"username": email,
                          "full_name": "{} {}".format(first, last),
                          "role": User.GRADUATE},
            )
            if created:
                user.set_password("testpass123")
                user.save()
            profile, _ = GraduateProfile.objects.get_or_create(
                user=user,
                defaults={
                    "degree": degree,
                    "class_of_degree": random.choice(CLASSES),
                    "institution": random.choice(INSTITUTIONS),
                    "field_of_study": field.title(),
                    "skills": random.choice(skill_options),
                    "preferred_location": random.choices(
                        LOCATIONS, weights=LOCATION_WEIGHTS, k=1)[0],
                    "preferred_job_type": random.choice(
                        ["full_time", "full_time", "internship", "nysc"]),
                    "years_of_experience": random.choice([0, 0, 0, 1, 1, 2]),
                },
            )
            graduates.append(profile)
        return graduates

    def _create_interactions(self, graduates, jobs):
        """Plausible implicit feedback: graduates engage mostly within their own field.

        Random interactions across unrelated fields would give the collaborative
        component nothing but noise to learn from.
        """
        for grad in graduates:
            field = grad.field_of_study.lower()
            related = [j for j in jobs if getattr(j, "seed_field", "") == field]
            pool = related if len(related) >= 6 else jobs
            viewed = random.sample(pool, min(len(pool), random.randint(6, 14)))
            for job in viewed:
                Interaction.objects.create(user=grad.user, job=job,
                                           interaction_type=Interaction.VIEW)
            for job in random.sample(viewed, min(len(viewed), random.randint(1, 4))):
                Interaction.objects.create(user=grad.user, job=job,
                                           interaction_type=Interaction.SAVE)
            for job in random.sample(viewed, min(len(viewed), random.randint(1, 3))):
                _, created = Application.objects.get_or_create(job=job, graduate=grad)
                if created:
                    Interaction.objects.create(user=grad.user, job=job,
                                               interaction_type=Interaction.APPLY)
