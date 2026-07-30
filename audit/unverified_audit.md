# Unverified-patch audit, PHercParis4 spiral-input

Audited **35,150** patch directories from `unverified_patches/` (synced 2026-07-30; a
partial but large sample of the ~204k published set). Validity follows VC3D's loader
rules, see the README.

| check | result |
|---|---|
| stale bbox, any direction | **0** |
| stale bbox, under-covering (the #1272 class) | **0** |
| missing bbox | 0 |
| unreadable | 0 |

This confirms the observation in villa #1272 that unverified patches are unaffected,
and supports the reading that the corruption originates in the verification and
re-optimization pipeline rather than in patch generation.

Note for anyone reproducing this: an earlier version of this tool replayed only the
`x == -1` validity rule and reported roughly 3.6% of these patches as stale. Every one
of those was a false positive caused by ignoring the loader's `z <= 0` and `mask.tif`
rules. Getting the validity rules right is the difference between confirming the issue
and contradicting it.
