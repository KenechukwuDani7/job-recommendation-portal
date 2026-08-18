"""Hybrid job recommendation engine (section 3.6.6).

Content-based component
    Graduate profiles and vacancies are each reduced to a text document, the
    corpus is converted to weighted vectors with TF-IDF, and the cosine
    similarity between the profile vector and every vacancy vector gives a
    content score in [0, 1].

Collaborative component
    Item-based collaborative filtering over the Interaction table: vacancies
    engaged with by graduates whose behaviour resembles the current user's
    score higher.

Hybrid
    final = w_content * content + w_collab * collaborative

    A graduate with no interaction history has no collaborative signal at all,
    so the engine falls back to the content score alone. That fallback is the
    cold-start answer discussed in section 3.6.6 and is the reason the hybrid
    is weighted towards the content component.
"""

import numpy as np
from django.conf import settings
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jobs.models import Interaction, Job

CONTENT_WEIGHT = getattr(settings, "RECOMMENDER_CONTENT_WEIGHT", 0.7)
COLLAB_WEIGHT = getattr(settings, "RECOMMENDER_COLLAB_WEIGHT", 0.3)

# Raw cosine similarity in a bag-of-words space is small even for an excellent
# match: a vacancy sharing every skill with a profile typically scores around
# 0.45, not 1.0. The two components must therefore be placed on a common scale
# before they are combined, or the collaborative term (which is min-max
# normalised, so its best item is always exactly 1.0) silently outweighs the
# content term and lifts vacancies that share nothing with the profile.
CONTENT_REFERENCE = getattr(settings, "RECOMMENDER_CONTENT_REFERENCE", 0.45)

# Below this raw cosine value a vacancy has essentially nothing in common with
# the profile. Collaborative evidence is damped rather than removed, so the
# component can still surface an adjacent role the content model would miss,
# but can no longer manufacture relevance out of nothing.
CONTENT_FLOOR = getattr(settings, "RECOMMENDER_CONTENT_FLOOR", 0.05)
COLLAB_DAMPING = getattr(settings, "RECOMMENDER_COLLAB_DAMPING", 0.25)

# A recommendation at or above this final score is presented as a strong match.
STRONG_MATCH = getattr(settings, "RECOMMENDER_STRONG_MATCH", 0.60)

# Below this the vacancy is not worth putting in front of the graduate. The
# feed is a recommendation list, not a listing of everything in the database;
# padding it with near-zero scores is what the portal is meant to avoid.
MIN_SCORE = getattr(settings, "RECOMMENDER_MIN_SCORE", 0.10)


class Recommendation:
    """One scored vacancy, ready for the template."""

    def __init__(self, job, score, content_score, collab_score, matched_skills):
        self.job = job
        self.score = score
        self.content_score = content_score
        self.collab_score = collab_score
        self.matched_skills = matched_skills

    @property
    def percentage(self):
        return int(round(self.score * 100))

    @property
    def is_cold_start(self):
        return self.collab_score == 0.0

    @property
    def is_strong(self):
        return self.score >= STRONG_MATCH


def _normalise(values):
    """Scale an array into [0, 1]; a flat array carries no information, so it
    is returned as zeros rather than being amplified into spurious signal."""
    if values.size == 0:
        return values
    top = values.max()
    if top <= 0:
        return np.zeros_like(values)
    return values / top


def _matched_skills(profile, job):
    """Skills present in both the profile and the vacancy.

    Shown in the interface so the graduate can see why a vacancy was
    recommended rather than being asked to trust an opaque score.
    """
    profile_skills = {s.lower(): s for s in profile.skill_list()}
    matched = []
    for skill in job.skill_list():
        key = skill.lower()
        if key in profile_skills:
            matched.append(skill)
        else:
            # "Django" in the profile should match "Django REST" in the vacancy.
            for p_key, p_original in profile_skills.items():
                if len(p_key) > 3 and (p_key in key or key in p_key):
                    matched.append(skill)
                    break
    return matched


