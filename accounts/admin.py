from django.contrib import admin

from .models import EmployerProfile, GraduateProfile, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "role", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("email", "full_name")


@admin.register(GraduateProfile)
class GraduateProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "field_of_study", "degree", "preferred_location", "updated_at")
    list_filter = ("field_of_study", "preferred_job_type")
    search_fields = ("user__full_name", "user__email", "skills")


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ("company_name", "industry", "is_approved")
    list_filter = ("industry", "is_approved")
    search_fields = ("company_name",)
