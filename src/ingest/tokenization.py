"""The pinned chunking tokenizer.

Chunk boundaries decide chunk IDs, and chunk IDs are cited by the pre-registered
gold passages, which are immutable once results exist. So the tokenizer that
governs splitting is pinned here as a named constant with its vocabulary file
checksum recorded in the ingestion manifest. Swapping the retrieval model later
cannot silently move a chunk ID: the manifest would show a different tokenizer
identity, and the ingestion output hash would change.

The tokenizer is vendored under `vendor/` rather than downloaded at run time, so
chunking is fully offline and deterministic.

Token counts include the [CLS] and [SEP] special tokens, because those occupy
positions in the encoder's 512-position window. Counting without them would let
a 512-token chunk overflow to 514 at embedding time and be silently truncated.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from tokenizers import Tokenizer

REPO_ROOT = Path(__file__).resolve().parents[2]

# Pinned identity. Changing any of these changes chunk boundaries and therefore
# chunk IDs, so all three are recorded in the ingestion manifest.
TOKENIZER_MODEL_ID = "BAAI/bge-base-en-v1.5"
TOKENIZER_DIR = REPO_ROOT / "vendor" / "bge-base-en-v1.5"
TOKENIZER_FILE = TOKENIZER_DIR / "tokenizer.json"

# The model's real ceiling: bge-base-en-v1.5 is a BERT encoder with
# max_position_embeddings = 512. A chunk over this would be truncated at
# embedding time, losing text from the index without any error.
MAX_TOKENS = 512


@lru_cache(maxsize=1)
def get_tokenizer() -> Tokenizer:
    if not TOKENIZER_FILE.exists():
        raise FileNotFoundError(
            f"vendored tokenizer missing: {TOKENIZER_FILE}. "
            "Chunking is pinned to this file so ingestion stays offline and deterministic."
        )
    tokenizer = Tokenizer.from_file(str(TOKENIZER_FILE))
    if tokenizer.truncation is not None:
        # Truncation would make count_tokens report a capped value and hide overflow.
        tokenizer.no_truncation()
    return tokenizer


def count_tokens(text: str) -> int:
    """Token count as the encoder will see it, including [CLS] and [SEP]."""
    return len(get_tokenizer().encode(text).ids)


@lru_cache(maxsize=1)
def tokenizer_fingerprint() -> dict[str, str | int]:
    """Identity recorded in the manifest so a swap cannot pass unnoticed."""
    digest = hashlib.sha256(TOKENIZER_FILE.read_bytes()).hexdigest()
    return {
        "model_id": TOKENIZER_MODEL_ID,
        "tokenizer_file": str(TOKENIZER_FILE.relative_to(REPO_ROOT)),
        "tokenizer_file_sha256": digest,
        "max_tokens": MAX_TOKENS,
        "counts_special_tokens": "true",
    }
