"""Measure recommendation relevance against conventional keyword search.

This produces the figures for Table 4.6 (section 4.6.2), which is the only
part of Chapter Four that cannot be written without a working system.

Relevance judgement
    A vacancy is judged relevant to a graduate when its occupational category
    matches the graduate's field of study. The category is a label attached to
    the vacancy when it is created; it is not produced by, or derived from,
    anything the recommendation engine computes. Judging relevance with the
    same similarity score that performs the ranking would guarantee the
    recommender a perfect result and would demonstrate nothing.

    This is an automated stand-in for human relevance judgement. It is
    reproducible and free of assessor bias, but it is coarser than a human
    would be: a Data Analyst vacancy is arguably relevant to a Business
    Administration graduate, and this measure would score it as irrelevant.
    That coarseness applies equally to both methods, so the comparison remains
    fair, but the write-up should describe the measure honestly rather than
    presenting it as human judgement.

Baselines
    Two keyword baselines are measured, because a single badly chosen query
    would understate what conventional search achieves and make the comparison
    look better than it is:

      field  - the graduate searches their field of study ("Computer Science")
      skill  - the graduate searches their strongest listed skill ("Python")

    Both reproduce the behaviour of the search page: substring matching over
    title, description, skills and company, ordered by date posted.
"""

from django.core.management.base import BaseCommand
from django.db.models import Q

from accounts.models import GraduateProfile
from jobs.models import Job
from recommender.engine import recommend

K = 10


