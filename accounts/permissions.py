"""Role-based access control for the three categories of user (section 3.2.3)."""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def _role_required(check, message):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("{}?next={}".format("/login/", request.path))
            if not check(request.user):
                messages.warning(request, message)
                return redirect("dashboard")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


graduate_required = _role_required(
    lambda user: user.is_graduate,
    "That page is only available to graduate accounts.",
)

employer_required = _role_required(
    lambda user: user.is_employer,
    "That page is only available to employer accounts.",
)

admin_required = _role_required(
    lambda user: user.is_administrator,
    "That page is only available to administrator accounts.",
)
