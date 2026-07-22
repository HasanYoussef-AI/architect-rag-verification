# Corpus sources and provenance

The code in this repository is licensed under Apache 2.0 (see `LICENSE`). The
corpus documents are not covered by that license. Each document retains its own
license or reuse terms, recorded per document below. NIST publications and
EUR-Lex documents fall under two different legal regimes, and they are stated
separately rather than under one blanket line.

ISO/IEC 42001 is copyrighted and is never included in this repository in any
form. It is referenced by pointer only. Recording the reuse terms of the
documents that are shipped is what makes that exclusion a consistent rule rather
than an arbitrary one.

All files were retrieved on 2026-07-22.

## Immutability of `raw/`

Everything under `corpus/*/raw/` is byte-identical to what the publisher served
and is never hand-edited. No document text was reconstructed, retyped,
summarised, or completed from any other source. Text extraction, parsing, and
chunking happen in the ingestion step and write to a separate location. The
checksums below pin the committed bytes, so any later modification is
detectable.

## File index

One row per file. Checksums and as-served metadata are in the second table to
keep both readable.

| File | Document | Identifier | Version, revision, or date | Publisher | Retrieved | Bytes |
| --- | --- | --- | --- | --- | --- | --- |
| `eu_ai_act/raw/CELEX_32024R1689_EN_OJ.html` | EU Artificial Intelligence Act | CELEX 32024R1689 | Official Journal text, OJ L, 2024/1689, 12.7.2024 | Publications Office of the European Union | 2026-07-22 | 1,264,455 |
| `eu_ai_act/raw/CELEX_32024R1689_EN_OJ.pdf` | EU Artificial Intelligence Act | CELEX 32024R1689 | Official Journal text, OJ L, 2024/1689, 12.7.2024 | Publications Office of the European Union | 2026-07-22 | 2,583,319 |
| `nist_ai_rmf/raw/NIST.AI.100-1.pdf` | AI Risk Management Framework (AI RMF 1.0) | NIST AI 100-1 | Version 1.0, cover date January 2023 | NIST, U.S. Department of Commerce | 2026-07-22 | 1,946,127 |
| `nist_ai_rmf/raw/NIST.AI.600-1.pdf` | AI RMF: Generative AI Profile | NIST AI 600-1 | Cover date July 2024 | NIST, U.S. Department of Commerce | 2026-07-22 | 1,174,643 |
| `nist_ai_rmf/raw/AI_RMF_Playbook.pdf` | NIST AI RMF Playbook | none assigned | Unversioned, see the Playbook section | NIST, U.S. Department of Commerce | 2026-07-22 | 2,882,270 |

| File | SHA-256 | `last-modified` as served |
| --- | --- | --- |
| `eu_ai_act/raw/CELEX_32024R1689_EN_OJ.html` | `a6f77d735ed4f8934a3515864c6334c11461354b7d1eeb868e282a36f58230f1` | not sent |
| `eu_ai_act/raw/CELEX_32024R1689_EN_OJ.pdf` | `bba630444b3278e881066774002a1d7824308934f49ccfa203e65be43692f55e` | not sent |
| `nist_ai_rmf/raw/NIST.AI.100-1.pdf` | `7576edb531d9848825814ee88e28b1795d3a84b435b4b797d3670eafdc4a89f1` | Wed, 04 Jun 2025 17:14:26 GMT |
| `nist_ai_rmf/raw/NIST.AI.600-1.pdf` | `6e73620ab6b64e90ef2c04bf0e0d6246185a2f4b1b13cab0df494496cff89b6a` | Mon, 24 Mar 2025 19:11:27 GMT |
| `nist_ai_rmf/raw/AI_RMF_Playbook.pdf` | `65d6101d806502875aadb0fd19a75c3a9cc9a5e9461129e9398a39192d8202d2` | Mon, 16 Sep 2024 16:19:06 GMT |

All five downloads returned HTTP 200, and each file's size matched the
`Content-Length` advertised by the server.

# Licensing and reuse terms

The terms below were read from the publishers' own notices at the URLs given,
not stated from memory. Where a notice is ambiguous about our specific case,
the ambiguity is recorded rather than resolved in this repository's favour.

## EU AI Act, EUR-Lex regime

Applies to `CELEX_32024R1689_EN_OJ.html` and `CELEX_32024R1689_EN_OJ.pdf`.

