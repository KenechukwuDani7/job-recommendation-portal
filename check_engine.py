"""Ad-hoc sanity check of the recommendation engine. Run: python check_engine.py"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from accounts.models import GraduateProfile  # noqa: E402
from recommender.engine import recommend  # noqa: E402

for email in ["chidi.okafor@example.com", "amaka.adeyemi@example.com",
              "tunde.bello@example.com", "ngozi.eze@example.com"]:
    profile = GraduateProfile.objects.get(user__email=email)
    print("=" * 80)
    print("{} | {} | {}".format(profile.user.full_name, profile.field_of_study, profile.skills))
    print("-" * 80)
    for r in recommend(profile, limit=5):
        print("  {:3d}%  {:<40} {:<13} c={:.3f} f={:.3f}".format(
            r.percentage, r.job.title[:40], r.job.location, r.content_score, r.collab_score))
        print("        matched: {}".format(", ".join(r.matched_skills) or "(none)"))
    print()
