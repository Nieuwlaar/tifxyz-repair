# tifxyz-doctor

**Validate, audit, and repair `tifxyz` surface-mesh patches from the [Vesuvius Challenge](https://scrollprize.org).**

`tifxyz` is the grid-topology mesh format used by [VC3D](https://github.com/ScrollPrize/villa/tree/main/volume-cartographer) and the whole Vesuvius segmentation pipeline: a directory with `x.tif`/`y.tif`/`z.tif` (float32 grids of 3D vertices) plus a `meta.json` sidecar. Metadata in these sidecars can silently go stale or corrupt — and downstream tools then silently drop or misuse the data.

`tifxyz-doctor` catches (and where safe, repairs) the known failure families:

| Check | What it catches | Why it matters |
|---|---|---|
| `bbox-stale` | `meta.json` bbox no longer matches the actual vertex extents | bbox-based filters (e.g. z-range selection of spiral-fit inputs) **silently drop valid patches** — [villa #1272](https://github.com/ScrollPrize/villa/issues/1272) documents 106 affected patches in the published PHercParis4 `spiral-input` dataset, up to 654 voxels off |
| `bbox-malformed` | unparseable bbox field | crashes or undefined filtering behavior |
| `meta-voxelsize` | zero/negative voxel size | zero voxel size nullifies area computations and gets segments **silently discarded** (the [villa #1226](https://github.com/ScrollPrize/villa/issues/1226) failure class) |
| `meta-scale` | missing/invalid `scale` | breaks size/area math everywhere downstream |
| `nan-vertices`, `partial-sentinel` | NaN/Inf coordinates; vertices where y/z are `-1` but x is not | VC3D treats them as *valid* vertices (validity = `x != -1` only), so they poison meshes and bboxes |
| `grid-shape`, `grid-dtype`, `tif-read`, `meta-parse` | mismatched/corrupt/unreadable files | fail loudly here instead of mysteriously later |

Plus an optional **deep geometry inspection** (`inspect`) targeting the mesh-defect families named in the [2026 Open Problems post](https://scrollprize.org/2026_open_problems) (holes, mergers, sheet switches):

- interior holes in the valid-vertex grid
- grid-spacing distortion vs the expected `1/scale` voxel pitch
- **sheet-switch / merger suspects**: vertex pairs far apart in grid space but close in 3D
- normal flips between adjacent quads

All CPU-only, no GPU required. Fast: a full validate pass runs at ~1,000 patches/minute on a 16-core machine; `inspect` takes ~0.5 s per typical patch.

## Install

```bash
pip install "tifxyz-doctor[deep] @ git+https://github.com/Nieuwlaar/tifxyz-doctor"
# or from a checkout:
pip install -e ".[deep]"
```

Python ≥ 3.10. Core dependencies: `numpy`, `tifffile`, `imagecodecs`. The `[deep]` extra adds `scipy` + `matplotlib` for `inspect`.

## Usage

### Validate one patch (or a whole tree)

```bash
tifxyz-doctor validate path/to/segment.tifxyz
tifxyz-doctor validate path/to/patches_dir/        # recurses
tifxyz-doctor validate path/to/patch --json        # machine-readable
```

Exit code `0` = clean, `1` = at least one error-severity finding.

```
[  error] verified_patches/auto_grown_20260420184842414_region_000
    ✗ bbox-stale: stored bbox is stale: max drift 439.0 voxels, 5.4% of valid vertices outside the stored box (villa #1272)
```

### Audit a whole corpus in parallel

```bash
tifxyz-doctor report verified_patches/ --workers 14 --csv audit.csv --out audit.md
```

Emits a Markdown summary (counts by check, worst offenders ranked by bbox drift) and a per-finding CSV.

### Repair stale bboxes

```bash
tifxyz-doctor fix verified_patches/ --dry-run   # show what would change
tifxyz-doctor fix verified_patches/             # recompute + write (keeps meta.json.bak)
tifxyz-doctor fix patch/ --strip-bbox           # or remove bbox (mirrors vc_tifxyz_trim; VC3D recomputes lazily)
```

`fix` only ever touches the `bbox` field; every other byte of `meta.json` is preserved. Writes are atomic (`meta.json.tmp` + rename), exactly like VC3D's own save path.

### Deep geometry inspection

```bash
tifxyz-doctor inspect segment.tifxyz --png-dir defect_maps/
```

Prints JSON metrics and (optionally) renders per-patch defect-map PNGs (validity, spacing distortion, z-height).

## Use as a library

All checks are importable — embed them in pipelines, dataset publication gates, or CI:

```python
from tifxyz_doctor.core import load_patch, compute_bbox
from tifxyz_doctor.checks import validate_patch, worst_severity

patch = load_patch("segment.tifxyz")
findings = validate_patch(patch)          # list of {check, severity, message, ...}
assert worst_severity(findings) != "error"
low, high = compute_bbox(patch)           # ground-truth bbox, QuadSurface semantics
```

For maintainers of the affected `spiral-input` corpus: [`audit/corrected_bboxes.json`](audit/corrected_bboxes.json) contains ready-to-apply recomputed bboxes for all 128 stale patches — no need to run anything.

## Semantics: matching VC3D exactly

The reference implementation for this format is C++ (`QuadSurface.cpp` in villa). `tifxyz-doctor` mirrors it deliberately:

- **Validity**: a vertex is invalid iff its **x** coordinate `== -1` — VC3D's `QuadSurface::bbox()` tests only channel 0. (That's why `partial-sentinel` vertices, with `-1` in y/z only, are dangerous: VC3D counts them as valid.)
- **bbox**: `[[min_x, min_y, min_z], [max_x, max_y, max_z]]` over valid vertices only.
- **Root cause of #1272**: `QuadSurface::bbox()` caches the box loaded from `meta.json` and only recomputes when unset — so a grid modified after load (e.g. re-optimization) saves the *pre-modification* bbox. `tifxyz-doctor fix` recomputes from the coordinate grids, which are the ground truth.
- **meta.json writing**: indent 4, trailing newline, atomic temp-file + rename — byte-compatible with VC3D's writer.

## Real-world results

Run against the published PHercParis4 `spiral-input` verified-patch corpus (the inputs to whole-scroll spiral fitting; synced 2026-07-30), `tifxyz-doctor` independently confirms and extends the villa #1272 report: **128 of 5,211 patches have stale bboxes** — including the issue's worst known offender (`same_wrap002986_lasagna`, 654-voxel drift, 25.6% of valid vertices outside the stored box) and six patches whose boxes drifted by **10,000–12,566 voxels** in the *over-covering* direction (no vertex loss, but spatial queries match patches they shouldn't). The whole 5,211-patch audit takes ~36 s on 14 workers. A corpus-wide deep-geometry pass ([`audit/deep_audit.md`](audit/deep_audit.md), ~7 min) additionally finds — among the 4,917 ordinary patches — **44 with sheet-switch/merger suspects, 620 with interior holes, and 510 with >1% stretched edges**, while correctly distinguishing long band surfaces whose self-proximity is legitimate winding clearance (verified at median 8.9-voxel separation, not duplicated geometry). See [`audit/`](audit/) for the full report and CSV produced by:

```bash
tifxyz-doctor report verified_patches/ --workers 14 --csv audit/audit.csv --out audit/audit.md
```

## License

MIT
