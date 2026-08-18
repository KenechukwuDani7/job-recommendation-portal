from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from accounts import views as account_views
from accounts.forms import EmailLoginForm
from jobs import views as job_views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", account_views.home, name="home"),
    path("register/", account_views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(
        template_name="accounts/login.html",
        authentication_form=EmailLoginForm,
        redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", account_views.profile, name="profile"),

    path("recommended/", job_views.recommended, name="recommended"),
    path("search/", job_views.search, name="search"),
    path("jobs/<int:pk>/", job_views.job_detail, name="job_detail"),
    path("jobs/<int:pk>/apply/", job_views.apply, name="apply"),
    path("applications/", job_views.my_applications, name="my_applications"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
