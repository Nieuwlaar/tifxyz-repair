import json
from pathlib import Path

import numpy as np
import pytest
import tifffile

from tifxyz_doctor.checks import validate_patch, worst_severity
from tifxyz_doctor.core import compute_bbox, find_patches, load_patch
from tifxyz_doctor.repair import repair_bbox


def make_patch(
    tmp: Path,
    name: str = "patch",
    shape=(20, 30),
    origin=(100.0, 200.0, 300.0),
    spacing=20.0,
    invalid_cells=(),
    bbox="auto",
    scale=(0.05, 0.05),
    extra_meta=None,
):
    """Write a synthetic planar tifxyz patch and return its path."""
    h, w = shape
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    x = origin[0] + xs * spacing
    y = origin[1] + ys * spacing
    z = np.full(shape, origin[2], dtype=np.float32)
    for r, c in invalid_cells:
        x[r, c] = y[r, c] = z[r, c] = -1.0
    d = tmp / name
    d.mkdir(parents=True)
    tifffile.imwrite(d / "x.tif", x.astype(np.float32))
    tifffile.imwrite(d / "y.tif", y.astype(np.float32))
    tifffile.imwrite(d / "z.tif", z.astype(np.float32))
    meta = {"format": "tifxyz", "scale": list(scale), "type": "seg", "uuid": name}
    if bbox == "auto":
        valid = x != -1
        meta["bbox"] = [
            [float(a[valid].min()) for a in (x, y, z)],
            [float(a[valid].max()) for a in (x, y, z)],
        ]
    elif bbox is not None:
        meta["bbox"] = bbox
    if extra_meta:
        meta.update(extra_meta)
    (d / "meta.json").write_text(json.dumps(meta, indent=4) + "\n")
    return d


def get(findings, check):
    return [f for f in findings if f["check"] == check]


class TestClean:
    def test_clean_patch_validates_ok(self, tmp_path):
        p = load_patch(make_patch(tmp_path))
        findings = validate_patch(p)
        assert worst_severity(findings) == "info"  # only the valid-fraction info line
        assert not get(findings, "bbox-stale")

    def test_bbox_matches_cpp_semantics_with_invalid_cells(self, tmp_path):
        # invalid cells must not influence the bbox
        d = make_patch(tmp_path, invalid_cells=[(0, 0), (19, 29)], bbox=None)
        p = load_patch(d)
        low, high = compute_bbox(p)
        # min x is still 100.0: (0,0) is invalid but (1,0) keeps x=100.0
        assert low[0] == pytest.approx(float(p.x[p.valid].min()))
        assert low[0] == pytest.approx(100.0)
        assert high[0] == pytest.approx(float(p.x[p.valid].max()))
        assert high[2] == pytest.approx(300.0)


class TestStaleBbox:
    def test_stale_bbox_detected(self, tmp_path):
        stale = [[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]]  # nowhere near the true extent
        d = make_patch(tmp_path, bbox=stale)
        findings = validate_patch(load_patch(d))
        f = get(findings, "bbox-stale")
        assert len(f) == 1
        assert f[0]["severity"] == "error"
        assert f[0]["frac_outside"] > 0.9
        assert f[0]["max_drift"] > 100

    def test_fix_recomputes_bbox(self, tmp_path):
        stale = [[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]]
        d = make_patch(tmp_path, bbox=stale)
        p = load_patch(d)
        change = repair_bbox(p)
        assert change and "recompute" in change
        meta = json.loads((d / "meta.json").read_text())
        low, high = meta["bbox"]
        assert low[0] == pytest.approx(100.0)
        assert high[0] == pytest.approx(100.0 + 29 * 20.0)
        assert (d / "meta.json.bak").exists()
        # now clean
        assert not get(validate_patch(load_patch(d)), "bbox-stale")
        # idempotent
        assert repair_bbox(load_patch(d)) is None

    def test_fix_dry_run_writes_nothing(self, tmp_path):
        stale = [[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]]
        d = make_patch(tmp_path, bbox=stale)
        before = (d / "meta.json").read_text()
        change = repair_bbox(load_patch(d), dry_run=True)
        assert change.startswith("[dry-run]")
        assert (d / "meta.json").read_text() == before

    def test_strip_bbox(self, tmp_path):
        d = make_patch(tmp_path)
        repair_bbox(load_patch(d), strip=True)
        assert "bbox" not in json.loads((d / "meta.json").read_text())

    def test_fix_preserves_other_fields(self, tmp_path):
        stale = [[0.0, 0.0, 0.0], [10.0, 10.0, 10.0]]
        d = make_patch(tmp_path, bbox=stale, extra_meta={"custom_field": {"a": 1}})
        repair_bbox(load_patch(d))
        meta = json.loads((d / "meta.json").read_text())
        assert meta["custom_field"] == {"a": 1}
        assert meta["uuid"] == "patch"

    def test_missing_bbox_is_info_not_error(self, tmp_path):
        d = make_patch(tmp_path, bbox=None)
        findings = validate_patch(load_patch(d))
        f = get(findings, "bbox-missing")
        assert len(f) == 1 and f[0]["severity"] == "info"
        # fix must NOT invent a bbox when none was stored
        assert repair_bbox(load_patch(d)) is None


