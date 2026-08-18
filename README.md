# Smart Job Recommendation Portal for Graduates

A web-based job portal that builds a structured profile for each graduate and
ranks vacancies by how well they fit that profile, instead of returning an
unranked list of keyword matches.

Final-year undergraduate project.

## Approach

The recommendation engine is a hybrid of two techniques:

- **Content-based filtering.** Each graduate profile and each vacancy is
  reduced to a text document. The corpus is converted to weighted vectors with
  TF-IDF, and cosine similarity between the profile vector and every vacancy
  vector produces a content score.
- **Item-based collaborative filtering.** Views, saves and applications are
  logged, and vacancies engaged with by graduates whose behaviour resembles the
  current user's score higher.

The two are combined as `0.7 * content + 0.3 * collaborative`. A graduate with
no interaction history has no collaborative signal, so the engine falls back to
the content score alone, which is how the cold-start problem is handled.

Both components are placed on a common scale before they are combined. Raw
cosine similarity is small even for an excellent match, while the collaborative
score is min-max normalised; combining them directly lets the collaborative
term lift vacancies that share nothing with the profile.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | HTML5, CSS3, JavaScript, Django template engine |
| Backend | Python, Django |
| Recommender | scikit-learn (TF-IDF, cosine similarity), NumPy |
| Database | SQLite in development, MySQL for deployment |
| Version control | Git, GitHub |

## Running locally

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py seed
.venv/Scripts/python.exe manage.py runserver
```

The site is then available at http://127.0.0.1:8000/.

`manage.py seed` populates the database with employers, a vacancy corpus,
graduate profiles and interaction records. It uses a fixed random seed so that
runs are reproducible. All seeded accounts use the password `testpass123`, and
the command prints one login for each role when it finishes.

## Roles

| Role | Screens |
| --- | --- |
| Graduate | Profile builder, ranked recommendation feed, keyword search, job detail, apply, application tracker |
| Employer | Company profile, post and manage vacancies, applicants ranked against the required skills, application status |
| Administrator | Platform summary, approve or suspend employers, withdraw or restore vacancies, plus the Django admin site |

Suspending an employer or withdrawing a vacancy removes it from the listings
without deleting records, so applications are preserved and the action can be
reversed.

## Evaluating the recommender

```bash
.venv/Scripts/python.exe manage.py seed --flush --jobs 150
.venv/Scripts/python.exe manage.py evaluate --markdown
```

This compares the recommendation engine with conventional keyword search on the
same corpus, reporting precision under both conventions and recall. Relevance is
judged by the vacancy's occupational category, which is assigned when a vacancy
is created and is independent of anything the engine computes.

The default corpus of 20 vacancies is sized for demonstration; the evaluation
needs the larger corpus to be meaningful. Reseed without `--jobs` afterwards to
return to the smaller one.

## Deployment

The repository is configured for Vercel. Import it as a new project, leave the
framework preset as "Other" so `vercel.json` drives the build, and set:

| Variable | Value |
| --- | --- |
| `DJANGO_SECRET_KEY` | a long random string |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `.vercel.app` |

The recommendation engine uses a NumPy implementation of TF-IDF and cosine
similarity rather than scikit-learn, because scikit-learn and SciPy together
exceed the platform's function size limit. `recommender/test_parity.py` checks
the two implementations against each other on the real corpus; they agree to
floating point precision, so the reported evaluation figures describe either.

The platform's filesystem is read-only apart from a temporary directory, so a
pre-seeded database ships with the deployment and is copied there when an
instance starts. Anything a visitor creates lasts only until that instance is
recycled, after which the seeded data returns. Set `DATABASE_URL` to an
external database if the data needs to persist; the settings prefer it whenever
it is present.

The administrator password in the deployed database is set from
`DEMO_ADMIN_PASSWORD` at seed time and is not the one documented above, since
the repository is public and a published administrator password would let any
visitor moderate the live demonstration.

## Structure

```
accounts/      users, graduate profiles, employer profiles, authentication
jobs/          vacancies, applications, interaction logging, views
recommender/   the hybrid recommendation engine
templates/     page templates
static/        stylesheet
```

## Switching to MySQL

Replace the `DATABASES` setting in `config/settings.py` with the MySQL
configuration commented at the foot of that file, install `mysqlclient`, then
re-run `migrate` and `seed`.
