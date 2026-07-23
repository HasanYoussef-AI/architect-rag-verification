"""Deterministic English wordlist, the hyphenation resolver's last-resort tier.

The U+FFFE line-break hyphen resolver (`src/ingest/hyphenation.py`) decides, per
occurrence, whether a hyphen at a line break was a typesetting artifact inside
one word, "cooper-ation", or a real hyphen in a compound, "third-party". Its
strongest evidence is corpus attestation: the same word pair appearing elsewhere
in the corpus, hyphenated or joined, settles the question. A small residue has
no attestation in either direction, because the word pair occurs exactly once in
the whole corpus and that once is at the line break. For that residue this
wordlist is evidence source four, consulted only where the earlier sources are
silent: if the joined form is a real English word the hyphen was typesetting and
is deleted, and if it is not the hyphen was real and is kept.

Why a committed, checksummed wordlist rather than a judgment about English. The
whole point is that the decision stays a mechanical lookup in a reproducible
artifact anyone can audit, not a recollection of whether a string is a word.
Looking up "cooperation" in a specific committed file is deterministic; deciding
it "looks like a word" is not. That is why this does not violate the
no-reconstruction rule the way morphological judgment would.

Source and license. This is SCOWL (Spell Checker Oriented Word Lists), revision
2020.12.07, by Kevin Atkinson. The lookup list is BUILT from the vendored,
as-served component files under `vendor/scowl/`, at SCOWL size levels 10 through
70, using only the dialect-neutral `english-words` and American `american-words`
families. British, variant, proper-name and abbreviation files are excluded, so
proper names and non-American spellings cannot enter and the false-positive
direction is controlled by construction. Level 80 is excluded deliberately: it
is the first level to include the UK Advanced Cryptics Dictionary, whose terms
are the only component in SCOWL that is not public domain or permissively
licensed, and the first level at which the false-positive surface begins to grow
(256,772 compound words enter at 95). Every component used here is public domain
or permissive; the full notices are in `vendor/scowl/Copyright`, vendored
verbatim to satisfy them, and the provenance is recorded in `corpus/SOURCES.md`.

The build recipe, and nothing more: concatenate the components, lowercase,
deduplicate, sort by Unicode code point, one word per line, trailing newline,
UTF-8. The built list is a DERIVED artifact, not as-served bytes, so its
reproducibility rests on this recipe rather than on a download. A test re-runs
the recipe and asserts byte-identity with the committed output, and the vendor
verifier pins both the components and the built list by checksum.

Known limitation, recorded rather than discovered: where a genuinely hyphenated
compound occurs exactly once, at a line break, and its joined form happens to be
a dictionary word, this tier will wrongly delete the hyphen. Corpus attestation
catches that whenever the compound appears anywhere else in the corpus, so the
exposure is narrow, but it is real and is stated.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VENDOR_DIR = REPO_ROOT / "vendor" / "scowl"

# SCOWL size levels 10 through 70. See the module docstring and
# vendor/scowl/Copyright for why 80 and above are excluded.
LEVELS = (10, 20, 35, 40, 50, 55, 60, 70)

# The dialect-neutral list plus the American-specific spellings, nothing else.
FAMILIES = ("english-words", "american-words")

# The single derived lookup list. Latin-1 in, UTF-8 out.
BUILT_LIST = VENDOR_DIR / "en-american.10-70.lower.txt"

# The SCOWL component files are ISO-8859-1 as shipped.
_COMPONENT_ENCODING = "iso-8859-1"


def component_paths() -> list[Path]:
    """The vendored as-served component files, in a fixed deterministic order."""
    return [VENDOR_DIR / f"{family}.{level}" for level in LEVELS for family in FAMILIES]


def build_bytes() -> bytes:
    """Build the lookup list from the vendored components.

    Concatenate, lowercase, deduplicate, sort by Unicode code point, one word per
    line, trailing newline, UTF-8. Sorting is done in Python rather than with the
    shell `sort` so the order is locale-independent and reproducible anywhere.
    Order of reading does not affect the result because the words are collected
    into a set and sorted; the fixed order exists only so the recipe is explicit.
    """
    words: set[str] = set()
    for path in component_paths():
        text = path.read_bytes().decode(_COMPONENT_ENCODING)
        for line in text.split("\n"):
            if line == "":
                continue
            if line != line.strip():
                raise ValueError(
                    f"unexpected surrounding whitespace in {path.name}: {line!r}"
                )
            words.add(line.lower())
    return ("\n".join(sorted(words)) + "\n").encode("utf-8")


def write_built_list() -> Path:
    """(Re)build the lookup list and write it to its committed location."""
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    BUILT_LIST.write_bytes(build_bytes())
    return BUILT_LIST


@lru_cache(maxsize=1)
def load_wordlist() -> frozenset[str]:
    """The built list as a frozenset of lowercase words, loaded once.

    Lookups must lowercase the probe first: the list is entirely lowercase, so a
    corpus form such as "Nonetheless" resolves via "nonetheless" while a proper
    name such as "AlGhoneim" resolves via "alghoneim", which is absent.
    """
    lines = BUILT_LIST.read_text(encoding="utf-8").split("\n")
    return frozenset(line for line in lines if line)


def main() -> int:
    path = write_built_list()
    count = len(load_wordlist())
    print(
        f"wrote {path.relative_to(REPO_ROOT)}: {count} entries, {path.stat().st_size} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
