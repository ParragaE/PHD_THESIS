# Module 12 v1.4.4 — Real-PDF regression validation

## Source

- Published Article 01 PDF
- SHA-256: `8393181f65dee0a676b504ace90a0859647a008a0e9671d57851545c43aa90db`
- Pages: 56
- OCR: disabled
- Plot digitization: disabled
- Interpolation: disabled

## Golden Reference Builder result

- Golden-reference rows: **82**
- Historical baseline: **82**
- Coverage status: **PASS**
- Audit rows: **36**
- Scalar `NOT_EXTRACTED`: **0**
- Source-comparison rows: **82**

## Regression comparison against the historical 82-row Golden Reference

The scientific key set is identical: **82/82 keys preserved**. No historical reference was removed and no new key was fabricated.

Exactly two numeric reference values changed, both correcting the previously demonstrated Figure 16 context-association error:

| Figure | Mode | Configuration | Metric | Historical incorrect | v1.4.4 | Article prose |
|---|---|---|---|---:|---:|---:|
| 16 | shared_reload_shuffle | 1N-4P | io_time | 8.13 s | **54.35 s** | 54.35 s |
| 16 | shared_reload_shuffle | 16N-64P | io_time | 6.59 s | **24.31 s** | 24.31 s |

Figure 15 remains unchanged at 8.13 s and 6.59 s.

## Extraction robustness change

Before article regex matching, v1.4.4 normalizes only lexical artifacts introduced by born-digital PDF extraction:

- non-breaking spaces (`U+00A0`) → ordinary spaces;
- typographic dashes used inside configuration labels → ASCII hyphen;
- alphabetic words split at line endings (`configura-\ntion`, `shuf-\nfle`) → rejoined words;
- repeated whitespace/newlines → one space.

Numeric tokens are not modified, inserted, estimated or inferred.

Figure 16 remains scoped to the explicit `Shared(reload+shuffle) Access Mode` subsection. Its I/O-time sentence spans PDF pages 44–45, where page furniture is inserted between `reduces` and `this metric`; the regex tolerates that intervening text while remaining inside the Figure 16 semantic scope.

## Acceptance

**Module 12 Golden Reference Builder v1.4.4: VALIDATED against Article 01 PDF.**