class TestDefects:
    def test_nan_vertices_flagged(self, tmp_path):
        d = make_patch(tmp_path)
        z = tifffile.imread(d / "z.tif")
        z[5, 5] = np.nan
        tifffile.imwrite(d / "z.tif", z)
        findings = validate_patch(load_patch(d))
        assert get(findings, "nan-vertices")

    def test_partial_sentinel_flagged(self, tmp_path):
        d = make_patch(tmp_path)
        y = tifffile.imread(d / "y.tif")
        y[3, 3] = -1.0  # x stays valid → inconsistent
        tifffile.imwrite(d / "y.tif", y)
        findings = validate_patch(load_patch(d))
        assert get(findings, "partial-sentinel")

    def test_all_invalid_is_error(self, tmp_path):
        h, w = 4, 4
        d = make_patch(tmp_path, shape=(h, w), invalid_cells=[(r, c) for r in range(h) for c in range(w)], bbox=None)
        findings = validate_patch(load_patch(d))
        assert get(findings, "no-valid-vertices")

    def test_shape_mismatch_is_error(self, tmp_path):
        d = make_patch(tmp_path)
        tifffile.imwrite(d / "y.tif", np.zeros((5, 5), dtype=np.float32))
        findings = validate_patch(load_patch(d))
        assert get(findings, "grid-shape")

    def test_bad_scale_is_error(self, tmp_path):
        d = make_patch(tmp_path, scale=(0.0, 0.05))
        findings = validate_patch(load_patch(d))
        assert get(findings, "meta-scale")

    def test_zero_voxelsize_is_error(self, tmp_path):
        d = make_patch(tmp_path, extra_meta={"voxelsize": 0})
        findings = validate_patch(load_patch(d))
        assert get(findings, "meta-voxelsize")

    def test_missing_meta_is_error(self, tmp_path):
        d = make_patch(tmp_path)
        (d / "meta.json").unlink()
        findings = validate_patch(load_patch(d))
        assert get(findings, "meta-parse")

    def test_corrupt_tif_is_error_not_crash(self, tmp_path):
        d = make_patch(tmp_path)
        (d / "x.tif").write_bytes(b"not a tiff")
        findings = validate_patch(load_patch(d))
        assert get(findings, "tif-read")


class TestDiscovery:
    def test_find_patches_nested(self, tmp_path):
        make_patch(tmp_path / "a", name="p1")
        make_patch(tmp_path / "b" / "c", name="p2")
        found = find_patches(tmp_path)
        assert len(found) == 2

    def test_find_patches_direct(self, tmp_path):
        d = make_patch(tmp_path)
        assert find_patches(d) == [d]


class TestDeep:
    def test_inspect_clean_patch(self, tmp_path):
        pytest.importorskip("scipy")
        from tifxyz_doctor.deep import inspect_patch

        d = make_patch(tmp_path, shape=(30, 30))
        m = inspect_patch(load_patch(d))
        assert m["holes"]["count"] == 0
        assert m["spacing"]["median"] == pytest.approx(20.0)
        assert m["self_proximity"]["pairs"] == 0

    def test_inspect_detects_interior_hole(self, tmp_path):
        pytest.importorskip("scipy")
        from tifxyz_doctor.deep import inspect_patch

        d = make_patch(tmp_path, shape=(30, 30), invalid_cells=[(10, 10), (10, 11)])
        m = inspect_patch(load_patch(d))
        assert m["holes"]["count"] == 1
        assert m["holes"]["cells"] == 2

    def test_inspect_detects_sheet_switch(self, tmp_path):
        pytest.importorskip("scipy")
        from tifxyz_doctor.deep import inspect_patch

        # Fold the right half back over the left: distant columns land at
        # identical 3D positions — the sheet-switch signature.
        d = make_patch(tmp_path, shape=(20, 40))
        x = tifffile.imread(d / "x.tif")
        x[:, 20:] = x[:, 19::-1]
        tifffile.imwrite(d / "x.tif", x.astype(np.float32))
        m = inspect_patch(load_patch(d))
        assert m["self_proximity"]["pairs"] > 0


class TestCli:
    def test_cli_validate_exit_codes(self, tmp_path, capsys):
        from tifxyz_doctor.cli import main

        clean = make_patch(tmp_path / "clean")
        assert main(["validate", str(clean)]) == 0
        stale = make_patch(tmp_path / "stale", bbox=[[0, 0, 0], [1, 1, 1]])
        assert main(["validate", str(stale)]) == 1

    def test_cli_report(self, tmp_path, capsys):
        from tifxyz_doctor.cli import main

        make_patch(tmp_path / "t" / "a", name="p1")
        make_patch(tmp_path / "t" / "b", name="p2", bbox=[[0, 0, 0], [1, 1, 1]])
        csv_out = tmp_path / "audit.csv"
        rc = main(["report", str(tmp_path / "t"), "--csv", str(csv_out), "--workers", "1"])
        assert rc == 1  # one patch has an error
        out = capsys.readouterr().out
        assert "Stale bboxes" in out
        assert csv_out.exists()

    def test_cli_json_output(self, tmp_path, capsys):
        from tifxyz_doctor.cli import main

        clean = make_patch(tmp_path)
        assert main(["validate", str(clean), "--json"]) == 0
        data = json.loads(capsys.readouterr().out)
        assert data[0]["status"] in ("ok", "info")
