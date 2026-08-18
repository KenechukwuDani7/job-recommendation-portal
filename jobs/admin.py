from django.contrib import admin

from .models import Application, Interaction, Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "employer", "location", "job_type", "experience_level",
                    "status", "date_posted")
    list_filter = ("status", "job_type", "experience_level", "location")
    search_fields = ("title", "required_skills", "employer__company_name")
    date_hierarchy = "date_posted"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("graduate", "job", "status", "date_applied")
    list_filter = ("status",)
    search_fields = ("graduate__user__full_name", "job__title")


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ("user", "job", "interaction_type", "timestamp")
    list_filter = ("interaction_type",)
