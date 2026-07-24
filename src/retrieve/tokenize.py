"""Lexical tokenisation for BM25, shared by indexing and querying.

One normalisation path for both sides so the index and a query cannot diverge:
apply normalise_for_comparison (curly quotes and apostrophe to ASCII, en and em
dash to hyphen, non-breaking space to space, whitespace collapsed), lowercase,
then match primary tokens.

Primary tokens keep the corpus's high-value anchors whole rather than shredding
them: "GOVERN 1.1" -> ["govern", "1.1"], "GV-1.1-001" -> ["gv-1.1-001"],
"art_6" -> ["art_6"], "third-party" -> ["third-party"]. Naive splitting on
non-alphanumerics would produce ["gv", "1", "1", "001"] and lose the identifier.

INDEX-SIDE EXPANSION, query side never. At index time each primary token that
carries a hyphen or underscore also emits its parts, so "third-party" indexes as
["third-party", "third", "party"] and a query "third party" reaches it, while a
query "third-party" reaches it through the whole token. Queries emit primary
tokens only. Expansion is an index-side synonym mechanism, not additional text,
so DOCUMENT LENGTH counts primary tokens only and the expansion parts contribute
term frequency and postings but are never charged against length. Dotted numeric
groups like "1.1" are not split, so "gv-1.1-001" expands to ["gv", "1.1", "001"].

No stopword removal: IDF already down-weights common terms, so a stopword list
buys nothing and would add an external artifact to license and vendor. No
stemming: it would mean vendoring a stemmer, another version surface and source
of nondeterminism, for morphology the dense arm already covers.
"""

from __future__ import annotations

import re

from src.ingest.normalize import normalise_for_comparison

# A primary token: alphanumeric runs joined by internal '.', '_' or '-'.
_PRIMARY = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")
# Expansion splits on hyphen and underscore only, keeping dotted groups intact.
_SPLIT = re.compile(r"[-_]")


def primary_tokens(text: str) -> list[str]:
    """The primary tokens of text, identifiers kept whole. Used for queries and dl."""
    return _PRIMARY.findall(normalise_for_comparison(text).lower())


def tokenize_query(text: str) -> list[str]:
    """Query tokenisation: primary tokens only, no expansion."""
    return primary_tokens(text)


def tokenize_document(text: str) -> list[str]:
    """Index tokenisation: primary tokens plus hyphen/underscore-separated parts."""
    tokens = primary_tokens(text)
    expanded = list(tokens)
    for token in tokens:
        if "-" in token or "_" in token:
            expanded.extend(part for part in _SPLIT.split(token) if part)
    return expanded


def document_length(text: str) -> int:
    """BM25 document length: primary-token count only, expansion parts excluded."""
    return len(primary_tokens(text))
