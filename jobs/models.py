from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import EmployerProfile, GraduateProfile


class Job(models.Model):
    """A vacancy posted by an employer (section 3.6.4, Jobs)."""

    JOB_TYPE_CHOICES = GraduateProfile.JOB_TYPE_CHOICES
    EXPERIENCE_CHOICES = [
        ("entry", "Entry Level"),
        ("junior", "Junior (1-2 years)"),
        ("mid", "Mid Level (3-5 years)"),
        ("senior", "Senior (5+ years)"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("closed", "Closed"),
    ]
    # The occupational category a vacancy belongs to. Job boards group
    # vacancies this way, and it also supplies the independent relevance
    # label used by the evaluation in section 4.6.2: it is assigned when the
    # vacancy is created and is not derived from anything the recommendation
    # engine computes.
    CATEGORY_CHOICES = [
        ("computer science", "Information Technology"),
        ("accounting", "Accounting and Finance"),
        ("marketing", "Marketing and Sales"),
        ("business administration", "Business and Administration"),
        ("human resource management", "Human Resources"),
        ("civil engineering", "Civil Engineering"),
        ("mechanical engineering", "Mechanical Engineering"),
        ("electrical engineering", "Electrical Engineering"),
        ("biochemistry", "Science and Laboratory"),
        ("mass communication", "Media and Communication"),
        ("economics", "Economics and Research"),
        ("law", "Legal"),
        ("education", "Education"),
    ]

    employer = models.ForeignKey(EmployerProfile, on_delete=models.CASCADE, related_name="jobs")
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    required_skills = models.TextField(help_text="Comma-separated list of required skills.")
    location = models.CharField(max_length=100)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default="full_time")
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default="entry")
    salary_min = models.PositiveIntegerField(blank=True, null=True)
    salary_max = models.PositiveIntegerField(blank=True, null=True)
    date_posted = models.DateTimeField(default=timezone.now)
    deadline = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")

    class Meta:
        ordering = ["-date_posted"]

    def __str__(self):
        return f"{self.title} at {self.employer.company_name}"

    def skill_list(self):
        return [s.strip() for s in self.required_skills.split(",") if s.strip()]

    def job_document(self):
        """Text document fed to the TF-IDF vectoriser (section 3.6.6).

        The title and required skills are repeated so that they carry more
        weight than the description. Descriptions share a great deal of
        boilerplate across vacancies, and left unweighted that common text
        dominates the vectors and drowns out the terms that actually
        distinguish one vacancy from another.
        """
        title = (self.title + " ") * 3
        skills = (self.required_skills.replace(",", " ") + " ") * 3
        parts = [title, skills, self.description, self.get_job_type_display(), self.location]
        return " ".join(p for p in parts if p).lower()

    def salary_display(self):
        if self.salary_min and self.salary_max:
            return f"N{self.salary_min:,} - N{self.salary_max:,}"
        if self.salary_min:
            return f"From N{self.salary_min:,}"
        return "Not disclosed"

    def posted_ago(self):
        days = (timezone.now().date() - self.date_posted.date()).days
        if days == 0:
            return "today"
        if days == 1:
            return "yesterday"
        if days < 30:
            return f"{days} days ago"
        return "on " + self.date_posted.strftime("%d %b %Y")

    def is_new(self):
        return (timezone.now().date() - self.date_posted.date()).days <= 3


class Application(models.Model):
    """A graduate's application to a vacancy (section 3.6.4, Applications)."""

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("shortlisted", "Shortlisted"),
        ("rejected", "Rejected"),
    ]

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    graduate = models.ForeignKey(GraduateProfile, on_delete=models.CASCADE, related_name="applications")
    date_applied = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted")

    class Meta:
        ordering = ["-date_applied"]
        constraints = [
            models.UniqueConstraint(fields=["job", "graduate"], name="unique_application"),
        ]

    def __str__(self):
        return f"{self.graduate.user.full_name} -> {self.job.title}"


class Interaction(models.Model):
    """Behavioural log feeding collaborative filtering (section 3.6.4, Interactions).

    Written on every job view, save and application. Without this table the
    collaborative component of the hybrid recommender has nothing to learn from.
    """

    VIEW = "view"
    SAVE = "save"
    APPLY = "apply"
    TYPE_CHOICES = [
        (VIEW, "View"),
        (SAVE, "Save"),
        (APPLY, "Apply"),
    ]
    # Implicit-feedback weights: an application signals far more interest than a view.
    WEIGHTS = {VIEW: 1.0, SAVE: 3.0, APPLY: 5.0}

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interactions")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="interactions")
    interaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=VIEW)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "job"]),
        ]

    def __str__(self):
        return f"{self.user.full_name} {self.interaction_type} {self.job.title}"

    @property
    def weight(self):
        return self.WEIGHTS.get(self.interaction_type, 1.0)
