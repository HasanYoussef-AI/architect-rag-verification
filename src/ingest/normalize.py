"""Text normalisation for ingestion.

Deliberately minimal. Normalisation changes the text that every downstream
number is computed over, so this module does only what is necessary to make
structural matching and chunking work, and nothing that would alter what the
document actually says.

What it does:
  - replaces the non-breaking space U+00A0 with an ordinary space, because
    EUR-Lex writes structural titles as "Article" + U+00A0 + "6", so a parser
    matching "Article 6" with a plain space silently finds nothing;
  - collapses runs of whitespace inside a block to a single space;
  - strips leading and trailing whitespace from each block.

What it deliberately does not do: no Unicode compatibility normalisation, no
quote or dash folding, no case folding, no spelling or hyphenation repair. The
typographic characters the Official Journal uses are preserved exactly.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from src.ingest.pdf_extract import SOFT_HYPHEN_BREAK

NBSP = " "
# Other fixed-width spaces that appear in official typesetting. Mapped to an
# ordinary space for the same reason as NBSP: they break structural matching.
_SPACE_LIKE = {
    NBSP: " ",
    " ": " ",  # figure space
    " ": " ",  # thin space
    " ": " ",  # narrow no-break space
}

_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_spaces(text: str) -> str:
    """Map space-like characters to U+0020 without touching anything else."""
    for source, target in _SPACE_LIKE.items():
        text = text.replace(source, target)
    return text


def normalize_block(text: str) -> str:
    """Normalise one block of text: space-like mapping, whitespace collapse, strip."""
    return _WHITESPACE_RUN.sub(" ", normalize_spaces(text)).strip()


# ---------------------------------------------------------------------------
# Comparison-time normalisation.
#
# STORED TEXT IS NEVER ALTERED BY THIS. The mappings below apply identically to
# BOTH sides of every grounding comparison and to BM25 tokenisation, at
# comparison time only. Models emit ASCII, so a model answer carries a straight
# apostrophe and a plain hyphen where a chunk carries the typographic U+2019 and
# U+2013. Without folding them at comparison time a genuinely supported claim
# fails to string-match its source chunk and is flagged unsupported, which
# corrupts the headline metric in the direction that makes the layer look worse,
# and a BM25 query typed with an ASCII apostrophe misses passages carrying the
# typographic one. Editing the stored text instead would be editing the source,
# which this repository does not do.
# ---------------------------------------------------------------------------

COMPARISON_NORMALISATION_MAP = {
    "‘": "'",  # left single quotation mark
    "’": "'",  # right single quotation mark, the typographic apostrophe
    "“": '"',  # left double quotation mark
    "”": '"',  # right double quotation mark
    "–": "-",  # en dash
    "—": "-",  # em dash
    " ": " ",  # non-breaking space
}

COMPARISON_TIME_NORMALISATION_NOTE = (
    "Stored text is never altered. At comparison time ONLY, on BOTH sides "
    "identically and for BM25 tokenisation, apply these mappings: curly single "
    "quotes and the typographic apostrophe U+2018 and U+2019 to ASCII apostrophe, "
    "curly double quotes U+201C and U+201D to ASCII double quote, en dash U+2013 "
    "and em dash U+2014 to ASCII hyphen, non-breaking space U+00A0 to space, and "
    "collapse all whitespace including newlines. Models emit ASCII, so without "
    "this a model answer fails to string-match a chunk carrying the typographic "
    "characters, flagging genuinely supported claims as unsupported and corrupting "
    "the headline metric, and a BM25 query with an ASCII apostrophe misses passages "
    "carrying the typographic one. See src.ingest.normalize.normalise_for_comparison."
)


def normalise_for_comparison(text: str) -> str:
    """Fold typographic characters to ASCII and collapse whitespace, for matching.

    For use at comparison time on both sides of grounding and for BM25, never on
    stored text. See COMPARISON_TIME_NORMALISATION_NOTE for why.
    """
    for source, target in COMPARISON_NORMALISATION_MAP.items():
        text = text.replace(source, target)
    return _WHITESPACE_RUN.sub(" ", text).strip()


def nonascii_inventory(text: str) -> list[dict]:
    """Every non-ASCII codepoint in text, with count and handling classification.

    Handling is one of: normalise_at_comparison_time for the quote, dash and
    space characters folded by normalise_for_comparison; resolved_at_ingestion
    for the U+FFFE line-break hyphen; leave_alone_genuine_content for everything
    else, which is deliberately excluded from any normalisation because it is
    genuine content, accented letters in author names, the parrot in a cited
    title, the registered sign, the bullet and the almost-equal sign.
    """
    counts = Counter(ch for ch in text if ord(ch) > 127)
    inventory: list[dict] = []
    for ch in sorted(counts, key=ord):
        try:
            name = unicodedata.name(ch)
        except ValueError:
            name = "<unnamed noncharacter>"
        if ch in COMPARISON_NORMALISATION_MAP:
            handling = "normalise_at_comparison_time"
        elif ch == SOFT_HYPHEN_BREAK:
            handling = "resolved_at_ingestion_by_hyphenation_resolve"
        else:
            handling = "leave_alone_genuine_content"
        inventory.append(
            {
                "codepoint": f"U+{ord(ch):04X}",
                "name": name,
                "count": counts[ch],
                "handling": handling,
            }
        )
    return inventory
