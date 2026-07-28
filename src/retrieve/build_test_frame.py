"""Sealed test-set candidate frame, committed before any query text exists.

The sealed specification fixes the stratum counts and the gold rules but leaves one degree
of freedom: which specific units are drawn within a stratum. If queries were authored and
then described, that selection would be unfalsifiable. So the sampling frame is derived
mechanically from committed artifacts by this committed code and frozen before any query
text, gold, rank or result exists, the same discipline as the development pool.

This file carries no query text, no gold, no rank and no result. It carries, per stratum,
the ordered candidate list a reviewer can replay, the closure it must avoid, the offsets
that make the spacing deterministic, and the recorded finding for the one allocation rule
that was withdrawn (NIST absent from clean multi-hop).

Spacing is population-agnostic: a sorted candidate list and a target m in, m evenly-spaced
indices out, reused verbatim from eval/dev_unit_pool.json's selection_rule. What varies per
stratum is only what the candidates are and how they sort. Selection under rejection is
defined so the final set is reconstructible from the draw order plus the rejection log
alone: walk the draw order, take the first m entries not in the rejection log.
"""

from __future__ import annotations

import json

from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.unit_index import OUTPUT as UNIT_INDEX
from src.ingest.unit_index import derive as derive_index
from src.ingest.unit_index import to_bytes as index_to_bytes

DATA = REPO_ROOT / "data"
EVAL = REPO_ROOT / "eval"
OUTPUT = EVAL / "test_frame.json"
BLOCK_SUFFIXES = (".ai_transparency_resources", ".references")

# Single-hop eligible unit types per document: the mechanical form of the sealed
# specification's own Playbook exclusion criterion (atomic-factual and not a duplicate).
# 600-1 subcategory_statements are additionally filtered to their originating document.
SINGLE_HOP_TYPES = {
    "eu_ai_act": {"recital", "article", "annex"},
    "nist_ai_100_1": {"subcategory", "section", "category", "appendix"},
    "nist_ai_600_1": {"section", "appendix_section", "subcategory_statement"},
}

# Canonical (stratum, source) order. The offset a stratum-source gets is its index here.
# Committed so the deterministic claim is verifiable; changing it changes every draw.
CANONICAL_ORDER = (
    ("single_hop", "eu_ai_act"),
    ("single_hop", "nist_ai_100_1"),
    ("single_hop", "nist_ai_600_1"),
    ("clean_multi_hop", "eu_internal_xref"),
    ("action_to_parent", "action_subcategory"),
    ("near_miss", "block_clusters"),
    ("near_miss", "near_duplicate"),
)
OFFSET = {pair: i for i, pair in enumerate(CANONICAL_ORDER)}


