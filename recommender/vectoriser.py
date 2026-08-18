"""Minimal TF-IDF vectoriser and cosine similarity, implemented with NumPy.

The recommendation engine originally used scikit-learn. That pulls in SciPy,
and the three libraries together exceed the deployment platform's function
size limit, so the two operations the engine actually needs are implemented
here directly.

The behaviour deliberately reproduces scikit-learn's
``TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1)``
followed by ``cosine_similarity``:

  * tokens are matched with the pattern ``\\b\\w\\w+\\b`` over lowercased text
  * English stop words are removed before n-grams are formed, so a bigram is
    never built across a removed word
  * inverse document frequency is smoothed: ``idf = ln((1 + n) / (1 + df)) + 1``
  * term frequency is the raw count, and each document vector is L2 normalised

Reproducing those details matters. The evaluation figures reported for this
project were produced with scikit-learn, and an implementation that merely
resembled it would quietly change them. ``test_parity.py`` checks the two
against each other on the real corpus.
"""

import re

import numpy as np

TOKEN_PATTERN = re.compile(r"(?u)\b\w\w+\b")

# scikit-learn's English stop word list, reproduced so that tokenisation
# matches the original implementation exactly.
STOP_WORDS = frozenset([
    "a", "about", "above", "across", "after", "afterwards", "again",
    "against", "all", "almost", "alone", "along", "already", "also",
    "although", "always", "am", "among", "amongst", "amoungst", "amount",
    "an", "and", "another", "any", "anyhow", "anyone", "anything", "anyway",
    "anywhere", "are", "around", "as", "at", "back", "be", "became",
    "because", "become", "becomes", "becoming", "been", "before",
    "beforehand", "behind", "being", "below", "beside", "besides",
    "between", "beyond", "bill", "both", "bottom", "but", "by", "call",
    "can", "cannot", "cant", "co", "con", "could", "couldnt", "cry", "de",
    "describe", "detail", "do", "done", "down", "due", "during", "each",
    "eg", "eight", "either", "eleven", "else", "elsewhere", "empty",
    "enough", "etc", "even", "ever", "every", "everyone", "everything",
    "everywhere", "except", "few", "fifteen", "fifty", "fill", "find",
    "fire", "first", "five", "for", "former", "formerly", "forty", "found",
    "four", "from", "front", "full", "further", "get", "give", "go", "had",
    "has", "hasnt", "have", "he", "hence", "her", "here", "hereafter",
    "hereby", "herein", "hereupon", "hers", "herself", "him", "himself",
    "his", "how", "however", "hundred", "i", "ie", "if", "in", "inc",
    "indeed", "interest", "into", "is", "it", "its", "itself", "keep",
    "last", "latter", "latterly", "least", "less", "ltd", "made", "many",
    "may", "me", "meanwhile", "might", "mill", "mine", "more", "moreover",
    "most", "mostly", "move", "much", "must", "my", "myself", "name",
    "namely", "neither", "never", "nevertheless", "next", "nine", "no",
    "nobody", "none", "noone", "nor", "not", "nothing", "now", "nowhere",
    "of", "off", "often", "on", "once", "one", "only", "onto", "or",
    "other", "others", "otherwise", "our", "ours", "ourselves", "out",
    "over", "own", "part", "per", "perhaps", "please", "put", "rather",
    "re", "same", "see", "seem", "seemed", "seeming", "seems", "serious",
    "several", "she", "should", "show", "side", "since", "sincere", "six",
    "sixty", "so", "some", "somehow", "someone", "something", "sometime",
    "sometimes", "somewhere", "still", "such", "system", "take", "ten",
    "than", "that", "the", "their", "them", "themselves", "then", "thence",
    "there", "thereafter", "thereby", "therefore", "therein", "thereupon",
    "these", "they", "thick", "thin", "third", "this", "those", "though",
    "three", "through", "throughout", "thru", "thus", "to", "together",
    "too", "top", "toward", "towards", "twelve", "twenty", "two", "un",
    "under", "until", "up", "upon", "us", "very", "via", "was", "we",
    "well", "were", "what", "whatever", "when", "whence", "whenever",
    "where", "whereafter", "whereas", "whereby", "wherein", "whereupon",
    "wherever", "whether", "which", "while", "whither", "who", "whoever",
    "whole", "whom", "whose", "why", "will", "with", "within", "without",
    "would", "yet", "you", "your", "yours", "yourself", "yourselves",
])


def _analyse(document):
    """Lowercase, tokenise, drop stop words, then append bigrams."""
    tokens = [t for t in TOKEN_PATTERN.findall(document.lower())
              if t not in STOP_WORDS]
    bigrams = [tokens[i] + " " + tokens[i + 1] for i in range(len(tokens) - 1)]
    return tokens + bigrams


class TfidfVectorizer:
    """The subset of scikit-learn's vectoriser that this project uses."""

    def __init__(self, **ignored):
        # Keyword arguments are accepted and ignored so the call sites read
        # exactly as they did with scikit-learn.
        self.vocabulary_ = {}
        self.idf_ = None

    def fit_transform(self, documents):
        analysed = [_analyse(d) for d in documents]

        vocabulary = {}
        for terms in analysed:
            for term in terms:
                if term not in vocabulary:
                    vocabulary[term] = len(vocabulary)
        self.vocabulary_ = vocabulary

        n_documents = len(analysed)
        counts = np.zeros((n_documents, len(vocabulary)), dtype=np.float64)
        for row, terms in enumerate(analysed):
            for term in terms:
                counts[row, vocabulary[term]] += 1.0

        document_frequency = (counts > 0).sum(axis=0)
        self.idf_ = np.log((1.0 + n_documents) / (1.0 + document_frequency)) + 1.0

        weighted = counts * self.idf_
        norms = np.linalg.norm(weighted, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return weighted / norms


def cosine_similarity(a, b=None):
    """Cosine similarity between every row of ``a`` and every row of ``b``.

    Called with one argument it compares ``a`` against itself, matching
    scikit-learn, which the item-based collaborative filtering relies on.
    """
    if b is None:
        b = a
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if b.ndim == 1:
        b = b.reshape(1, -1)

    a_norm = np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = np.linalg.norm(b, axis=1, keepdims=True)
    a_norm[a_norm == 0.0] = 1.0
    b_norm[b_norm == 0.0] = 1.0

    return (a / a_norm) @ (b / b_norm).T
