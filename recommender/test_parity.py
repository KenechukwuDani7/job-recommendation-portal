"""Check the NumPy vectoriser reproduces scikit-learn's output.

Run while scikit-learn is still installed:
    .venv/Scripts/python.exe recommender/test_parity.py

The project's reported evaluation figures were produced with scikit-learn. If
the replacement diverges, those figures no longer describe the running system,
so this compares the two implementations on the real corpus before the
dependency is removed.
"""

import os
import sys

import django
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from sklearn.feature_extraction.text import TfidfVectorizer as SkVectoriser  # noqa: E402
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine  # noqa: E402

from accounts.models import GraduateProfile  # noqa: E402
from jobs.models import Job  # noqa: E402
from recommender.vectoriser import TfidfVectorizer as NpVectoriser  # noqa: E402
from recommender.vectoriser import cosine_similarity as np_cosine  # noqa: E402


def compare(label, mine, theirs, tolerance=1e-9):
    delta = float(np.max(np.abs(np.asarray(mine) - np.asarray(theirs))))
    status = "MATCH" if delta <= tolerance else "DIVERGES"
    print("  {:<44} max difference {:.3e}  {}".format(label, delta, status))
    return delta <= tolerance


def main():
    jobs = list(Job.objects.all())
    profiles = list(GraduateProfile.objects.select_related("user"))
    documents = [j.job_document() for j in jobs]
    print("Corpus: {} vacancies, {} profiles".format(len(jobs), len(profiles)))
    print()

    ok = True

    # Vocabulary
    sk = SkVectoriser(stop_words="english", ngram_range=(1, 2), min_df=1)
    sk_matrix = sk.fit_transform(documents).toarray()
    np_vec = NpVectoriser()
    np_matrix = np_vec.fit_transform(documents)

    print("Vectoriser")
    sk_vocab, np_vocab = set(sk.vocabulary_), set(np_vec.vocabulary_)
    same = sk_vocab == np_vocab
    print("  {:<44} {} vs {} terms  {}".format(
        "vocabulary", len(sk_vocab), len(np_vocab), "MATCH" if same else "DIVERGES"))
    if not same:
        ok = False
        missing = list(sk_vocab - np_vocab)[:5]
        extra = list(np_vocab - sk_vocab)[:5]
        print("      only in scikit-learn:", missing)
        print("      only in numpy       :", extra)

    if same:
        # Align columns before comparing, since term ordering may differ.
        order = [np_vec.vocabulary_[t] for t in sk.get_feature_names_out()]
        ok &= compare("document vectors", np_matrix[:, order], sk_matrix)
        idf_order = [np_vec.vocabulary_[t] for t in sk.get_feature_names_out()]
        ok &= compare("inverse document frequencies",
                      np_vec.idf_[idf_order], sk.idf_)

    print()
    print("Cosine similarity")
    rng = np.random.default_rng(0)
    a = rng.random((6, 40))
    b = rng.random((9, 40))
    ok &= compare("dense matrices", np_cosine(a, b), sk_cosine(a, b))
    ok &= compare("single row against matrix", np_cosine(a[0], b), sk_cosine([a[0]], b))
    # Item-based collaborative filtering calls this with a single argument.
    ok &= compare("matrix against itself", np_cosine(a), sk_cosine(a))
    ok &= compare("transposed matrix against itself", np_cosine(b.T), sk_cosine(b.T))

    print()
    print("End-to-end profile scoring")
    worst = 0.0
    for profile in profiles[:10]:
        docs = documents + [profile.profile_document()]

        s = SkVectoriser(stop_words="english", ngram_range=(1, 2), min_df=1)
        m = s.fit_transform(docs)
        sk_scores = sk_cosine(m[-1], m[:-1]).flatten()

        n = NpVectoriser()
        m2 = n.fit_transform(docs)
        np_scores = np_cosine(m2[-1], m2[:-1]).flatten()

        worst = max(worst, float(np.max(np.abs(sk_scores - np_scores))))
    print("  {:<44} max difference {:.3e}  {}".format(
        "content scores across 10 profiles", worst,
        "MATCH" if worst <= 1e-9 else "DIVERGES"))
    ok &= worst <= 1e-9

    print()
    print("RESULT:", "identical to scikit-learn" if ok else "DIVERGENCE FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