- Rights holder: © European Union, 1998-2026.
- Applicable terms: the Commission's document reuse policy, based on
  **Commission Decision 2011/833/EU**. The EUR-Lex notice states that unless
  otherwise specified, the legal documents published in EUR-Lex may be re-used
  for commercial or non-commercial purposes.
- Source notice: https://eur-lex.europa.eu/content/legal-notice/legal-notice.html
- Decision 2011/833/EU: http://data.europa.eu/eli/dec/2011/833/oj

Two points of precision that matter for this corpus.

First, the Creative Commons Attribution 4.0 licence named in the same EUR-Lex
notice does **not** apply to these files. That licence is scoped to the
editorial content of the EUR-Lex website, the summaries of EU legislation, and
the consolidated texts. The files here are the Official Journal legal text, so
they fall under the Decision 2011/833/EU reuse policy instead. Since the
consolidated text was deliberately not used (see the ruling below), the CC BY
4.0 branch is not engaged at all.

Second, a stated ambiguity. The EUR-Lex notice attaches the explicit
"acknowledge the source and indicate any changes" wording to the CC BY 4.0
clause, not to the sentence authorising reuse of legal documents. Attribution
for legal documents follows from Decision 2011/833/EU itself rather than from
that sentence. This repository attributes the source in full either way, so
nothing turns on the ambiguity, but it is recorded rather than smoothed over.

The EUR-Lex notice also warns that some documents, such as the International
Accounting Standards, carry special conditions of use stated in the document
itself. The retrieved AI Act file was checked for such a notice and carries
none, nor any "all rights reserved" marking.

## NIST publications, two different sub-regimes

NIST works are not one uniform regime, and the three NIST files here do not all
sit in the same category.

### AI 100-1 and AI 600-1, NIST Technical Series Publications

Both documents carry a NIST report number, a DOI, and a reference to NIST
Technical Series Policies, which places them in the NIST Technical Series.

- Applicable terms: works authored by NIST employees are not subject to
  copyright protection within the United States, and foreign rights are
  reserved. To the extent NIST may assert rights outside the United States, the
  public is granted a non-exclusive, perpetual, paid-up, royalty-free, worldwide
  right to reprint the works in all formats and in derivative works. NIST asks
  that the recommended citation be followed by "Republished courtesy of the
  National Institute of Standards and Technology."
- Source notice: https://www.nist.gov/open/copyright-fair-use-and-licensing-statements-srd-data-software-and-technical-series-publications
- Underlying statute for the general position: 17 U.S.C. 105,
  https://www.law.cornell.edu/uscode/text/17/105
- Statutory basis NIST cites for the Technical Series: Public Law 100-519,
  Section 107 (24 October 1988).

Stated ambiguity, taken from NIST's own wording: NIST notes that some works it
publishes may have been written by third parties and may be subject to copyright
protection. The grant is therefore not an unconditional guarantee that every
element of every document is free of third-party rights. Note also that the
position is "not subject to copyright within the United States, foreign rights
reserved", which is narrower than a worldwide public-domain dedication, although
the reprint grant above is expressed as worldwide.

### AI RMF Playbook, general NIST site terms

The Playbook is **not** a NIST Technical Series publication. It carries no NIST
report number, no DOI, and no NIST Technical Series Policies reference, and it
is served from `airc.nist.gov` rather than the NIST publications repository. The
Technical Series statement above should therefore not be read as covering it.

- Applicable terms: the general NIST site terms, which state that with the
  exception of material marked as copyrighted, information presented on NIST
  sites is considered public information and may be distributed or copied, and
  that use of appropriate byline and credits is requested.
