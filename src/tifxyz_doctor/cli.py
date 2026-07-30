"""tifxyz-doctor command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .checks import validate_patch, worst_severity
from .core import find_patches, load_patch
from .repair import repair_bbox
from .report import audit_tree, summarize_markdown, write_csv

SEV_ICON = {"error": "✗", "warning": "!", "info": "·"}


def _print_findings(path: Path, findings, *, verbose: bool) -> None:
    shown = [f for f in findings if verbose or f["severity"] != "info"]
    status = worst_severity(findings)
    print(f"[{status:>7}] {path}")
    for f in shown:
        print(f"    {SEV_ICON[f['severity']]} {f['check']}: {f['message']}")


def cmd_validate(args) -> int:
    exit_code = 0
    results = []
    for target in args.paths:
        for p in find_patches(Path(target)):
            patch = load_patch(p)
            findings = validate_patch(patch)
            results.append({"path": str(p), "status": worst_severity(findings), "findings": findings})
            if any(f["severity"] == "error" for f in findings):
                exit_code = 1
            if not args.json:
                _print_findings(p, findings, verbose=args.verbose)
    if args.json:
        print(json.dumps(results, indent=2))
    return exit_code


def cmd_fix(args) -> int:
    n_fixed = 0
    for target in args.paths:
        for p in find_patches(Path(target)):
            patch = load_patch(p)
            change = repair_bbox(
                patch,
                dry_run=args.dry_run,
                backup=not args.no_backup,
                strip=args.strip_bbox,
            )
            if change:
                n_fixed += 1
                print(f"{p}: {change}")
    verb = "would fix" if args.dry_run else "fixed"
    print(f"\n{verb} {n_fixed} patch(es)")
    return 0


def cmd_report(args) -> int:
    root = Path(args.root)
    print(f"scanning {root} ...", file=sys.stderr)
    results = audit_tree(root, workers=args.workers)
    if not results:
        print("no tifxyz patches found", file=sys.stderr)
        return 2
    if args.csv:
        write_csv(results, Path(args.csv))
        print(f"wrote {args.csv}", file=sys.stderr)
    text = summarize_markdown(results, Path(args.out) if args.out else None)
    print(text)
    n_err = sum(1 for r in results if r["status"] == "error")
    return 1 if n_err else 0


def cmd_inspect(args) -> int:
    try:
        from .deep import inspect_patch, render_defect_map
    except ImportError as e:
        print(f"inspect requires the [deep] extra (scipy, matplotlib): {e}", file=sys.stderr)
        return 2
    exit_code = 0
    for target in args.paths:
        for p in find_patches(Path(target)):
            patch = load_patch(p)
            metrics = inspect_patch(patch)
            print(f"== {p}")
            print(json.dumps(metrics, indent=2))
            if args.png_dir:
                out_dir = Path(args.png_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                png = out_dir / (p.name + ".png")
                render_defect_map(patch, metrics, png)
                print(f"   wrote {png}", file=sys.stderr)
    return exit_code


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="tifxyz-doctor",
        description="Validate, audit, and repair tifxyz surface-mesh patches "
        "(Vesuvius Challenge / VC3D format).",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="command", required=True)

    p_val = sub.add_parser("validate", help="validate one or more patches (or trees of patches)")
    p_val.add_argument("paths", nargs="+")
    p_val.add_argument("--json", action="store_true", help="machine-readable output")
    p_val.add_argument("-v", "--verbose", action="store_true", help="also show info-level findings")
    p_val.set_defaults(func=cmd_validate)

    p_fix = sub.add_parser("fix", help="repair stale/malformed bboxes in meta.json (villa #1272)")
    p_fix.add_argument("paths", nargs="+")
    p_fix.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
    p_fix.add_argument("--no-backup", action="store_true", help="skip writing meta.json.bak")
    p_fix.add_argument(
        "--strip-bbox",
        action="store_true",
        help="remove the bbox field instead of recomputing it (mirrors vc_tifxyz_trim)",
    )
    p_fix.set_defaults(func=cmd_fix)

    p_rep = sub.add_parser("report", help="audit a whole tree of patches in parallel")
    p_rep.add_argument("root")
    p_rep.add_argument("--csv", help="write per-finding CSV here")
    p_rep.add_argument("--out", help="write Markdown summary here (also printed)")
    p_rep.add_argument("--workers", type=int, default=8)
    p_rep.set_defaults(func=cmd_report)

    p_ins = sub.add_parser(
        "inspect", help="deep geometry checks: holes, spacing distortion, sheet-switch suspects, normal flips"
    )
    p_ins.add_argument("paths", nargs="+")
    p_ins.add_argument("--png-dir", help="write per-patch defect-map PNGs into this directory")
    p_ins.set_defaults(func=cmd_inspect)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
