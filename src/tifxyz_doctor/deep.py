"""Deep geometry inspection for tifxyz patches (optional, needs scipy).

These checks target the mesh-defect families named in the Vesuvius
Challenge 2026 Open Problems post ("mergers, holes, sheet switches"):

- interior holes: invalid regions fully enclosed by valid cells
- grid-spacing distortion: adjacent-vertex distances vs the expected
  1/scale voxels (stretch or compression concentrations)
- self-proximity: vertex pairs far apart in grid (UV) space but close in
  3D — the signature of a sheet switch or a merger folding a mesh onto a
  neighboring wrap
- normal flips: adjacent quads whose normals point in opposite directions

All metrics are conservative *detectors*: they flag places a human (or a
downstream repair tool) should look at, they do not modify anything.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import numpy as np

from .core import Patch


def _expected_spacing(patch: Patch) -> Optional[float]:
    meta = patch.meta or {}
    scale = meta.get("scale")
    try:
        s = float(scale[0])
        if s > 0:
            return 1.0 / s
    except (TypeError, ValueError, IndexError):
        pass
    return None


def inspect_patch(patch: Patch, *, proximity_factor: float = 0.5, uv_min_dist: int = 10) -> dict[str, Any]:
    """Compute deep geometry metrics. Returns a JSON-serializable dict."""
    from scipy import ndimage
    from scipy.spatial import cKDTree

    if patch.x.size == 0:
        return {"error": "empty grid"}

    P = patch.points().astype(np.float64)
    V = patch.valid & np.isfinite(P).all(axis=-1)
    H, W = V.shape
    result: dict[str, Any] = {"grid": [H, W], "valid_fraction": float(V.mean())}

    if not V.any():
        result["error"] = "no valid vertices"
        return result

    # --- interior holes -------------------------------------------------
    inv = ~V
    lbl, n = ndimage.label(inv)
    border = np.zeros_like(inv)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    border_labels = set(np.unique(lbl[border & inv]).tolist())
    hole_ids = [i for i in range(1, n + 1) if i not in border_labels]
    hole_sizes = ndimage.sum_labels(inv, lbl, hole_ids).astype(int).tolist() if hole_ids else []
    result["holes"] = {"count": len(hole_ids), "cells": int(sum(hole_sizes)), "largest": max(hole_sizes, default=0)}

    # --- spacing distortion --------------------------------------------
    du = np.linalg.norm(np.diff(P, axis=1), axis=2)
    dv = np.linalg.norm(np.diff(P, axis=0), axis=2)
    mu = V[:, 1:] & V[:, :-1]
    mv = V[1:, :] & V[:-1, :]
    edges = np.concatenate([du[mu], dv[mv]])
    spacing: dict[str, Any] = {}
    if edges.size:
        spacing["median"] = float(np.median(edges))
        spacing["p01"] = float(np.percentile(edges, 1))
        spacing["p99"] = float(np.percentile(edges, 99))
        expected = _expected_spacing(patch)
        if expected:
            spacing["expected"] = expected
            spacing["stretch_frac"] = float((edges > 1.5 * expected).mean())
            spacing["compress_frac"] = float((edges < 0.5 * expected).mean())
    result["spacing"] = spacing

    # --- self-proximity (sheet-switch / merger suspects) ----------------
    expected = _expected_spacing(patch) or (spacing.get("median") or 1.0)
    idx = np.argwhere(V)
    pts = P[V]
    # Subsample very large grids to keep the KD-tree pass fast.
    max_pts = 400_000
    if pts.shape[0] > max_pts:
        stride = int(np.ceil(pts.shape[0] / max_pts))
        pts, idx = pts[::stride], idx[::stride]
    tree = cKDTree(pts)
    pairs = tree.query_pairs(r=expected * proximity_factor, output_type="ndarray")
    if pairs.size:
        uv_dist = np.abs(idx[pairs[:, 0]] - idx[pairs[:, 1]]).max(axis=1)
        suspects = pairs[uv_dist > uv_min_dist]
    else:
        suspects = np.empty((0, 2), dtype=int)
    sus_cells = np.unique(idx[suspects.ravel()], axis=0) if suspects.size else np.empty((0, 2), dtype=int)
    result["self_proximity"] = {
        "pairs": int(len(suspects)),
        "cells": int(len(sus_cells)),
        "radius_voxels": float(expected * proximity_factor),
        "note": "grid-distant vertex pairs closer than radius in 3D (sheet-switch/merger suspects)",
    }

    # --- normal flips ---------------------------------------------------
    dpu = np.gradient(P, axis=1)
    dpv = np.gradient(P, axis=0)
    nrm = np.cross(dpv, dpu)
    length = np.linalg.norm(nrm, axis=2, keepdims=True)
    length[length == 0] = 1.0
    nrm /= length
    dot_u = (nrm[:, 1:] * nrm[:, :-1]).sum(axis=2)[mu]
    dot_v = (nrm[1:, :] * nrm[:-1, :]).sum(axis=2)[mv]
    dots = np.concatenate([dot_u, dot_v])
    if dots.size:
        result["normals"] = {
            "median_adjacent_dot": float(np.median(dots)),
            "flip_fraction": float((dots < 0).mean()),
        }

    return result


def render_defect_map(patch: Patch, metrics: dict[str, Any], out_png: Path) -> None:
    """Write a quick-look PNG: validity, spacing distortion, and z-height."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    P = patch.points().astype(np.float64)
    V = patch.valid & np.isfinite(P).all(axis=-1)
    du = np.linalg.norm(np.diff(P, axis=1), axis=2)
    spacing_img = np.full(V.shape, np.nan)
    spacing_img[:, 1:] = np.where(V[:, 1:] & V[:, :-1], du, np.nan)
    z_img = np.where(V, P[..., 2], np.nan)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    axes[0].imshow(V, cmap="gray", interpolation="nearest")
    axes[0].set_title(f"validity ({metrics.get('valid_fraction', 0):.1%} valid, "
                      f"{metrics.get('holes', {}).get('count', 0)} interior holes)")
    im1 = axes[1].imshow(spacing_img, cmap="magma", interpolation="nearest")
    axes[1].set_title("adjacent-vertex spacing (voxels)")
    fig.colorbar(im1, ax=axes[1], fraction=0.046)
    im2 = axes[2].imshow(z_img, cmap="viridis", interpolation="nearest")
    axes[2].set_title("z height (voxels)")
    fig.colorbar(im2, ax=axes[2], fraction=0.046)
    for ax in axes:
        ax.set_xlabel("grid col")
        ax.set_ylabel("grid row")
    fig.suptitle(str(patch.path.name))
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
