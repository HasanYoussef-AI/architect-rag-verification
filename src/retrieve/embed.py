"""Corpus embeddings from bge-base-en-v1.5, ONNX path, generated once and committed.

Build-only. Retrieval reads the committed embeddings; this module runs the model
and is not imported in the runtime path. It uses onnxruntime rather than
transformers because transformers pins tokenizers <= 0.23.0 while the frozen
chunking tokenizer is 0.23.1. The deciding reason for the ONNX path is not that
conflict, though: it lets the SAME frozen tokenizer that determined the chunk
boundaries also tokenise the text for embedding, so the two halves of the repo do
not run different tokenizer builds. The conflict is the trigger, the consistency
is the justification.

Weight run: onnx/model.onnx at the pinned revision, SHA-256 verified on download.
Pooling is CLS, read from the model's own 1_Pooling/config.json
(pooling_mode_cls_token: true). Embeddings are L2-normalised for cosine. No query
instruction: the bge-v1.5 card states embeddings can be generated without one.

The embedding input is comparison-normalised, normalise_for_comparison, before the
model tokenizer sees it, on BOTH the corpus and the query side. Dense retrieval is a
comparison, so it falls under the same shared-path rule that governs BM25 and the
grounding check: fold the typographic characters our extraction pipeline carries,
curly quotes, en and em dashes, non-breaking space, to the ASCII a typed query
would contain, so a real query's dense vector matches the corpus key rather than
missing it on a publisher's apostrophe. This is a retrieval-key normalisation, not
an edit to stored text, which is never altered.

Determinism settings are explicit, because onnxruntime parallelises reductions and
reduction order changes float results: CPUExecutionProvider only, one intra-op and
one inter-op thread, and a named graph optimisation level, all recorded in the
manifest with the onnxruntime version.
"""

from __future__ import annotations

import hashlib

import numpy as np

from src.ingest.corpus_integrity import REPO_ROOT
from src.ingest.normalize import normalise_for_comparison

MODEL_REPO = "BAAI/bge-base-en-v1.5"
MODEL_REVISION = "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a"
ONNX_FILE = "onnx/model.onnx"
ONNX_SHA256 = "9bc579acdba21c253c62a9bf866891355a63ffa3442b52c8a37d75b2ccb91848"
# Recorded as the file we did NOT run, see the retrieval manifest decision log.
SAFETENSORS_SHA256 = "c7c1988aae201f80cf91a5dbbd5866409503b89dcaba877ca6dba7dd0a5167d7"

MAX_SEQ = 512
EMBED_DIM = 768
GRAPH_OPT_LEVEL = "ORT_ENABLE_ALL"
TOKENIZER_FILE = REPO_ROOT / "vendor" / "bge-base-en-v1.5" / "tokenizer.json"
OUTPUT_DIR = REPO_ROOT / "data" / "retrieval"


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download_onnx() -> str:
    """Download the ONNX weight at the pinned revision and verify its SHA-256."""
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(MODEL_REPO, ONNX_FILE, revision=MODEL_REVISION)
    actual = sha256_file(path)
    if actual != ONNX_SHA256:
        raise ValueError(f"ONNX checksum mismatch: expected {ONNX_SHA256}, got {actual}")
    return path


def make_session(onnx_path: str):
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.graph_optimization_level = getattr(ort.GraphOptimizationLevel, GRAPH_OPT_LEVEL)
    return ort.InferenceSession(onnx_path, sess_options=options, providers=["CPUExecutionProvider"])


def _tokenizer(pad: bool):
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(TOKENIZER_FILE))
    tok.enable_truncation(max_length=MAX_SEQ)
    if pad:
        tok.enable_padding()
    return tok


def embed_texts(texts: list[str], session, batch_size: int = 1) -> np.ndarray:
    """CLS-pooled, L2-normalised float32 embeddings for texts.

    token_type_ids is a required input of this graph and is fed as explicit zeros
    rather than relying on a default.
    """
    tok = _tokenizer(pad=batch_size > 1)
    out = np.empty((len(texts), EMBED_DIM), dtype=np.float32)
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encoded = tok.encode_batch([normalise_for_comparison(t) for t in batch])
        input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids)
        hidden = session.run(
            ["last_hidden_state"],
            {"input_ids": input_ids, "attention_mask": attention_mask, "token_type_ids": token_type_ids},
        )[0]
        cls = hidden[:, 0, :]
        norms = np.linalg.norm(cls, axis=1, keepdims=True)
        out[start : start + len(batch)] = (cls / norms).astype(np.float32)
    return out


def token_lengths(texts: list[str]) -> list[int]:
    """Encoded length of each text under the model's own tokenizer, no truncation.

    Measured on the comparison-normalised text, the same input embed_texts encodes,
    so the truncation check reflects the tokens actually embedded.
    """
    from tokenizers import Tokenizer

    tok = Tokenizer.from_file(str(TOKENIZER_FILE))
    return [len(e.ids) for e in tok.encode_batch([normalise_for_comparison(t) for t in texts])]