def content_scores(profile, jobs):
    """TF-IDF + cosine similarity between the profile and each vacancy."""
    if not jobs:
        return np.array([])

    documents = [job.job_document() for job in jobs]
    profile_document = profile.profile_document()

    if not profile_document.strip():
        return np.zeros(len(jobs))

    vectoriser = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)
    matrix = vectoriser.fit_transform(documents + [profile_document])

    job_vectors = matrix[:-1]
    profile_vector = matrix[-1]
    return cosine_similarity(profile_vector, job_vectors).flatten()


def collaborative_scores(user, jobs):
    """Item-based collaborative filtering over logged interactions.

    Returns zeros when the user has no history, or when no other user's
    history overlaps with theirs.
    """
    zeros = np.zeros(len(jobs))
    if not jobs or user is None or not user.is_authenticated:
        return zeros

    own = list(Interaction.objects.filter(user=user).values_list("job_id", "interaction_type"))
    if not own:
        return zeros

    all_rows = list(
        Interaction.objects.exclude(user=user).values_list("user_id", "job_id", "interaction_type")
    )
    if not all_rows:
        return zeros

    users = sorted({row[0] for row in all_rows})
    job_ids = [job.id for job in jobs]
    job_index = {job_id: i for i, job_id in enumerate(job_ids)}
    user_index = {user_id: i for i, user_id in enumerate(users)}

    # Users x vacancies matrix of implicit-feedback weights.
    matrix = np.zeros((len(users), len(job_ids)))
    for user_id, job_id, kind in all_rows:
        if job_id in job_index:
            weight = Interaction.WEIGHTS.get(kind, 1.0)
            matrix[user_index[user_id], job_index[job_id]] = max(
                matrix[user_index[user_id], job_index[job_id]], weight
            )

    if not matrix.any():
        return zeros

    item_similarity = cosine_similarity(matrix.T)

    scores = np.zeros(len(job_ids))
    for job_id, kind in own:
        if job_id in job_index:
            weight = Interaction.WEIGHTS.get(kind, 1.0)
            scores += item_similarity[job_index[job_id]] * weight

    # Never recommend something the graduate has already applied to.
    for job_id, kind in own:
        if kind == Interaction.APPLY and job_id in job_index:
            scores[job_index[job_id]] = 0.0

    return _normalise(scores)


def recommend(profile, limit=None, queryset=None, min_score=None):
    """Return vacancies ranked by hybrid score, highest first.

    Vacancies scoring below ``min_score`` are dropped. Pass ``min_score=0`` to
    score the whole corpus, which the evaluation in section 4.6.2 requires.
    """
    jobs = list(queryset if queryset is not None else Job.objects.filter(status="open")
                .select_related("employer"))
    if not jobs:
        return []

    content = content_scores(profile, jobs)
    collaborative = collaborative_scores(profile.user, jobs)

    # Calibrate the content score against a fixed reference rather than against
    # the candidate set. Scaling by the best score in the set would force the
    # top vacancy to 100% even for a profile that nothing genuinely fits, which
    # would make the reported score meaningless.
    content_calibrated = np.clip(content / CONTENT_REFERENCE, 0.0, 1.0)

    if collaborative.any():
        gate = np.where(content >= CONTENT_FLOOR, 1.0, COLLAB_DAMPING)
        combined = (CONTENT_WEIGHT * content_calibrated
                    + COLLAB_WEIGHT * collaborative * gate)
    else:
        combined = content_calibrated  # cold start: content-based only

    results = [
        Recommendation(
            job=job,
            score=float(combined[i]),
            content_score=float(content[i]),
            collab_score=float(collaborative[i]),
            matched_skills=_matched_skills(profile, job),
        )
        for i, job in enumerate(jobs)
    ]
    cutoff = MIN_SCORE if min_score is None else min_score
    results = [r for r in results if r.score >= cutoff]
    results.sort(key=lambda r: r.score, reverse=True)
    return results[:limit] if limit else results
