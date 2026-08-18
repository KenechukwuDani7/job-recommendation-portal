from django import forms

from .models import Job


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ["title", "description", "required_skills", "location", "job_type",
                  "experience_level", "salary_min", "salary_max", "deadline"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Junior Backend Developer"}),
            "description": forms.Textarea(attrs={
                "rows": 8,
                "placeholder": "Describe the role, the responsibilities and what you are "
                               "looking for in a candidate."}),
            "required_skills": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "e.g. Python, Django, SQL, REST APIs, Git"}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Lagos"}),
            "salary_min": forms.NumberInput(attrs={"placeholder": "150000"}),
            "salary_max": forms.NumberInput(attrs={"placeholder": "250000"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "required_skills": "Separate each skill with a comma. These are matched against "
                               "graduate profiles, so state them explicitly.",
        }

    def clean(self):
        cleaned = super().clean()
        low, high = cleaned.get("salary_min"), cleaned.get("salary_max")
        if low and high and low > high:
            raise forms.ValidationError(
                "The minimum salary cannot be greater than the maximum salary.")
        return cleaned
