# Unverified-patch audit, PHercParis4 spiral-input

Audited **all 40,782** patch directories of the published `unverified_patches/`
corpus (203,900 files, synced complete 2026-07-31). Validity follows VC3D's loader
rules, see the README.

| check | result |
|---|---|
| stale bbox, any direction | **0** |
| stale bbox, under-covering (the #1272 class) | **0** |
| missing bbox | 0 |
| unreadable / malformed | 0 |

Every patch validates clean. This independently reproduces the full-scan result
reported in villa #1272 (0 / 40,782 stale) and supports the reading that the
corruption originates in the verification and re-optimization pipeline rather than
in patch generation.

Note for anyone reproducing this: an earlier version of this tool replayed only the
`x == -1` validity rule and reported roughly 3.6% of these patches as stale. Every one
of those was a false positive caused by ignoring the loader's `z <= 0` and `mask.tif`
rules. Getting the validity rules right is the difference between confirming the issue
and contradicting it.
