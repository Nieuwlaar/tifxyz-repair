# Cross-scroll audit: all published segment meshes (S3 open-data bucket)

Meshes audited: **817** across 7 scrolls (every `segments/*/mesh/*.tifxyz` on the bucket, fetched 2026-07-30).

| scroll | meshes | with errors |
|---|---|---|
| PHerc0139 | 189 | 0 |
| PHerc0172 | 106 | 0 |
| PHerc0343P | 16 | 0 |
| PHerc0500P2 | 116 | 0 |
| PHerc0814 | 57 | 0 |
| PHerc1667 | 79 | 0 |
| PHercParis4 | 254 | 0 |

Error checks across all scrolls: **none, all published segment meshes are clean**


**Interpretation.** Every published segment mesh is clean, while 128/5,211 verified *patches* (see `audit.md`) and ~3.6% of sampled *unverified* patches carry stale bboxes. This scopes the villa #1272 corruption to the re-optimization / patch-editing pipeline (auto-grown, lasagna, same-wrap re-fitting). the published segment meshes, written once by flatboi, are unaffected. Good news for anyone consuming the segment meshes directly; the fix still matters for the patch corpora that feed spiral fitting.
