from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import EmployerProfile, GraduateProfile
from accounts.permissions import employer_required, graduate_required
from recommender.engine import recommend, score_candidates

from .forms import JobForm
from .models import Application, Interaction, Job


def _filtered_jobs(request):
    """Vacancies narrowed by the sidebar filters, shared by both listing views."""
    jobs = Job.objects.filter(status="open").select_related("employer")
    location = request.GET.get("location", "")
    job_type = request.GET.get("job_type", "")
    experience = request.GET.get("experience", "")
    if location:
        jobs = jobs.filter(location=location)
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    if experience:
        jobs = jobs.filter(experience_level=experience)
    return jobs


def _filter_options(request):
    """Filter values with their counts, in the manner of a real job board."""
    base = Job.objects.filter(status="open")
    locations = (base.values_list("location", flat=True))
    counts = {}
    for loc in locations:
        counts[loc] = counts.get(loc, 0) + 1
    location_options = sorted(counts.items(), key=lambda kv: -kv[1])

    type_counts = {}
    for value, label in Job.JOB_TYPE_CHOICES:
        n = base.filter(job_type=value).count()
        if n:
            type_counts[value] = (label, n)

    exp_counts = {}
    for value, label in Job.EXPERIENCE_CHOICES:
        n = base.filter(experience_level=value).count()
        if n:
            exp_counts[value] = (label, n)

    return {
        "location_options": location_options,
        "job_type_options": [(v, l, n) for v, (l, n) in type_counts.items()],
        "experience_options": [(v, l, n) for v, (l, n) in exp_counts.items()],
        "active_location": request.GET.get("location", ""),
        "active_job_type": request.GET.get("job_type", ""),
        "active_experience": request.GET.get("experience", ""),
    }


@graduate_required
def recommended(request):
    """The personalised, relevance-ranked feed (section 4.3.5)."""
    profile, _ = GraduateProfile.objects.get_or_create(user=request.user)

    if profile.completeness() == 0:
        messages.info(request, "Add your field of study and skills to start receiving recommendations.")
        return redirect("profile")

    results = recommend(profile, queryset=_filtered_jobs(request))
    paginator = Paginator(results, 10)
    page = paginator.get_page(request.GET.get("page"))

    applied_ids = set(
        Application.objects.filter(graduate=profile).values_list("job_id", flat=True)
    )

    context = {
        "page_obj": page,
        "total": len(results),
        "strong": sum(1 for r in results if r.is_strong),
        "profile": profile,
        "applied_ids": applied_ids,
        "querystring": _querystring(request),
    }
    context.update(_filter_options(request))
    return render(request, "jobs/recommended.html", context)


@login_required
def search(request):
    """Conventional keyword search (section 4.3.6).

    Deliberately unranked and score-free: this reproduces the behaviour of
    existing portals and is the baseline the recommender is measured against
    in section 4.6.2.
    """
    query = request.GET.get("q", "").strip()
    jobs = _filtered_jobs(request)
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(required_skills__icontains=query)
            | Q(employer__company_name__icontains=query)
        )
    jobs = jobs.order_by("-date_posted")

    paginator = Paginator(jobs, 10)
    page = paginator.get_page(request.GET.get("page"))

    profile = GraduateProfile.objects.filter(user=request.user).first()
    applied_ids = set()
    if profile:
        applied_ids = set(
            Application.objects.filter(graduate=profile).values_list("job_id", flat=True)
        )

    context = {
        "page_obj": page,
        "total": jobs.count(),
        "query": query,
        "applied_ids": applied_ids,
        "querystring": _querystring(request),
    }
    context.update(_filter_options(request))
    return render(request, "jobs/search.html", context)


@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related("employer"), pk=pk)
    profile = GraduateProfile.objects.filter(user=request.user).first()

    # Every graduate view is logged; without this the collaborative component
    # starves. Employer views are excluded: an employer browsing their own
    # postings is not a signal about what graduates find relevant.
    if request.user.is_graduate:
        Interaction.objects.create(user=request.user, job=job,
                                   interaction_type=Interaction.VIEW)

    matched, percentage = [], None
    if profile and profile.completeness():
        scored = recommend(profile, queryset=Job.objects.filter(pk=job.pk))
        if scored:
            matched = scored[0].matched_skills
            percentage = scored[0].percentage

    has_applied = bool(profile) and Application.objects.filter(job=job, graduate=profile).exists()

    return render(request, "jobs/job_detail.html", {
        "job": job,
        "matched_skills": matched,
        "percentage": percentage,
        "has_applied": has_applied,
    })


