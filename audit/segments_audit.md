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


**Interpretation.** Every published segment mesh carries a correct bbox. So do all 35,150 *unverified* patches audited (see `unverified_audit.md`). The stale bboxes are confined to the *verified* patch corpus, 106 of 4,922 patch directories under the definition in villa #1272.

That pattern supports the hypothesis in the issue: the corruption comes from the verification and re-optimization pipeline (auto-grown, lasagna, same-wrap re-fitting), which loads a patch, mutates its grid, and saves it again. Surfaces written once and never re-optimized, whether flatboi segment meshes or freshly generated unverified patches, are unaffected.
