"""Tests for the vendored English wordlist and its deterministic builder.

The wordlist is the hyphenation resolver's last-resort evidence tier, so two
properties matter and are pinned here. First, the built list must be exactly
reproducible from the vendored components, so a hand edit to the committed list
is caught the same way a hand-edited ingestion output would be. Second, the list
must resolve the real residue cases correctly: the ordinary inflected American
words present, and the compound and proper-name joined forms absent, because a
false positive there would delete a real hyphen and reintroduce the original
"thirdparty" defect.
"""

from __future__ import annotations

from src.ingest.wordlist import (
    BUILT_LIST,
    LEVELS,
    VENDOR_DIR,
    build_bytes,
    component_paths,
    load_wordlist,
)

# Ordinary English words that occur exactly once in the corpus, at a line break,
# with no attestation in either direction. The joined form is a real word, so the
# resolver must find it and delete the hyphen. American spellings and inflected
# forms are the coverage that a lemma-only list such as web2 fails.
RESIDUE_PRESENT = (
    "cooperation",
    "emphasize",
    "managers",
    "nonetheless",
    "quantities",
    "developments",
    "illustrated",
    "formalized",
)

# Real hyphenated compounds and proper names whose joined form is NOT a word. The
# resolver must NOT find these, so the hyphen is kept. The first three are the
# corpus's actual at-risk forms, the rest the broader "thirdparty" defect class.
RESIDUE_ABSENT = (
    "alghoneim",
    "selfassessment",
    "webcrawled",
    "costeffective",
    "highor",
    "thirdparty",
    "decisionmaking",
    "humanai",
    "privacyenhancing",
    "contextspecific",
    "realworld",
    "riskbased",
)


def test_build_is_byte_identical_to_the_committed_list():
    """Re-running the recipe must reproduce the committed bytes exactly.

    Same discipline as the byte-identical ingestion rerun: a word added or
    removed by hand in the committed list is undetectable in a diff of 135,951
    lines, but it fails this assertion.
    """
    assert build_bytes() == BUILT_LIST.read_bytes()


def test_every_entry_is_lowercase_and_stripped():
    """The resolver lowercases the probe before lookup; the list must be lowercase."""
    wordlist = load_wordlist()
    assert wordlist
    for word in wordlist:
        assert word
        assert word == word.lower()
        assert word == word.strip()


def test_covers_the_inflected_american_residue_cases():
    wordlist = load_wordlist()
    missing = [word for word in RESIDUE_PRESENT if word not in wordlist]
    assert not missing, f"residue words missing from the wordlist: {missing}"


def test_excludes_compound_and_proper_name_joined_forms():
    """A false positive here would delete a real hyphen. This pins the defect class."""
    wordlist = load_wordlist()
    present = [word for word in RESIDUE_ABSENT if word in wordlist]
    assert not present, f"dangerous joined forms present in the wordlist: {present}"


def test_is_american_not_british():
    """The corpus is American; the build excludes British-only spellings by construction."""
    wordlist = load_wordlist()
    assert {"emphasize", "formalized", "organized", "behavior", "color"} <= wordlist
    assert not ({"emphasise", "formalised", "organise", "behaviour", "colour"} & wordlist)


def test_levels_stop_at_seventy_excluding_the_ukacd_tier():
    """Level 80 introduces UKACD's restrictive terms and the compound-word tier."""
    assert max(LEVELS) == 70
    assert 80 not in LEVELS and 95 not in LEVELS
    for component in VENDOR_DIR.glob("*-words.*"):
        level = int(component.suffix.lstrip("."))
        assert level <= 70, f"a level above 70 is vendored: {component.name}"


def test_component_paths_are_the_expected_sixteen_and_present():
    paths = component_paths()
    assert len(paths) == 16
    assert all(path.exists() for path in paths)
    families = {path.name.rsplit(".", 1)[0] for path in paths}
    assert families == {"english-words", "american-words"}


def test_entry_count_is_pinned():
    assert len(load_wordlist()) == 135951