- Source notice: https://www.nist.gov/copyrights-disclaimers
  (reached via a 301 redirect from https://www.nist.gov/oism/copyrights)
- 17 U.S.C. 105 applies to the extent the content is authored by NIST employees.

Stated ambiguity: the Playbook carries no licence, copyright, or attribution
statement of its own anywhere in the document, so its status rests on the
general site terms plus 17 U.S.C. 105 rather than on an explicit publication
notice. Its reference list cites third-party works, and NIST's general terms
carve out material marked as copyrighted. This is a weaker and less explicit
basis than the one covering AI 100-1 and AI 600-1, and it is recorded as such.

## How this repository attributes these sources

This section exists to satisfy the attribution that the publishers request in
the terms recorded above.

### EU Artificial Intelligence Act

Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13
June 2024 laying down harmonised rules on artificial intelligence and amending
Regulations (EC) No 300/2008, (EU) No 167/2013, (EU) No 168/2013, (EU) 2018/858,
(EU) 2018/1139 and (EU) 2019/2144 and Directives 2014/90/EU, (EU) 2016/797 and
(EU) 2020/1828 (Artificial Intelligence Act), OJ L, 2024/1689, 12.7.2024, ELI:
http://data.europa.eu/eli/reg/2024/1689/oj. Published by the Publications Office
of the European Union. © European Union, 1998-2026. Retrieved 2026-07-22.

### NIST AI 100-1 and AI 600-1

Source note: NIST does not print a recommended citation in the front matter of
either PDF. The two citations below are reproduced as published in the
"Citation" field of each document's official NIST publication landing page,
which is where NIST states them. The accessed date shown is this repository's
retrieval date. Each is followed by the courtesy line NIST asks for.

Tabassi, E. (2023), Artificial Intelligence Risk Management Framework (AI RMF
1.0), NIST Trustworthy and Responsible AI, National Institute of Standards and
Technology, Gaithersburg, MD, [online], https://doi.org/10.6028/NIST.AI.100-1,
https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=936225 (Accessed July 22,
2026)

Republished courtesy of the National Institute of Standards and Technology.

Autio, C., Schwartz, R., Dunietz, J., Jain, S., Stanley, M., Tabassi, E., Hall,
P. and Roberts, K. (2024), Artificial Intelligence Risk Management Framework:
Generative Artificial Intelligence Profile, NIST Trustworthy and Responsible AI,
National Institute of Standards and Technology, Gaithersburg, MD, [online],
https://doi.org/10.6028/NIST.AI.600-1,
https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=958388 (Accessed July 22,
2026)

Republished courtesy of the National Institute of Standards and Technology.

### NIST AI RMF Playbook

No recommended citation is printed in the document, and none is given on its
landing page, so the citation below is composed from what the document and the
landing page actually state.

AI RMF Playbook, National Institute of Standards and Technology, U.S. Department
of Commerce, [online], https://airc.nist.gov/docs/AI_RMF_Playbook.pdf, landing
page https://airc.nist.gov/airmf-resources/playbook/ (Accessed July 22, 2026).
No version number or release date is printed, so the retrieved file is
identified by the SHA-256 and the server `last-modified` date of 2024-09-16
recorded above.

Credit: National Institute of Standards and Technology.

# Document detail

## EU Artificial Intelligence Act

Full title: Regulation (EU) 2024/1689 of the European Parliament and of the
Council of 13 June 2024 laying down harmonised rules on artificial intelligence
and amending Regulations (EC) No 300/2008, (EU) No 167/2013, (EU) No 168/2013,
(EU) 2018/858, (EU) 2018/1139 and (EU) 2019/2144 and Directives 2014/90/EU,
(EU) 2016/797 and (EU) 2020/1828 (Artificial Intelligence Act).

- Identifier: CELEX 32024R1689
- ELI: http://data.europa.eu/eli/reg/2024/1689/oj
- Official Journal reference: OJ L, 2024/1689, 12.7.2024
- Source URLs, both HTTP 200:
  - HTML: https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32024R1689
  - PDF: https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32024R1689
- PDF: 144 pages, internal creation date 2024-07-11.

### Ruling: original Official Journal text, consolidated version rejected

The original Official Journal text is used. A consolidated version was checked
first and rejected, and the reason is stronger than a version-date preference.

**There is no English consolidated version of this regulation.** EUR-Lex lists a
consolidated version dated 12/07/2024 under CELEX 02024R1689-20240712, but
requesting it through the English interface returns the notice "The document is
unavailable in your User interface language" and serves the French text instead.
The served header line carries the CELEX number 02024R1689, the language code
FR, the consolidation date 12.07.2024, and the revision number 000.001.

The mechanism explains why. Consolidated versions are produced only for the
language versions that received a corrigendum. Four corrigenda have been issued
against this regulation, and English appears in none of them:

| Corrigendum | Language versions affected |
| --- | --- |
| 32024R1689R(01) | ES, DE, FR, GA, LT, HU, SK, SL, SV |
| 32024R1689R(02) | NL, SL |
| 32024R1689R(03) | CS |
| 32024R1689R(04) | ES, NL |

The English text has therefore never been corrected. The Official Journal text
is both the only English text and the authentic one. EUR-Lex states in its own
disclaimer that only documents published in the Official Journal are deemed
authentic, and consolidated texts carry an explicit disclaimer that they are a
documentation tool with no legal effect.

Two amending acts are listed against the regulation, 52025PC0836 and
52025PC1023. Both are Commission proposals, neither is in force, and neither
affects the text as retrieved.

### Reproducing the HTML checksum

The EUR-Lex HTML response embeds a per-request analytics script whose
`agentId`, `rid`, and `rpid` attributes change on every request. A reviewer who
re-downloads the file will therefore compute a different raw SHA-256 even though
the legal text is unchanged. This was verified by fetching the document twice:
the two responses were the same length, 1,264,455 bytes, and differed only
inside the `ruxitagentjs` script element, 518 bytes in total.

The raw checksum in the file index pins the committed bytes, which is what every
downstream number in this repository reproduces from, since the file itself is
committed.

For a checksum reproducible from a fresh download, remove the injected analytics
element before hashing. The rule is: decode the file as UTF-8, delete every
match of the regular expression `<script[^>]*ruxitagentjs.*?</script>` evaluated
with the dot-matches-newline flag, re-encode as UTF-8, and take the SHA-256 of
the result. Equivalently:

```python
import hashlib, re, sys
raw = open(sys.argv[1], 'rb').read()
text = raw.decode('utf-8', errors='surrogateescape')
stripped = re.sub(r'<script[^>]*ruxitagentjs.*?</script>', '', text, flags=re.DOTALL)
print(hashlib.sha256(stripped.encode('utf-8', errors='surrogateescape')).hexdigest())
```

```
stable content SHA-256: 7b1622f36bf2bac85bbedf4f95cf8a3ee79e116da7d431c20fabe1d4c9a327c1
```

This value was confirmed to be identical across two independent fetches whose
raw checksums differed. The PDF contains no injected content and its raw
SHA-256 is directly reproducible.

### Why the HTML format, and why not Formex XML

Chunking is structure-aware along each document's native units, so the parse
source must expose Article and Annex boundaries. The Official Journal HTML
carries semantic ELI anchors that match the structure of the act exactly:
`art_1` through `art_113` for the 113 Articles, `anx_I` through `anx_XIII` for
the 13 Annexes, `rct_1` through `rct_180` for the 180 Recitals, plus
`cpt_*.sct_*` anchors for Chapters and Sections, and paired `oj-ti-art` and
`oj-sti-art` article titles and subtitles.

Formex 4 XML was considered and rejected on availability, not on preference:

| Candidate | Result |
| --- | --- |
| `http://publications.europa.eu/resource/celex/32024R1689` with `Accept: application/zip;mtype=fmx4` | HTTP 303 to the Cellar manifestation, then **HTTP 404** |
| `http://publications.europa.eu/resource/oj/L_202401689` with `Accept: application/zip;mtype=fmx4` | HTTP 303 to the same manifestation, then **HTTP 404** |
| `https://eur-lex.europa.eu/legal-content/EN/TXT/XML/?uri=CELEX:32024R1689` | HTTP 200, but returns a Cellar bibliographic notice, not the legal text |

The manifestation `L_202401689.ENG.fmx4` is referenced in the Cellar metadata
but is not retrievable, so Formex is not a usable source here.

The PDF is retained as an authoritative reference snapshot, not as a parse
source.

### Ingestion note, non-breaking spaces

Structural titles in the HTML separate the label from the number with a
non-breaking space, U+00A0, rather than an ordinary space. Examples are
`Article` + U+00A0 + `6` and `ANNEX` + U+00A0 + `III`. Any parser matching on
`"Article 6"` with a plain space will silently fail to match. Normalise U+00A0
to a plain space before structural matching during ingestion.

## NIST AI 100-1

- Title: Artificial Intelligence Risk Management Framework (AI RMF 1.0)
- Identifier: NIST AI 100-1
- DOI: https://doi.org/10.6028/NIST.AI.100-1
- Printed cover date: January 2023. Landing page publication date: 26 January
  2023.
- Source URL, HTTP 200: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf
- Landing page: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10
- Pages: 48

### Pinned to version 1.0 as retrieved

NIST describes the framework as a living document and states that a review with
formal input from the AI community is expected no later than 2028. NIST also
states separately that **AI RMF 1.0 is currently being updated**. No revision
has been published as at the retrieval date, so this corpus is pinned to version
1.0 exactly as retrieved on 2026-07-22 and as pinned by the checksum above. A
reviewer re-downloading this URL at a later date may receive a different
document, and the checksum is how that is detected.

## NIST AI 600-1

- Title: Artificial Intelligence Risk Management Framework: Generative
  Artificial Intelligence Profile
- Identifier: NIST AI 600-1, in the NIST Trustworthy and Responsible AI series
- DOI: https://doi.org/10.6028/NIST.AI.600-1
- Source URL, HTTP 200: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf
- Landing page: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- Pages: 64

### Four dates, and the discrepancy stated plainly

Four different dates are attached to this document by four different sources,
and they do not agree:

| Source | Date |
| --- | --- |
| Printed on the document cover | July 2024, with "Approved by the NIST Editorial Review Board on 07-25-2024" |
| Landing page "Published" field | 26 July 2024 |
| Landing page "Updated" marker | 8 April 2026 |
| HTTP `last-modified` on the PDF | 24 March 2025 |

The reading recorded here is that the later dates reflect re-posts and page
edits, not a revision of the document:

- The "Updated April 8, 2026" string sits in the page footer immediately before
  "Was this page helpful?" and the site address block, which is the standard
  NIST page-level last-edited marker, not a document field. The document field
  on the same page, "Published", still reads 26 July 2024.
- The HTTP `last-modified` of 24 March 2025 predates that April 2026 marker, so
  the two cannot both describe the same document event.
- The document itself still carries the July 2024 cover date, the same DOI, and
  no revision number or errata notice.

The printed cover date governs for citation. The checksum pins the exact bytes
retrieved regardless of any re-post. The same pattern applies to AI 100-1, whose
`last-modified` is 4 June 2025 against a January 2023 cover date. This is
recorded as an observation, not as a resolved fact about NIST's internal
process.

## NIST AI RMF Playbook

- Title: AI RMF Playbook
- Identifier: none assigned. No NIST report number, no DOI, no version number,
  and no printed release date anywhere in the document.
- Source URL, HTTP 200: https://airc.nist.gov/docs/AI_RMF_Playbook.pdf
- Landing page: https://airc.nist.gov/airmf-resources/playbook/
- Pages: 147
- PDF internal creation date: 2024-08-02. Server `last-modified` as retrieved:
  **Mon, 16 Sep 2024 16:19:06 GMT**.

### Limitation, recorded deliberately

The Playbook is a living resource. NIST states that updates are released
approximately twice per year, and that the Playbook will be updated again after
AI RMF 1.0 is revised. It therefore cannot be cited to a stable revision
identifier the way AI 100-1 and AI 600-1 can, and it is the weakest link in this
corpus from a provenance standpoint.

Reproducibility is preserved by a different route. The exact file is committed
to this repository and pinned by its SHA-256 and by the server `last-modified`
of 2024-09-16 recorded above, so every downstream number reproduces from the
committed bytes regardless of what NIST publishes later. A reviewer downloading
the Playbook fresh at a later date may well receive a different file, and the
checksum is how that is detected rather than something that would pass
unnoticed.

The Playbook is organised by AI RMF subcategory, 72 of them across the four
functions, and cross-references AI 100-1 directly, which is why it is included.
That overlap with the Core is a known consideration for gold-passage definition
and is handled at the pre-registration step, not here.

# Retrieval notes

**EUR-Lex rate limiting.** Under load, EUR-Lex responds with **HTTP 202 Accepted
and an empty body** rather than an error status, and it may also return a
zero-length body on an otherwise successful-looking request. A naive downloader
will treat that as success and write an empty or truncated file. Anyone
re-downloading these files should check that the response body is non-empty and
of the expected size, and back off and retry rather than trusting the status
code alone. Both EU files here were verified against the size the server
advertised.

**NIST hosts.** `nvlpubs.nist.gov` and `airc.nist.gov` served all three PDFs
without throttling. `https://www.nist.gov/oism/copyrights` responds with HTTP
301 and redirects to `https://www.nist.gov/copyrights-disclaimers`.
