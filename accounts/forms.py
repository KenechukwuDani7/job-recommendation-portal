from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import EmployerProfile, GraduateProfile, User


class GraduateRegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=150, widget=forms.TextInput(
        attrs={"placeholder": "e.g. Chidi Okafor"}))
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={"placeholder": "you@example.com"}))

    class Meta:
        model = User
        fields = ["full_name", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        user.full_name = self.cleaned_data["full_name"]
        user.role = User.GRADUATE
        if commit:
            user.save()
            GraduateProfile.objects.create(user=user)
        return user


class EmployerRegistrationForm(UserCreationForm):
    company_name = forms.CharField(max_length=150, widget=forms.TextInput(
        attrs={"placeholder": "e.g. Andela"}))
    industry = forms.CharField(max_length=100, required=False, widget=forms.TextInput(
        attrs={"placeholder": "e.g. Technology"}))
    full_name = forms.CharField(max_length=150, label="Contact name",
                                widget=forms.TextInput(attrs={"placeholder": "e.g. Ada Nwosu"}))
    email = forms.EmailField(widget=forms.EmailInput(
        attrs={"placeholder": "recruitment@company.com"}))

    class Meta:
        model = User
        fields = ["company_name", "industry", "full_name", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        user.full_name = self.cleaned_data["full_name"]
        user.role = User.EMPLOYER
        if commit:
            user.save()
            EmployerProfile.objects.create(
                user=user,
                company_name=self.cleaned_data["company_name"],
                industry=self.cleaned_data.get("industry", ""),
            )
        return user


class EmployerProfileForm(forms.ModelForm):
    class Meta:
        model = EmployerProfile
        fields = ["company_name", "industry", "description", "website"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "website": forms.URLInput(attrs={"placeholder": "https://"}),
        }


class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(label="Email address", widget=forms.EmailInput(
        attrs={"autofocus": True, "placeholder": "you@example.com"}))


class GraduateProfileForm(forms.ModelForm):
    class Meta:
        model = GraduateProfile
        fields = ["degree", "class_of_degree", "institution", "field_of_study",
                  "skills", "preferred_location", "preferred_job_type",
                  "years_of_experience", "cv"]
        widgets = {
            "degree": forms.TextInput(attrs={"placeholder": "e.g. BSc Computer Science"}),
            "institution": forms.TextInput(attrs={"placeholder": "e.g. University of Nigeria, Nsukka"}),
            "field_of_study": forms.TextInput(attrs={"placeholder": "e.g. Computer Science"}),
            "skills": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "e.g. Python, Django, SQL, Git, Problem Solving"}),
            "preferred_location": forms.TextInput(attrs={"placeholder": "e.g. Lagos"}),
        }
        help_texts = {
            "skills": "Separate each skill with a comma. These drive your recommendations, "
                      "so list them as they appear in job adverts.",
        }
