"""Build the segment embedding cache the dense attributability arm reads.

The cache is deliberately NOT committed, on size: 40,636,416 bytes, 10.2 times the committed
chunk embeddings. This is NOT the retrieval pattern, which commits data/retrieval/embeddings.npy
so retrieval reproduces at level 2 without the model. The cost of declining here is that the dense
arm sits at level 3. What commits is this generator, the pinned model revision it records, and the
per-pick scan output. It is written under embeddings_cache/, git-ignored, and
nothing here reads or writes anything under data/retrieval/, whose parameters are frozen for
retrieval.

Segments come from Corpus.load(), the one segmentation both arms share. The index records a
fingerprint of that exact segmentation, and load_segment_cache refuses a cache whose fingerprint
no longer matches, so changing the segmenter cannot silently leave embeddings that correspond to
text nobody is comparing any more.

Run:  python -m src.goldset.build_segment_embeddings
"""

from __future__ import annotations

import hashlib
import json
import time

import numpy as np

from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.normalize import normalise_for_comparison
from src.retrieve.embed import EMBED_DIM, MODEL_REPO, MODEL_REVISION, embed_texts
from src.goldset.attributability import (
    CACHE,
    DETERMINISM_NOTE,
    MANIFEST,
    SEGMENTER_ID,
    SEGMENT_INDEX,
    SEGMENT_VECTORS,
    Corpus,
    exclusion_report,
    onnx_session,
)

BATCH = 16


def write_manifest(corpus: Corpus) -> dict:
    """Emit the committed manifest from an existing cache, without re-embedding.

    Separated from build so a reviewer holding a regenerated cache can produce the manifest and
    diff it, and so the manifest can be refreshed without a second generation pass.
    """
    index = json.loads(SEGMENT_INDEX.read_text(encoding="utf-8"))
    fingerprint = corpus.segmentation_fingerprint()
    if index["segmentation_fingerprint"] != fingerprint:
        raise ValueError(
            "refusing to write a manifest for a cache built from a different segmentation: "
            f"cache {index['segmentation_fingerprint']!r} against current {fingerprint!r}"
        )
    digest = hashlib.sha256(SEGMENT_VECTORS.read_bytes()).hexdigest()
    manifest = {
        "description": (
            "Reproduction manifest for the attributability dense arm's segment embedding cache. "
            "The cache itself is not committed, at 40.6 MB against the 3.9 MB committed chunk "
            "embeddings, so this manifest is what makes the dense arm checkable: regenerate the "
            "cache with the command below and compare cache_sha256."
        ),
        "cache_path": str(SEGMENT_VECTORS.relative_to(REPO_ROOT)),
        "cache_sha256": digest,
        "cache_bytes": SEGMENT_VECTORS.stat().st_size,
        "cache_sha256_determinism": DETERMINISM_NOTE,
        "n_segments": index["n_segments"],
        "n_units": index["n_units"],
        "segmentation_fingerprint": fingerprint,
        "segmenter": SEGMENTER_ID,
        "exclusion_funnel": exclusion_report(corpus),
        "model_repo": MODEL_REPO,
        "model_revision": MODEL_REVISION,
        "embed_dim": EMBED_DIM,
        "batch_size": BATCH,
        "input_normalisation": (
            "normalise_for_comparison, the same shared comparison path the retriever uses"
        ),
        "generator_command": "python -m src.goldset.build_segment_embeddings",
        "reproducibility_level": 3,
        "reproducibility_note": (
            "Level 3 in data/retrieval/retrieval_manifest.json. Regenerating from ONNX at the "
            "pinned revision reproduces rankings, not bytes, across machines. cache_sha256 is "
            "therefore a same-machine reproduction check and not a cross-platform guarantee; a "
            "reviewer whose digest differs should compare the dense arm's reported units and "
            "cosines rather than the hash."
        ),
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def build() -> dict:
    corpus = Corpus.load()
    pairs = corpus.ordered_segments()
    fingerprint = corpus.segmentation_fingerprint()
    session = onnx_session()
    if session is None:
        raise SystemExit(
            "the pinned ONNX model is not cached and this generator never downloads. "
            "Prime the cache first, then re-run."
        )

    texts = [normalise_for_comparison(segment) for _, segment in pairs]
    print(f"segments to embed: {len(texts)}")
    print(f"segmentation fingerprint: {fingerprint}")

    started = time.perf_counter()
    vectors = np.zeros((len(texts), EMBED_DIM), dtype=np.float32)
    for start in range(0, len(texts), BATCH):
        stop = min(start + BATCH, len(texts))
        vectors[start:stop] = embed_texts(texts[start:stop], session, batch_size=BATCH)
        if start % (BATCH * 40) == 0:
            done = stop
            rate = done / max(time.perf_counter() - started, 1e-9)
            print(
                f"  {done}/{len(texts)}  {rate:.1f} seg/s  "
                f"eta {(len(texts) - done) / max(rate, 1e-9) / 60:.1f} min",
                flush=True,
            )
    elapsed = time.perf_counter() - started

    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1.0, atol=1e-4):
        raise ValueError(
            f"embeddings are not L2-normalised: norm range {norms.min()} to {norms.max()}. "
            "Cosine is computed as a dot product downstream and would be wrong."
        )

    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(SEGMENT_VECTORS, vectors)
    index = {
        "description": (
            "Segment embeddings for the attributability dense arm. Not committed: large and "
            "regenerable. Regenerate with python -m src.goldset.build_segment_embeddings."
        ),
        "model_repo": MODEL_REPO,
        "model_revision": MODEL_REVISION,
        "embed_dim": EMBED_DIM,
        "n_segments": len(texts),
        "n_units": len({u for u, _ in pairs}),
        "segmentation_fingerprint": fingerprint,
        "exclusion_funnel": exclusion_report(corpus),
        "input_normalisation": "normalise_for_comparison, the same shared path the retriever uses",
        "reproducibility_level": 3,
        "build_seconds": round(elapsed, 1),
    }
    SEGMENT_INDEX.write_text(
        json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    manifest = write_manifest(corpus)
    print(f"wrote {SEGMENT_VECTORS}, {SEGMENT_INDEX} and {MANIFEST} in {elapsed / 60:.1f} min")
    print(f"cache_sha256: {manifest['cache_sha256']}")
    return manifest


if __name__ == "__main__":
    build()