class Command(BaseCommand):
    help = "Compare recommendation relevance with keyword search relevance (Table 4.6)."

    def add_arguments(self, parser):
        parser.add_argument("--profiles", type=int, default=10,
                            help="Number of test graduate profiles to evaluate.")
        parser.add_argument("--k", type=int, default=K,
                            help="Cut-off for precision@k.")
        parser.add_argument("--markdown", action="store_true",
                            help="Emit the results table in Markdown for the write-up.")

    def handle(self, *args, **options):
        k = options["k"]
        corpus = Job.objects.filter(status="open").select_related("employer")
        total_jobs = corpus.count()

        if total_jobs < k * 3:
            self.stdout.write(self.style.WARNING(
                "Only {} vacancies in the corpus. Precision@{} drawn from so small a "
                "corpus carries little meaning; reseed with a larger one first:\n"
                "    manage.py seed --flush --jobs 150".format(total_jobs, k)))
            self.stdout.write("")

        profiles = [p for p in GraduateProfile.objects.select_related("user")
                    if p.field_of_study and p.skills][:options["profiles"]]
        if not profiles:
            self.stderr.write("No graduate profiles with a field of study and skills.")
            return

        uncategorised = corpus.filter(category="").count()
        if uncategorised:
            self.stdout.write(self.style.WARNING(
                "{} of {} vacancies have no category and will be judged irrelevant "
                "to every profile. Reseed so that every vacancy is "
                "categorised.".format(uncategorised, total_jobs)))
            self.stdout.write("")

        rows = []
        for profile in profiles:
            available = corpus.filter(category=profile.field_of_study.lower()).count()
            rec = self._precision(profile, self._recommended(profile, k), k, available)
            by_field = self._precision(
                profile, self._keyword(profile.field_of_study, k), k, available)
            by_skill = self._precision(
                profile, self._keyword(self._top_skill(profile), k), k, available)
            rows.append((profile, rec, by_field, by_skill, available))

        self._report(rows, k, total_jobs, options["markdown"])

    # --- retrieval ---------------------------------------------------------

    def _recommended(self, profile, k):
        """Top k from the hybrid engine, scoring the whole corpus."""
        return [r.job for r in recommend(profile, limit=k, min_score=0)]

    def _keyword(self, query, k):
        """Top k from conventional keyword search, as the search page performs it."""
        query = (query or "").strip()
        if not query:
            return []
        return list(Job.objects.filter(status="open").filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(required_skills__icontains=query)
            | Q(employer__company_name__icontains=query)
        ).order_by("-date_posted")[:k])

    def _top_skill(self, profile):
        skills = profile.skill_list()
        return skills[0] if skills else ""

    # --- measurement -------------------------------------------------------

    def _is_relevant(self, profile, job):
        return bool(job.category) and job.category == profile.field_of_study.lower()

    def _precision(self, profile, jobs, k, available):
        """Return both precision conventions, plus recall.

        strict    relevant / k
        retrieved relevant / number actually returned
        recall    relevant / all relevant vacancies in the corpus

        The two precision conventions differ only when a method returns fewer
        than k results, which keyword search frequently does. Under the strict
        convention a query returning three relevant results out of three
        scores 0.30; under the retrieved convention it scores 1.00. Neither is
        wrong, and reporting only the one that favours the recommender would
        misrepresent the comparison.

        Recall is what separates them. A query that returns four relevant
        vacancies when twelve exist has perfect precision by the retrieved
        convention while leaving two thirds of the suitable openings unseen,
        which is precisely the failure this project exists to address.
        """
        if not jobs:
            return 0.0, 0.0, 0.0, 0, 0
        relevant = sum(1 for job in jobs if self._is_relevant(profile, job))
        recall = relevant / available if available else 0.0
        return relevant / k, relevant / len(jobs), recall, relevant, len(jobs)

    # --- reporting ---------------------------------------------------------

    def _report(self, rows, k, total_jobs, markdown):
        out = self.stdout.write

        out("")
        out("Evaluation of recommendation relevance (Table 4.6)")
        out("Corpus: {} open vacancies   Profiles: {}   Cut-off: k={}".format(
            total_jobs, len(rows), k))
        out("Relevance: vacancy category matches the graduate's field of study")
        out("")

        measures = (
            ("Precision@{} (strict: relevant / k)".format(k), 0),
            ("Precision@{} (retrieved: relevant / results returned)".format(k), 1),
            ("Recall@{} (relevant found / relevant available)".format(k), 2),
        )
        for title, idx in measures:
            out(title)
            header = "{:<6} {:<26} {:>12} {:>14} {:>14} {:>10}".format(
                "Profile", "Field of study", "Recommender",
                "Keyword field", "Keyword skill", "Available")
            out(header)
            out("-" * len(header))

            for i, (profile, rec, fld, skl, available) in enumerate(rows, 1):
                out("{:<6} {:<26} {:>12} {:>14} {:>14} {:>10}".format(
                    "P{}".format(i),
                    profile.field_of_study[:26],
                    "{:.2f}".format(rec[idx]),
                    "{:.2f}".format(fld[idx]),
                    "{:.2f}".format(skl[idx]),
                    available,
                ))

            n = len(rows)
            mean_rec = sum(r[1][idx] for r in rows) / n
            mean_fld = sum(r[2][idx] for r in rows) / n
            mean_skl = sum(r[3][idx] for r in rows) / n

            out("-" * len(header))
            out("{:<6} {:<26} {:>12} {:>14} {:>14}".format(
                "Mean", "", "{:.2f}".format(mean_rec),
                "{:.2f}".format(mean_fld), "{:.2f}".format(mean_skl)))

            best = max(mean_fld, mean_skl)
            label = "field-of-study" if mean_fld >= mean_skl else "skill"
            delta = mean_rec - best
            relative = " ({:+.0f}% relative)".format(delta / best * 100) if best else ""
            out("Best baseline: {} query at {:.2f}. Recommender {:+.2f}{}".format(
                label, best, delta, relative))
            out("")

        shortfalls = sum(1 for (_, _, f, s, _a) in rows for r in (f, s) if r[4] < k)
        if shortfalls:
            out("Keyword search returned fewer than {} results for {} of the {} queries "
                "measured, which is why the two conventions differ. The Returned column "
                "shows the count for the field and skill queries.".format(
                    k, shortfalls, len(rows) * 2))
            out("")

        out("Limitation to state in the write-up: the corpus is generated, and the "
            "skills held by seeded graduates were authored alongside the skills "
            "required by seeded vacancies. The association the recommender exploits "
            "is therefore stronger here than it would be against vacancies written "
            "independently by real employers, so these figures should be read as an "
            "upper bound rather than as field performance.")

        if markdown:
            out("")
            out("--- Markdown for the write-up ---")
            out("")
            out("| Profile | Field of Study | Precision@{k} (Recommender) | "
                "Precision@{k} (Keyword Search) |".format(k=k))
            out("| --- | --- | --- | --- |")
            n = len(rows)
            m_rec = sum(r[1][0] for r in rows) / n
            m_base = max(sum(r[2][0] for r in rows) / n, sum(r[3][0] for r in rows) / n)
            for i, (profile, rec, fld, skl, _a) in enumerate(rows, 1):
                out("| P{} | {} | {:.2f} | {:.2f} |".format(
                    i, profile.field_of_study, rec[0], max(fld[0], skl[0])))
            out("| **Mean** | | **{:.2f}** | **{:.2f}** |".format(m_rec, m_base))
