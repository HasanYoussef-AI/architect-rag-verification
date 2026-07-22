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