@graduate_required
def apply(request, pk):
    if request.method != "POST":
        return redirect("job_detail", pk=pk)

    job = get_object_or_404(Job, pk=pk)
    profile, _ = GraduateProfile.objects.get_or_create(user=request.user)

    if profile.completeness() < 40:
        messages.warning(request, "Complete your profile before applying so employers can assess you.")
        return redirect("profile")

    application, created = Application.objects.get_or_create(job=job, graduate=profile)
    if created:
        Interaction.objects.create(user=request.user, job=job,
                                   interaction_type=Interaction.APPLY)
        messages.success(request, "Application submitted to {}.".format(job.employer.company_name))
    else:
        messages.info(request, "You have already applied for this vacancy.")
    return redirect("job_detail", pk=pk)


@graduate_required
def my_applications(request):
    profile, _ = GraduateProfile.objects.get_or_create(user=request.user)
    applications = (Application.objects
                    .filter(graduate=profile)
                    .select_related("job", "job__employer"))
    return render(request, "jobs/my_applications.html", {"applications": applications})


# --- Employer role ----------------------------------------------------------


def _company(request):
    company, _ = EmployerProfile.objects.get_or_create(
        user=request.user, defaults={"company_name": request.user.full_name})
    return company


@employer_required
def employer_dashboard(request):
    """Overview of the company's vacancies and the applications received."""
    company = _company(request)
    jobs = (Job.objects
            .filter(employer=company)
            .annotate(application_count=Count("applications"))
            .order_by("-date_posted"))

    return render(request, "jobs/employer_dashboard.html", {
        "company": company,
        "jobs": jobs,
        "open_count": jobs.filter(status="open").count(),
        "total_applications": Application.objects.filter(job__employer=company).count(),
    })


@employer_required
def job_create(request):
    company = _company(request)
    if request.method == "POST":
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = company
            job.save()
            messages.success(request, "Vacancy posted. It is now visible to graduates.")
            return redirect("employer_dashboard")
    else:
        form = JobForm()
    return render(request, "jobs/job_form.html", {"form": form, "job": None})


@employer_required
def job_edit(request, pk):
    company = _company(request)
    job = get_object_or_404(Job, pk=pk, employer=company)
    if request.method == "POST":
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Vacancy updated.")
            return redirect("employer_dashboard")
    else:
        form = JobForm(instance=job)
    return render(request, "jobs/job_form.html", {"form": form, "job": job})


@employer_required
def job_toggle(request, pk):
    """Close a vacancy, or reopen a closed one."""
    if request.method != "POST":
        return redirect("employer_dashboard")
    job = get_object_or_404(Job, pk=pk, employer=_company(request))
    job.status = "closed" if job.status == "open" else "open"
    job.save(update_fields=["status"])
    messages.success(request, "Vacancy {}.".format(
        "closed and withdrawn from the listings" if job.status == "closed" else "reopened"))
    return redirect("employer_dashboard")


@employer_required
def job_applicants(request, pk):
    """Applicants for one vacancy, ranked by fit (section 4.3.12)."""
    job = get_object_or_404(Job, pk=pk, employer=_company(request))
    applications = (Application.objects
                    .filter(job=job)
                    .select_related("graduate", "graduate__user"))
    candidates = score_candidates(job, applications)

    return render(request, "jobs/applicants.html", {
        "job": job,
        "candidates": candidates,
        "strong": sum(1 for c in candidates if c.is_strong),
        "status_choices": Application.STATUS_CHOICES,
    })


@employer_required
def application_status(request, pk):
    if request.method != "POST":
        return redirect("employer_dashboard")
    application = get_object_or_404(
        Application.objects.select_related("job"), pk=pk, job__employer=_company(request))
    status = request.POST.get("status")
    if status in dict(Application.STATUS_CHOICES):
        application.status = status
        application.save(update_fields=["status"])
        messages.success(request, "{} marked as {}.".format(
            application.graduate.user.full_name, application.get_status_display().lower()))
    return redirect("job_applicants", pk=application.job.pk)


def _querystring(request):
    """Current filters minus the page number, for pagination links."""
    params = request.GET.copy()
    params.pop("page", None)
    encoded = params.urlencode()
    return "&" + encoded if encoded else ""
