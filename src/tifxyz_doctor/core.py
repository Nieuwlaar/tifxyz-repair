"""Core tifxyz reading and bbox computation.

Semantics deliberately mirror VC3D's C++ implementation
(villa/volume-cartographer/core/src/QuadSurface.cpp):

- A tifxyz patch is a directory with ``x.tif``, ``y.tif``, ``z.tif``
  (float32 2D grids of equal shape; cell (row, col) holds one 3D vertex)
  and a ``meta.json`` sidecar.
- A vertex is *invalid* when its **x** coordinate equals ``-1``
  (``QuadSurface::bbox()`` tests only channel 0, see QuadSurface.cpp,
  ``Rect3D QuadSurface::bbox()``). y/z are ignored for validity.
- ``meta.json``'s ``bbox`` is ``[[min_x, min_y, min_z], [max_x, max_y, max_z]]``
  computed over valid vertices only.
- An optional ``mask.tif`` sidecar may also mark missing cells (nonzero =
  valid); it is read when present but validity for bbox purposes follows the
  C++ ``x == -1`` rule.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np
import tifffile

COORD_FILES = ("x.tif", "y.tif", "z.tif")
INVALID_SENTINEL = -1.0


def is_tifxyz_dir(path: Path) -> bool:
    return all((path / f).is_file() for f in COORD_FILES)


def find_patches(root: Path) -> list[Path]:
    """Find all tifxyz directories under ``root`` (including root itself)."""
    root = Path(root)
    if is_tifxyz_dir(root):
        return [root]
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        names = set(filenames)
        if all(f in names for f in COORD_FILES):
            found.append(Path(dirpath))
            dirnames.clear()  # tifxyz dirs don't nest
    return sorted(found)


@dataclass
class Patch:
    """A loaded tifxyz patch."""

    path: Path
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    meta: Optional[dict] = None
    meta_error: Optional[str] = None
    mask: Optional[np.ndarray] = None
    read_errors: dict[str, str] = field(default_factory=dict)

    @property
    def shape(self) -> tuple[int, int]:
        return self.x.shape

    @property
    def valid(self) -> np.ndarray:
        """Validity mask under VC3D semantics: x != -1."""
        return self.x != INVALID_SENTINEL

    def points(self) -> np.ndarray:
        """(H, W, 3) float32 array in (x, y, z) channel order."""
        return np.stack([self.x, self.y, self.z], axis=-1)


def load_patch(path: Path, *, load_mask: bool = True) -> Patch:
    """Load a tifxyz directory. Coordinate read errors are captured
    per-file in ``read_errors`` (with a zero-size placeholder array) so
    validation can report them instead of crashing."""
    path = Path(path)
    arrays: dict[str, np.ndarray] = {}
    read_errors: dict[str, str] = {}
    for fname in COORD_FILES:
        key = fname[0]
        try:
            arrays[key] = tifffile.imread(path / fname)
        except Exception as e:  # noqa: BLE001 - report, don't crash
            arrays[key] = np.zeros((0, 0), dtype=np.float32)
            read_errors[fname] = f"{type(e).__name__}: {e}"

    meta: Optional[dict] = None
    meta_error: Optional[str] = None
    meta_path = path / "meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text())
        except Exception as e:  # noqa: BLE001
            meta_error = f"{type(e).__name__}: {e}"
    else:
        meta_error = "meta.json not found"

    mask = None
    if load_mask and (path / "mask.tif").is_file():
        try:
            mask = tifffile.imread(path / "mask.tif")
        except Exception as e:  # noqa: BLE001
            read_errors["mask.tif"] = f"{type(e).__name__}: {e}"

    return Patch(
        path=path,
        x=arrays["x"],
        y=arrays["y"],
        z=arrays["z"],
        meta=meta,
        meta_error=meta_error,
        mask=mask,
        read_errors=read_errors,
    )


def compute_bbox(patch: Patch) -> Optional[tuple[list[float], list[float]]]:
    """Recompute the true bbox over valid vertices, mirroring
    ``QuadSurface::bbox()``. Returns ``(low, high)`` in (x, y, z) order,
    or ``None`` when the patch has no valid vertices.

    NaNs are excluded from min/max so a few corrupt vertices cannot
    poison the box (they are reported separately by the nan check).
    """
    valid = patch.valid
    if not valid.any():
        return None
    low, high = [], []
    for arr in (patch.x, patch.y, patch.z):
        vals = arr[valid]
        finite = vals[np.isfinite(vals)]
        if finite.size == 0:
            return None
        low.append(float(finite.min()))
        high.append(float(finite.max()))
    return low, high


def parse_meta_bbox(meta: dict) -> Optional[tuple[list[float], list[float]]]:
    """Parse meta.json's bbox field into (low, high), or None if absent
    or malformed (malformedness is reported by the bbox check)."""
    raw = meta.get("bbox")
    if raw is None:
        return None
    try:
        low = [float(v) for v in raw[0]]
        high = [float(v) for v in raw[1]]
        if len(low) != 3 or len(high) != 3:
            return None
        if any(not math.isfinite(v) for v in low + high):
            return None
        return low, high
    except (TypeError, ValueError, IndexError, KeyError):
        return None
