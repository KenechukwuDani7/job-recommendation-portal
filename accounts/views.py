from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import (EmployerProfileForm, EmployerRegistrationForm,
                    GraduateProfileForm, GraduateRegistrationForm)
from .models import EmployerProfile, GraduateProfile
from .permissions import employer_required


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    from jobs.models import Job
    return render(request, "home.html", {
        "job_count": Job.objects.filter(status="open").count(),
    })


@login_required
def dashboard(request):
    """Send each user to the landing page for their role after signing in."""
    if request.user.is_administrator:
        return redirect("admin_dashboard")
    if request.user.is_employer:
        return redirect("employer_dashboard")
    return redirect("recommended")


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = GraduateRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created. Complete your profile to get recommendations.")
            return redirect("profile")
    else:
        form = GraduateRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


def register_employer(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST":
        form = EmployerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Employer account created. You can now post a vacancy.")
            return redirect("employer_dashboard")
    else:
        form = EmployerRegistrationForm()
    return render(request, "accounts/register_employer.html", {"form": form})


@login_required
def profile(request):
    if request.user.is_employer:
        return redirect("employer_profile")

    graduate_profile, _ = GraduateProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = GraduateProfileForm(request.POST, request.FILES, instance=graduate_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile saved. Your recommendations have been updated.")
            return redirect("recommended")
    else:
        form = GraduateProfileForm(instance=graduate_profile)
    return render(request, "accounts/profile.html", {
        "form": form,
        "profile": graduate_profile,
    })


@employer_required
def employer_profile(request):
    company, _ = EmployerProfile.objects.get_or_create(
        user=request.user, defaults={"company_name": request.user.full_name})
    if request.method == "POST":
        form = EmployerProfileForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, "Company profile saved.")
            return redirect("employer_dashboard")
    else:
        form = EmployerProfileForm(instance=company)
    return render(request, "accounts/employer_profile.html", {
        "form": form,
        "company": company,
    })
