from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import GraduateProfileForm, GraduateRegistrationForm
from .models import GraduateProfile


def home(request):
    if request.user.is_authenticated and request.user.is_graduate:
        return redirect("recommended")
    from jobs.models import Job
    return render(request, "home.html", {
        "job_count": Job.objects.filter(status="open").count(),
    })


def register(request):
    if request.user.is_authenticated:
        return redirect("recommended")
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


@login_required
def profile(request):
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