def _sha256(path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unit_of(chunk_id: str) -> str:
    return chunk_id.split("#", 1)[0]


def compute_closure() -> tuple[set[str], dict[str, str]]:
    """The 50-unit burned closure and, per added unit, the artifact that pulled it in."""
    pool = json.loads((EVAL / "dev_unit_pool.json").read_text(encoding="utf-8"))
    closure = {u["unit_id"] for u in pool["units"]}
    origin: dict[str, str] = {}

    vg = json.loads((DATA / "retrieval" / "verbatim_groups.json").read_text(encoding="utf-8"))
    ni_groups = [[_unit_of(m) for m in g["members"]] for g in vg["bases"]["normalised_identity"]["groups"]]
    dup = json.loads((DATA / "chunks" / "nist_ai_100_1.duplication_map.json").read_text(encoding="utf-8"))
    dup_groups = [[r["source_unit_id"], *[d["unit_id"] for d in r["duplicated_in"]]] for r in dup]

    changed = True
    while changed:
        changed = False
        for members in ni_groups:
            if closure & set(members):
                for u in members:
                    if u not in closure:
                        closure.add(u)
                        origin.setdefault(u, "verbatim_groups")
                        changed = True
        for members in dup_groups:
            if closure & set(members):
                for u in members:
                    if u not in closure:
                        closure.add(u)
                        origin.setdefault(u, "duplication_map")
                        changed = True
    return closure, origin


def spaced_indices(n: int, m: int, offset: int) -> list[int]:
    """m evenly-spaced indices into a length-n list, rotated by offset. Pool's rule."""
    return [(offset + (i * n) // m) % n for i in range(m)]


def _circular_distance(a: int, b: int, n: int) -> int:
    d = (a - b) % n
    return min(d, n - d)


def draw_order(candidates: list, m: int, offset: int) -> list:
    """Total order whose first m entries are the evenly-spaced picks. The tail, from which every
    backfill is drawn (a distinct-target skip or an authoring rejection), is ordered by maximum
    minimum circular distance to every already-taken index, ties broken by the lower index, so a
    replacement comes from a representative point in the candidate space rather than off the
    sorted alphabetical head. Circular, to match the mod n in the spacing rule. Selection is the
    first m not-rejected entries, so rejections walk forward."""
    n = len(candidates)
    if m >= n:
        return list(candidates)
    picks = spaced_indices(n, m, offset % n)
    taken = set(picks)
    remaining = [i for i in range(n) if i not in taken]
    mindist = {i: min(_circular_distance(i, p, n) for p in picks) for i in remaining}
    tail: list[int] = []
    while remaining:
        best = max(remaining, key=lambda i: (mindist[i], -i))
        tail.append(best)
        remaining.remove(best)
        for i in remaining:
            d = _circular_distance(i, best, n)
            if d < mindist[i]:
                mindist[i] = d
    return [candidates[i] for i in picks] + [candidates[i] for i in tail]


def largest_remainder(sizes: list[int], total: int) -> list[int]:
    s = sum(sizes)
    quotas = [total * x / s for x in sizes]
    alloc = [int(q) for q in quotas]
    order = sorted(range(len(sizes)), key=lambda i: quotas[i] - alloc[i], reverse=True)
    for i in range(total - sum(alloc)):
        alloc[order[i]] += 1
    return alloc


def select(draw: list, m: int, distinct_key=None, rejected=(), *, taken=()) -> list:
    """The committed selection rule: forward-walk the draw order, taking the first m entries that
    are not in the rejection log and, when distinct_key is given, whose key has not already been
    taken. Rejections and key-collisions both walk forward, so the selected set stays
    reconstructible from the draw order and the rejection log alone.

    taken seeds the key set, which is how a source constrains itself against another source's
    already-selected units. A distinct_key returning None means the candidate carries no key and
    can never collide, which is how a rule keyed on a partial property leaves the rest
    unconstrained. Both are keyword-only so no positional call can bind them by accident."""
    blocked = {json.dumps(r, ensure_ascii=False) for r in rejected}
    out, seen = [], set(taken)
    for c in draw:
        if json.dumps(c, ensure_ascii=False) in blocked:
            continue
        if distinct_key is not None:
            k = distinct_key(c)
            if k is not None:
                if k in seen:
                    continue
                seen.add(k)
        out.append(c)
        if len(out) == m:
            break
    return out


def _stratum_source(
    stratum, source, candidates, m, distinct_target=False, distinct_from=None, identity_group=None
):
    off = OFFSET[(stratum, source)]
    spec = {
        "offset": off,
        "allocation": m,
        "n_candidates": len(candidates),
        "draw_order": draw_order(candidates, m, off),
    }
    if distinct_target:
        spec["select_distinct_target"] = True
    if distinct_from is not None:
        spec["select_distinct_from"] = distinct_from
    if identity_group is not None:
        spec["select_distinct_identity_group"] = identity_group
    return spec


def build_frame() -> dict:
    index = derive_index()
    units_by_doc: dict[str, list[str]] = {}
    for u in index["units"]:
        units_by_doc.setdefault(u["doc"], []).append(u["unit_id"])

    closure, origin = compute_closure()
    assert len(closure) == 50, f"closure size {len(closure)} != 50"
    assert sum(1 for u in closure if u not in origin) == 40, "dev-pool units in closure != 40"

    # single-hop eligibility: the sealed Playbook criterion in mechanical form, atomic-factual
    # and not a duplicate. A per-document unit-type allow-list handles atomic-factual; a
    # duplication-map filter handles not-a-duplicate for the one type that carries cross-document
    # restatements, 600-1 subcategory statements, which are eligible only in their originating
    # document. Both are applied mechanically, never by judgment on a specific unit.
    utype = {u["unit_id"]: u["unit_type"] for u in index["units"]}
    dup_records = json.loads(
        (DATA / "chunks" / "nist_ai_100_1.duplication_map.json").read_text(encoding="utf-8")
    )
    dup_600 = {
        d["unit_id"]
        for r in dup_records
        for d in r["duplicated_in"]
        if d["unit_id"].startswith("nist_ai_600_1:")
    }

    def sh_eligible(uid: str, doc: str) -> bool:
        t = utype[uid]
        if t not in SINGLE_HOP_TYPES[doc]:
            return False
        if doc == "nist_ai_600_1" and t == "subcategory_statement" and uid in dup_600:
            return False
        return True

    sh_sources = ("eu_ai_act", "nist_ai_100_1", "nist_ai_600_1")
    sh_pop = {
        d: sorted(u for u in units_by_doc[d] if u not in closure and sh_eligible(u, d))
        for d in sh_sources
    }
    ss600 = [
        u for u in units_by_doc["nist_ai_600_1"] if u not in closure and utype[u] == "subcategory_statement"
    ]
    dup_split = {
        "non_closure": len(ss600),
        "map_duplicated_excluded": sum(1 for u in ss600 if u in dup_600),
        "originating_eligible": sorted(u for u in ss600 if u not in dup_600),
    }
    sizes = [len(sh_pop[d]) for d in sh_sources]
    lr = largest_remainder(sizes, 18 - len(sh_sources))
    sh_alloc = {d: 1 + lr[i] for i, d in enumerate(sh_sources)}
    assert sum(sh_alloc.values()) == 18
    assert sh_alloc == {"eu_ai_act": 11, "nist_ai_100_1": 5, "nist_ai_600_1": 2}, (
        f"single-hop allocation {sh_alloc} does not reproduce the ruling's 11/5/2; "
        f"eligible populations were {dict(zip(sh_sources, sizes))}"
    )

    # clean multi-hop: EU internal cross-reference edges, both endpoints out of closure.
    eu_edges = []
    for line in (DATA / "chunks" / "eu_ai_act.xrefs.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        src = rec["unit_id"]
        if src in closure:
            continue
        for tgt in rec.get("refs_internal", []):
            if tgt not in closure:
                eu_edges.append([src, tgt])
    eu_edges = sorted(map(list, {tuple(e) for e in eu_edges}))

    # action-to-parent: action_subcategory edges (action -> parent), parent out of closure.
    # The gold is the parent statement, so a parent in the burned closure is ineligible even
    # though the action itself never is. Filter on the parent, keep the raw 212 as a sanity pin.
    raw_action = []
    for line in (DATA / "chunks" / "nist_ai_600_1.relations.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        for entry in rec.get("action_subcategory", []):
            raw_action.append((rec["unit_id"], entry["unit_id"]))
    raw_action = sorted(set(raw_action))
    assert len(raw_action) == 212, f"raw action edges {len(raw_action)} != 212"
    action_edges = [[a, p] for a, p in raw_action if p not in closure]
    action_dropped = len(raw_action) - len(action_edges)
    assert len(action_edges) >= 4, f"action-to-parent candidates after closure filter: {len(action_edges)}"

    # near-miss, source 1: surviving normalise-identical block clusters, as UNIT ids. The
    # verbatim_groups representatives are chunk-level because identity is a chunk property, which
    # is correct in that artifact; gold is unit-level per the sealed spec, so a candidate that
    # cannot be a gold identifier is the wrong object, and one unit holding two draw slots would
    # double-weight it in the spacing. Normalise each surviving representative to its unit and
    # dedup: two of the 18, references#p1 and #p2 of one unit, collapse, so this scope's 18
    # becomes 17. The 20 block-cluster total is the sealed chunk-level number and is kept.
    vg = json.loads((DATA / "retrieval" / "verbatim_groups.json").read_text(encoding="utf-8"))
    nd = json.loads((DATA / "retrieval" / "near_duplicate_exceptions.json").read_text(encoding="utf-8"))
    block_clusters, surviving_units = [], []
    for g in vg["bases"]["normalised_identity"]["groups"]:
        members = [_unit_of(m) for m in g["members"]]
        if any(any(s in u for s in BLOCK_SUFFIXES) for u in members):
            block_clusters.append(g["representative"])
            if not (closure & set(members)):
                surviving_units.append(_unit_of(g["representative"]))
    surviving_clusters = sorted(set(surviving_units))
    assert len(block_clusters) == 20, f"block clusters {len(block_clusters)} != 20"
    assert len(surviving_clusters) == 17, f"surviving block clusters {len(surviving_clusters)} != 17"

    # Sealed line 58 names the 12 hand-audited near-block-duplicate pairs as a source for the
    # three measured picks alongside the clusters, so the population is the union of both, query
    # side only. The returned side is the competitor, not the gold, and has 6 distinct values
    # across the 12, so unioning it would give one unit several draw slots.
    twelve_queries = [p["query"] for p in nd["block_near_duplicates_hand_audited"]["pairs"]]
    assert len(twelve_queries) == 12, f"hand-audited pairs {len(twelve_queries)} != 12"
    bc_union = sorted(set(surviving_clusters) | set(twelve_queries))
    assert len(bc_union) == 27, f"block-cluster union {len(bc_union)} != 27"
    bc_candidates = [u for u in bc_union if u not in closure]
    assert len(bc_candidates) == 27, f"union after closure filter {len(bc_candidates)} != 27"

    # Rule B key: the identity group's representative, matched by exact string equality between
    # the candidate and a group member. See select_distinct_identity_group.basis for why exact
    # equality rather than the unit-normalised alternative.
    identity_key: dict[str, str] = {}
    candidate_set = set(bc_candidates)
    for g in vg["bases"]["normalised_identity"]["groups"]:
        for mem in g["members"]:
            if mem in candidate_set:
                assert mem not in identity_key, f"candidate {mem} in two identity groups"
                identity_key[mem] = g["representative"]
    assert len(identity_key) == 18, f"identity keys {len(identity_key)} != 18"

    # near-miss, source 2: near-duplicate pairs whose query unit is out of closure.
    nd_pairs = []
    for cls in ("cross_document_statement_class", "block_near_duplicates_hand_audited"):
        for p in nd[cls]["pairs"]:
            if _unit_of(p["query"]) not in closure and _unit_of(p["returned"]) not in closure:
                nd_pairs.append([p["query"], p["returned"]])
    nd_pairs = sorted(map(list, {tuple(p) for p in nd_pairs}))

    # clean multi-hop selection: forward-walk with gold-target disjointness, verified here so a
    # duplicate target or a closure touch fails the build rather than reaching a reviewer.
    cm_source = _stratum_source(
        "clean_multi_hop", "eu_internal_xref", eu_edges, 12, distinct_target=True
    )
    cm_selected = select(cm_source["draw_order"], 12, distinct_key=lambda e: e[1])
    assert len(cm_selected) == 12, f"clean multi-hop selected {len(cm_selected)} != 12"
    assert len({e[1] for e in cm_selected}) == 12, "clean multi-hop selection has duplicate targets"
    assert not (closure & {u for e in cm_selected for u in e}), "clean multi-hop selection touches closure"

    # near-miss selection: block_clusters resolves first, per canonical_offset_order, then
    # near_duplicate walks with those picks seeded into its taken set. Both distinctness rules are
    # verified here so a violation fails the build rather than reaching a reviewer.
    identity_basis = (
        "The representative of the normalise-identity group in "
        "data/retrieval/verbatim_groups.json at .bases.normalised_identity whose members include "
        "the candidate, matched by exact string equality between the candidate and a member. 18 "
        "of the 27 candidates carry a key; the 9 in no group are absent from the map and never "
        "block. The population and the key are built on different matching rules: the population "
        "admits a unit through chunk-level membership normalised to its unit id, while the key "
        "requires the member string to equal the candidate string. One candidate, "
        "nist_playbook:sub_MEASURE_4.1.references, is admitted by the population and carries no "
        "key, because its two chunks belong to two different groups and a single-valued key "
        "cannot hold both. The unit-normalised alternative would give it a key and 19 of 27, and "
        "was rejected because it requires choosing between those two groups after the draw. Both "
        "definitions select the same three units on this population, so the choice could not have "
        "been fitted to an outcome. A build-time assertion re-derives this map and fails on any "
        "divergence."
    )
    nm_bc = _stratum_source(
        "near_miss",
        "block_clusters",
        bc_candidates,
        3,
        identity_group={
            "basis": identity_basis,
            "key_by_candidate": {k: identity_key[k] for k in sorted(identity_key)},
        },
    )
    nm_nd = _stratum_source(
        "near_miss", "near_duplicate", nd_pairs, 5, distinct_from="block_clusters"
    )
    nm_bc_selected = select(nm_bc["draw_order"], 3, distinct_key=lambda c: identity_key.get(c))
    nm_nd_selected = select(
        nm_nd["draw_order"], 5, distinct_key=lambda e: e[0], taken=set(nm_bc_selected)
    )
    assert len(nm_bc_selected) == 3, f"near-miss block_clusters selected {len(nm_bc_selected)} != 3"
    assert len(nm_nd_selected) == 5, f"near-miss near_duplicate selected {len(nm_nd_selected)} != 5"
    _bk = [identity_key[c] for c in nm_bc_selected if c in identity_key]
    assert len(_bk) == len(set(_bk)), "near-miss block_clusters selection shares an identity group"
    assert not (set(nm_bc_selected) & {e[0] for e in nm_nd_selected}), (
        "near-miss sources selected the same unit"
    )
    assert not (closure & set(nm_bc_selected)), "near-miss block_clusters selection touches closure"
    assert not (closure & {_unit_of(u) for e in nm_nd_selected for u in e}), (
        "near-miss near_duplicate selection touches closure"
    )

    finding = (
        "Clean multi-hop is allocated 12 EU internal cross-references and 0 NIST prose "
        "references. The one-per-source floor introduced during frame design is withdrawn for "
        "this stratum only; single-hop keeps its floor because all three of its sources have "
        "real supply. This is a withdrawal of a design-time allocation rule, not a split "
        "mandated by the sealed specification, which names eligible sources and does not "
        "mandate a split. Two causes, both measured: (1) the frameworks' NIST prose reference "
        "supply is thin and pointer-class, 13 NIST prose references against 367 EU internal "
        "edges before any closure, and the survivors are see-also and bibliography pointers, "
        "not different-content hops; (2) the development pool's one-unit-per-(document, "
        "unit_type) design burned the units these references cite from or point to. Of the 8 "
        "burned, 5 fall to size-1 NIST structural strata the pool necessarily takes whole "
        "(nist_ai_100_1:exec_summary, and the 600-1 appendix and references appendices "
        "nist_ai_600_1:app_A and app_B), and 3 fall to nist_ai_100_1:sec_2, the single section "
        "the pool drew from the size-23 (nist_ai_100_1, section) stratum, which happens to be a "
        "dense cross-referencing hub. So 8 of 10 same-document (classification internal) NIST "
        "references were burned by the closure. Cause (1) is prior and dominant; cause (2) "
        "jointly determines the final zero."
    )

    govern_1_3 = (
        "Single-hop draws nist_ai_100_1:sub_GOVERN_1.3 and action-to-parent draws its gold parent "
        "nist_ai_600_1:sub_GOVERN_1.3. These are the same GOVERN 1.3 statement: the duplication "
        "map records it as map-duplicated, it is not among the two 600-1 originating-eligible "
        "statements, so under the any-carrier gold rule one slot is satisfied by either carrier. "
        "This is the closure's defect shape, unit identity versus equivalence class, and a "
        "unit-id collision check does not see it. It is recorded, not engineered away: the same "
        "statement reached by an easy single-hop query and by a hard structural action-to-parent "
        "hop, with opposite pre-registered predictions, is a controlled pair, not a confound, and "
        "inventing a cross-stratum disjointness constraint after the frame is drawn would be the "
        "worse move. Stated here so a reviewer finds it in the frame rather than discovering it "
        "unremarked."
    )

    near_miss_overlap = (
        "Sealed line 58 names the 12 fixture near-block-duplicates twice: as a source for the "
        "three measured picks alongside the 20 normalise-identical block clusters, and inside the "
        "committed near_duplicate class from which the five authored picks are drawn. The builder "
        "resolved that overlap without recording it, iterating both sub-populations of "
        "near_duplicate_exceptions.json into the near_duplicate source while building "
        "block_clusters from verbatim_groups.json alone. The three measured were therefore drawn "
        "entirely from the normalise-identical half, where 16 of the 17 candidates were the "
        "lexicographic minimum of their own identity group and the chunk-id tie-break, not "
        "retrieval, decides the ordering among byte-identical text. Sealed line 58 states that "
        "the three reproduce the development query 11 structure, and that query's gold unit "
        "belongs to no normalise-identity group, so the structure the three were specified to "
        "reproduce was absent from the pool they were drawn from. Correcting rather than "
        "recording was decided on measurement: 8 of the 12 query-side units belong to no identity "
        "group, and 8 of 12 by the reason and genuine_preference fields, or 9 of 12 by "
        "won_by_fused, resolve by a BM25 term-density separation rather than by the tie-break, so "
        "the 12 are a different instrument and not a relabelling of the clusters. The "
        "block_clusters population became the union of the 17 surviving clusters and the 12 "
        "query-side units, 27 after 2 duplicates were removed, with 0 removed by the closure "
        "filter. The 12 entered whole; filtering them by identity-group membership, "
        "won_by_fused, reason or cosine was rejected, because selecting a population on a "
        "property measured after the draw is shaping. The near_duplicate source is unchanged and "
        "remains set-equal to the 59 surviving cross-document pairs plus the 12. The deviation "
        "was reached by inspecting the drawn units, and is independently visible by comparing "
        "sealed line 58 against the builder's population code without knowledge of which units "
        "were drawn. Residual: 1 of the 3 corrected picks has gold in no identity group, against "
        "0 of 3 before. The other 2 remain identity-group cases decided by the tie-break, which "
        "is a property of a corpus whose block clusters are predominantly identity groups. No "
        "adjustment to the offset, the spacing rule or the population was made to improve that "
        "ratio."
    )

    near_duplicate_record_10 = (
        "In data/retrieval/near_duplicate_exceptions.json, the hand-audited pair whose query is "
        "nist_playbook:sub_MAP_3.5.ai_transparency_resources and whose returned unit is "
        "nist_playbook:sub_GOVERN_1.1.ai_transparency_resources carries won_by_fused set to "
        "strict while both reason and genuine_preference record a tie resolved to the lower chunk "
        "id by the locked tie-break. Across the 12 hand-audited pairs, reason and "
        "genuine_preference agree on 12 of 12 and won_by_fused disagrees with them on 1. The "
        "inconsistency is recorded and not resolved. Nothing in the near-miss population or its "
        "draw depends on which field is authoritative, because the 12 enter the block_clusters "
        "population whole and are filtered on none of the three."
    )

    nm_population_correction = (
        "The block_clusters population is the union of the surviving normalise-identical block "
        "clusters and the query-side units of the 12 hand-audited near-block-duplicate pairs, "
        "which is what sealed line 58 names as the source for the three measured picks. It was "
        "previously the clusters alone. The 12 enter whole and are filtered on no measured "
        "property. See recorded_finding.near_miss_population_overlap_resolved_silently for the "
        "deviation, the measurements that decided the correction, and the residual it does not "
        "remove."
    )

    nm_cross_source_cascade = (
        "The five picks from near_duplicate are selected with the three already selected from "
        "block_clusters seeded into the taken set, so the two sources are not independent, and "
        "canonical_offset_order fixes block_clusters ahead of near_duplicate for that reason. An "
        "authoring rejection in block_clusters can therefore change which near_duplicate entries "
        "are selected, which is stated here because it changes what a rejection costs at "
        "authoring time. A first check reported the cascade as demonstrated on this draw; that "
        "result was withdrawn after isolation showed it had injected rejections into both sources "
        "and attributed the change to the wrong cause. Rejecting only the first block_clusters "
        "pick leaves the five unchanged, because the replacement pick is element 0 of no "
        "near_duplicate entry. The mechanism is live and does not fire on this draw."
    )

    nm_backfill_authoring_rule = (
        "Both distinctness rules apply during backfill and not only to the initial selection: the "
        "walk continues through the draw order, skipping rejected and colliding entries, until "
        "each allocation fills. A pick entering by backfill, from a distinctness skip or an "
        "authoring rejection, is judged and rejected with a recorded reason under the same "
        "standard as a spaced pick. A unit may be gold for a block_clusters pick and "
        "simultaneously the returned-side competitor of a near_duplicate pair; this is permitted, "
        "because the two picks have different gold, no identical text is involved, and their "
        "outcomes are not correlated by construction. That was ruled before the corrected draw "
        "was computed, and select_distinct_from keys on element 0 only and does not exclude the "
        "returned side. It does not fire on this draw."
    )

    return {
        "description": (
            "Sealed test-set candidate frame. Committed before any query text, gold, rank or "
            "result exists, mechanically derived from the committed artifacts by "
            "src/retrieve/build_test_frame.py. It fixes the within-stratum selection the sealed "
            "specification left open, so a reviewer can replay it rather than trust it."
        ),
        "universe": {
            "unit_index": str(UNIT_INDEX.relative_to(REPO_ROOT)),
            "sha256": _sha256(UNIT_INDEX),
            "n_units": index["n_units"],
        },
        "closure": {
            "n": len(closure),
            "pool_units": 40,
            "expansion_units": 10,
            "units": [
                {"unit_id": u, "pulled_by": origin.get(u, "dev_pool")} for u in sorted(closure)
            ],
            "pool_reconciliation": (
                "The sealed specification promises that the test-set builder will assert no gold "
                "unit is drawn from the reserved 40-unit development pool. This frame filters "
                "against a 50-unit closure: those 40 units plus the 10 units that carry a "
                "statement verbatim-identical to a pool unit. Because a gold slot is satisfied by "
                "any carrying unit, a slot naming a non-pool carrier of a pool statement would "
                "either admit the pool unit into gold or score a retrieval hit on identical text "
                "as a miss. The closure is a strict superset of the pool, so the sealed promise "
                "is honoured and exceeded, and no correction to the sealed file is required."
            ),
        },
        "spacing_rule": (
            "indices {(offset + floor(i*n/m)) mod n : i in 0..m-1} over the sorted candidate "
            "list; the draw order is those m picks in i-order, then the remaining candidates "
            "ordered by maximum minimum circular distance to every already-taken index, ties "
            "broken by the lower index, so a backfill comes from a representative point in the "
            "candidate space rather than off the sorted head. Selection is the first m draw-order "
            "entries not in the rejection log. A stratum marked select_distinct_target additionally "
            "skips a draw-order entry whose target unit is already selected, continuing the forward "
            "walk until m are taken, the same forward walk a rejection uses. A source marked "
            "select_distinct_from names another source in the same stratum and starts its walk "
            "with that source's already-selected units in its taken set, keyed on element 0 of a "
            "pair or on the candidate itself for a bare string, which makes the two sources "
            "order-dependent in the order canonical_offset_order fixes. A source marked "
            "select_distinct_identity_group carries a key_by_candidate map and skips an entry "
            "whose key is already taken; a candidate absent from that map carries no key and never "
            "collides. Every rule applies during backfill and not only to the initial picks. The "
            "spaced picks reuse eval/dev_unit_pool.json selection_rule."
        ),
        "canonical_offset_order": [list(p) for p in CANONICAL_ORDER],
        "strata": {
            "single_hop": {
                "total": 18,
                "floor": "one per source, then largest remainder proportional to eligible size",
                "eligibility": {
                    "criterion_source": (
                        "The sealed specification's own reason for excluding the Playbook from "
                        "single-hop: its only atomic-factual candidates are duplicates of the NIST "
                        "subcategory statements, and its unique content is block elaboration rather "
                        "than atomic fact. This allow-list is the mechanical form of that criterion, "
                        "atomic-factual and not a duplicate, not a new composition decision."
                    ),
                    "allow_list": {d: sorted(SINGLE_HOP_TYPES[d]) for d in sh_sources},
                    "excluded": [
                        {
                            "doc": "nist_ai_600_1",
                            "unit_type": "action",
                            "reason": (
                                "procedural suggested-action items rather than atomic fact, and the "
                                "action-to-parent stratum's own source; including them would overlap "
                                "two strata on one unit type"
                            ),
                        },
                        {
                            "doc": "nist_ai_100_1",
                            "unit_type": "part",
                            "reason": (
                                "a bare structural divider carrying no atomic fact; the one unit, "
                                "part_2, reads 'Part 2: Core and Profiles'"
                            ),
                        },
                        {
                            "doc": "nist_ai_600_1",
                            "unit_type": "subcategory_statement where duplicated",
                            "reason": (
                                "verbatim restatements of the AI 100-1 Core statements, rooted at AI "
                                "100-1 in the duplication map, so eligible only in the originating "
                                "document; the same sealed criterion that excludes the Playbook, and "
                                "it avoids inflating precision and NDCG on slots satisfiable from "
                                "three documents"
                            ),
                        },
                    ],
                    "included_over_borderline": [
                        {
                            "doc": "nist_ai_100_1",
                            "unit_type": "category",
                            "reason": (
                                "carries real statements and duplicates nothing, so both sealed tests "
                                "pass; adjacency to its own subcategories is a retrieval-difficulty "
                                "property, not the eligibility criterion, and is left to the rejection "
                                "procedure if a specific draw is unanswerable"
                            ),
                        },
                        {
                            "doc": "nist_ai_100_1",
                            "unit_type": "appendix",
                            "reason": "substantive content, three units remaining",
                        },
                    ],
                    "duplication_filter": {"nist_ai_600_1_subcategory_statement": dup_split},
                    "eu_heavy_note": (
                        "The 11/5/2 split follows eligible supply, which is a property of the corpus. "
                        "Forcing NIST single-hop slots would manufacture balance, the same error as "
                        "forcing a NIST clean-multi-hop slot; in both strata the allocation follows "
                        "supply rather than a target."
                    ),
                },
                "sources": {
                    d: _stratum_source("single_hop", d, sh_pop[d], sh_alloc[d]) for d in sh_sources
                },
            },
            "clean_multi_hop": {
                "total": 12,
                "floor": "withdrawn for this stratum; see recorded_finding",
                "gold_target_disjointness": (
                    "No two selected edges share a target unit; art_72 was gold for two spaced "
                    "picks, which would correlate their outcomes and shrink effective n. Enforced "
                    "by the forward walk under select_distinct_target, not by removing candidates."
                ),
                "backfill_authoring_rule": (
                    "A pick entering by backfill, from a distinct-target skip or an authoring "
                    "rejection, gets the same both-endpoints test at authoring that a spaced pick "
                    "gets: it is rejected with a recorded reason if no query requiring content from "
                    "both endpoints can be written, rather than one where the source only points at "
                    "where the answer lives. This covers every future replacement without "
                    "pre-judging its text."
                ),
                "sources": {"eu_internal_xref": cm_source},
            },
            "action_to_parent": {
                "total": 4,
                "raw_edges": 212,
                "excluded_parent_in_closure": action_dropped,
                "sources": {
                    "action_subcategory": _stratum_source(
                        "action_to_parent", "action_subcategory", action_edges, 4
                    )
                },
            },
            "near_miss": {
                "total": 8,
                "population_correction": nm_population_correction,
                "cross_source_cascade": nm_cross_source_cascade,
                "backfill_authoring_rule": nm_backfill_authoring_rule,
                "sources": {
                    "block_clusters": nm_bc,
                    "near_duplicate": nm_nd,
                },
            },
            "adversarial": {
                "total": 8,
                "draw": False,
                "spec": {"iso": 3, "nonexistent_identifier": 4, "out_of_domain": 1},
                "absence_verification_requirement": (
                    "Each fabricated identifier is checked absent against eval/corpus_unit_index.json "
                    "and the frozen chunk-id set, with a same-form positive control; the records ship "
                    "with the queries in eval/test_query_verification.jsonl, not in this frame."
                ),
            },
        },
        "recorded_finding": {
            "clean_multi_hop_is_eu_only": finding,
            "cross_stratum_gold_govern_1_3": govern_1_3,
            "near_miss_population_overlap_resolved_silently": near_miss_overlap,
            "near_duplicate_record_10_internally_inconsistent": near_duplicate_record_10,
        },
    }


def to_bytes(frame: dict) -> bytes:
    return (json.dumps(frame, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def build() -> dict:
    # Guard: the index the frame cites must be the committed one, byte-for-byte.
    if not UNIT_INDEX.exists() or UNIT_INDEX.read_bytes() != index_to_bytes(derive_index()):
        raise RuntimeError("eval/corpus_unit_index.json is missing or stale; build it first")
    frame = build_frame()
    OUTPUT.write_bytes(to_bytes(frame))
    return frame


def main() -> int:
    frame = build()
    sh = frame["strata"]["single_hop"]["sources"]
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")
    print(f"  closure {frame['closure']['n']}")
    print("  single_hop alloc " + ", ".join(f"{d}={sh[d]['allocation']}/{sh[d]['n_candidates']}" for d in sh))
    print(f"  clean_multi_hop 12 from {frame['strata']['clean_multi_hop']['sources']['eu_internal_xref']['n_candidates']} EU edges")
    print(f"  action_to_parent 4 from {frame['strata']['action_to_parent']['sources']['action_subcategory']['n_candidates']}")
    nm = frame["strata"]["near_miss"]["sources"]
    print(f"  near_miss 3 from {nm['block_clusters']['n_candidates']} clusters, 5 from {nm['near_duplicate']['n_candidates']} near-duplicate pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
