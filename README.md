# architect-rag-verification

A public case study of a deterministic verification layer over a
retrieval-augmented generation pipeline, evaluated honestly on a bounded public
corpus of AI governance frameworks.

## The problem

TODO: Describe the two RAG failure surfaces this case study targets. Surface one
is generation faithfulness, where the model asserts claims the retrieved chunks
do not support. Surface two is retrieval completeness, where the retriever misses
a relevant passage and the model answers faithfully from partial context. Keep
the two surfaces separate.

## The design

TODO: Describe the raw versus layer comparison. Raw is standard RAG with a neutral
prompt, a single pass, and no verification, and raw means no verification layer,
not no retrieval. Layer is the same model with the same first-pass prompt,
followed by deterministic post-hoc checks that flag, refuse, re-retrieve, or
abstain. Describe closed-book enforcement, the spine of the result: the model
answers only from the retrieved chunks, never from training memory.

## Reproducibility guarantees

TODO: Explain that generation is the only paid step and runs once, with its
outputs committed as data files. Every downstream number then reproduces
deterministically over the committed files with no API key and no cost. Note the
optional path to regenerate answers with a reviewer's own key.

## How to run

TODO: Document the setup and the commands to reproduce the results from the
committed files, and separately the optional generation path that requires a key.
Record the key hygiene pattern, loading the key only inside a subshell.

## Results

TODO: Report the layer-minus-raw delta on the identical query set under the
identical deterministic grader, per model tier and per failure surface. No
numbers are recorded until the runs exist and are committed.

## Honest boundary

TODO: State the boundary. The completeness check works because the corpus is
bounded and small enough to read in full per query, and this does not scale. Name
the rough point where full-corpus checking stops being practical, and do not
claim the bounded-corpus method as a general solution.

## What still fails

TODO: List the real failure modes the layer does not fix, added once measured.

## License

The code in this repository is licensed under the Apache License 2.0 (see
`LICENSE`). Corpus documents keep their own licenses, recorded in
`corpus/SOURCES.md`.
