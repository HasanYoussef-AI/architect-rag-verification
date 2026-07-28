"""Carrier multiplicity on duplicated gold, re-derived and pinned against the manifest.

PREREGISTRATION.md scores Precision@10 over chunks, so a retrieval returning several
verbatim carriers of one statement raises it, and the sealed file requires each query's
carrier count to be reported alongside the figure. The rule lives there; this module
measures the population it acts on and pins the measurement.

Carriers are derived from the duplication map and the normalise-identity verbatim groups,
composed into equivalence classes, because either relation alone is incomplete. They are
deliberately not derived from ``hit_ranks`` in the development results: that field records
ranks per expected unit under the any-carrier rule and omits at least one carrier that is
present in the committed top 10, so it understates the very quantity being measured.
"""

from __future__ import annotations

import collections
import json

from src.ingest.corpus_integrity import REPO_ROOT

MANIFEST = REPO_ROOT / "data" / "retrieval" / "retrieval_manifest.json"
DUP_MAP = REPO_ROOT / "data" / "chunks" / "nist_ai_100_1.duplication_map.json"
VERBATIM = REPO_ROOT / "data" / "retrieval" / "verbatim_groups.json"
DEV_RESULTS = REPO_ROOT / "eval" / "dev_retrieval_results.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _unit_of(chunk_id: str) -> str:
    return chunk_id.split("#", 1)[0]


def carrier_classes() -> dict[str, str]:
    """Union-find over both duplication relations. Returns unit id -> class representative.

    The duplication map carries semantic restatement structure; the normalise-identity
    groups carry byte-level identity after comparison normalisation. Neither is a subset of
    the other, so a carrier set built from one alone is short.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for row in _load(DUP_MAP):
        members = [row["source_unit_id"], *[d["unit_id"] for d in row["duplicated_in"]]]
        for m in members[1:]:
            union(members[0], m)
    for group in _load(VERBATIM)["bases"]["normalised_identity"]["groups"]:
        members = [_unit_of(m) for m in group["members"]]
        for m in members[1:]:
            union(members[0], m)
    return {u: find(u) for u in parent}


def derive() -> dict:
    rows = _load(DUP_MAP)
    groups = [[r["source_unit_id"], *[d["unit_id"] for d in r["duplicated_in"]]] for r in rows]
    per_group = collections.Counter(len(set(g)) for g in groups)

    vg_groups = _load(VERBATIM)["bases"]["normalised_identity"]["groups"]
    per_vg = collections.Counter(len(g["members"]) for g in vg_groups)

    cls = carrier_classes()
    observed = {}
    for rec in _load(DEV_RESULTS)["retrieval"]:
        seen: dict[str, list] = {}
        for rank, chunk in enumerate(rec["top10"], 1):
            unit = _unit_of(chunk)
            key = cls.get(unit)
            if key is None:
                continue
            seen.setdefault(key, [])
            if unit not in [u for u, _ in seen[key]]:
                seen[key].append((unit, rank))
        best = max(seen.values(), key=len) if seen else []
        observed[rec["id"]] = {
            "max_carriers_of_one_statement_in_top10": len(best),
            "carriers": [{"unit_id": u, "rank": r} for u, r in sorted(best, key=lambda x: x[1])],
        }
    return {
        "duplication_map": {
            "groups": len(groups),
            "carriers_per_group": {str(k): per_group[k] for k in sorted(per_group)},
            "groups_with_more_than_one_carrier": sum(v for k, v in per_group.items() if k > 1),
        },
        "normalised_identity_groups": {
            "groups": len(vg_groups),
            "members_per_group": {str(k): per_vg[k] for k in sorted(per_vg)},
        },
        "observed_in_development_top10": observed,
    }


def test_manifest_records_the_derived_carrier_counts():
    recorded = _load(MANIFEST)["duplicated_gold_carrier_counts"]
    derived = derive()
    for section in ("duplication_map", "normalised_identity_groups", "observed_in_development_top10"):
        assert recorded[section] == derived[section], (
            f"{section} in the manifest does not match the artifacts it is derived from"
        )


def test_the_two_duplication_relations_are_composed_not_substituted():
    """Neither relation alone reproduces the classes, which is why both are unioned."""
    dup_only = {r["source_unit_id"] for r in _load(DUP_MAP)}
    vg_only = {
        _unit_of(m)
        for g in _load(VERBATIM)["bases"]["normalised_identity"]["groups"]
        for m in g["members"]
    }
    assert vg_only - dup_only, "verbatim groups add no unit the duplication map lacks"


def test_dev_05_carries_three_carriers_of_one_statement():
    """The observation the sealed precision property rests on. Recorded as three, because
    hit_ranks records two and a third carrier is present in the committed top 10."""
    d = derive()["observed_in_development_top10"]["dev_05"]
    assert d["max_carriers_of_one_statement_in_top10"] == 3
    assert [c["rank"] for c in d["carriers"]] == [1, 2, 3]


def test_hit_ranks_understates_the_carrier_count():
    """Pins the reason this measurement is not derived from hit_ranks."""
    rec = [r for r in _load(DEV_RESULTS)["retrieval"] if r["id"] == "dev_05"][0]
    recorded_ranks = sorted(r for ranks in rec["hit_ranks"].values() for r in ranks)
    assert len(recorded_ranks) < 3 + 1, "sanity: hit_ranks holds fewer entries than carriers found"
    assert derive()["observed_in_development_top10"]["dev_05"][
        "max_carriers_of_one_statement_in_top10"
    ] > len(rec["hit_ranks"]["nist_ai_600_1:sub_GOVERN_6.2"])
