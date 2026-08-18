from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Email is the login identifier, so username is derived rather than asked for."""

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        extra.setdefault("username", email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", "admin")
        extra.setdefault("full_name", "Administrator")
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    """Single user table serving all three roles (section 3.6.4, Users)."""

    GRADUATE = "graduate"
    EMPLOYER = "employer"
    ADMIN = "admin"
    ROLE_CHOICES = [
        (GRADUATE, "Graduate"),
        (EMPLOYER, "Employer"),
        (ADMIN, "Administrator"),
    ]

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=GRADUATE)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    @property
    def is_graduate(self):
        return self.role == self.GRADUATE

    @property
    def is_employer(self):
        return self.role == self.EMPLOYER


class GraduateProfile(models.Model):
    """Graduate attributes from which the recommender builds its profile vector."""

    CLASS_CHOICES = [
        ("first", "First Class"),
        ("2:1", "Second Class Upper"),
        ("2:2", "Second Class Lower"),
        ("third", "Third Class"),
        ("hnd", "HND"),
        ("ond", "OND"),
    ]
    JOB_TYPE_CHOICES = [
        ("full_time", "Full Time"),
        ("part_time", "Part Time"),
        ("contract", "Contract"),
        ("internship", "Internship"),
        ("nysc", "NYSC"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="graduate_profile")
    degree = models.CharField(max_length=120, blank=True)
    class_of_degree = models.CharField(max_length=20, choices=CLASS_CHOICES, blank=True)
    institution = models.CharField(max_length=150, blank=True)
    field_of_study = models.CharField(max_length=150, blank=True)
    skills = models.TextField(blank=True, help_text="Comma-separated list of skills.")
    preferred_location = models.CharField(max_length=100, blank=True)
    preferred_job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, blank=True)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    cv = models.FileField(upload_to="cvs/", blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.full_name}"

    def skill_list(self):
        return [s.strip() for s in self.skills.split(",") if s.strip()]

    def profile_document(self):
        """Text document fed to the TF-IDF vectoriser (section 3.6.6)."""
        skills = (self.skills.replace(",", " ") + " ") * 3
        field = (self.field_of_study + " ") * 2
        parts = [
            field,
            skills,
            self.degree,
            self.get_preferred_job_type_display() if self.preferred_job_type else "",
            self.preferred_location,
        ]
        return " ".join(p for p in parts if p).lower()

    def completeness(self):
        """Percentage of the fields that drive recommendation quality."""
        fields = [
            self.degree,
            self.class_of_degree,
            self.institution,
            self.field_of_study,
            self.skills,
            self.preferred_location,
            self.preferred_job_type,
        ]
        filled = sum(1 for f in fields if f)
        return int(filled / len(fields) * 100)


class EmployerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employer_profile")
    company_name = models.CharField(max_length=150)
    industry = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_approved = models.BooleanField(default=True)

    def __str__(self):
        return self.company_name

    PALETTE = ["#1f4e79", "#2d6a4f", "#7b341e", "#4a3f8f", "#0a66c2",
               "#8a5a00", "#41545e", "#6b2d5c"]

    def initials(self):
        words = [w for w in self.company_name.split() if w]
        return "".join(w[0] for w in words[:2]).upper() or "?"

    def logo_colour(self):
        """Stable flat colour per company. Generated initials read as a real
        logo placeholder; a broken image icon reads as an unfinished project."""
        return self.PALETTE[sum(ord(c) for c in self.company_name) % len(self.PALETTE)]
