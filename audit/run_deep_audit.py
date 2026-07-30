"""Corpus-wide deep geometry audit (produces audit/deep_audit.md + .jsonl)."""

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from tifxyz_doctor.core import find_patches, load_patch
from tifxyz_doctor.deep import inspect_patch

ROOT = Path(sys.argv[1])
OUT = Path(__file__).parent


def one(path):
    try:
        m = inspect_patch(load_patch(path))
        m["path"] = str(path)
        return m
    except Exception as e:  # noqa: BLE001
        return {"path": str(path), "error": f"{type(e).__name__}: {e}"}


def main():
    patches = find_patches(ROOT)
    print(f"deep-auditing {len(patches)} patches", flush=True)
    results = []
    with ProcessPoolExecutor(max_workers=14) as pool:
        for i, m in enumerate(pool.map(one, patches, chunksize=8)):
            results.append(m)
            if i % 500 == 0:
                print(f"{i}/{len(patches)}", flush=True)

    with open(OUT / "deep_audit.jsonl", "w") as fh:
        for m in results:
            fh.write(json.dumps(m) + "\n")

    ok = [m for m in results if "error" not in m]
    switch = sorted(
        (m for m in ok if m["self_proximity"]["pairs"] > 0),
        key=lambda m: -m["self_proximity"]["pairs"],
    )
    holey = sorted(
        (m for m in ok if m["holes"]["count"] > 0), key=lambda m: -m["holes"]["cells"]
    )
    stretched = sorted(
        (m for m in ok if m.get("spacing", {}).get("stretch_frac", 0) > 0.01),
        key=lambda m: -m["spacing"]["stretch_frac"],
    )
    flipped = sorted(
        (m for m in ok if m.get("normals", {}).get("flip_fraction", 0) > 0.05),
        key=lambda m: -m["normals"]["flip_fraction"],
    )

    def table(rows, cols, fmt):
        lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(fmt(m)) + " |" for m in rows]
        return "\n".join(lines)

    md = [
        "# Deep geometry audit — PHercParis4 spiral-input verified patches",
        "",
        f"Patches inspected: **{len(ok)}** ({len(results) - len(ok)} failed to load)",
        "",
        f"- with **sheet-switch/merger suspects** (grid-distant pairs <0.5 spacing apart in 3D): **{len(switch)}**",
        f"- with **interior holes**: **{len(holey)}**",
        f"- with **>1% stretched edges** (>1.5x expected spacing): **{len(stretched)}**",
        f"- with **>5% normal flips**: **{len(flipped)}**",
        "",
        "## Top sheet-switch suspects",
        "",
        table(
            switch[:20],
            ["suspect pairs", "cells", "patch"],
            lambda m: [
                str(m["self_proximity"]["pairs"]),
                str(m["self_proximity"]["cells"]),
                f"`{Path(m['path']).name}`",
            ],
        ),
        "",
        "## Largest interior holes",
        "",
        table(
            holey[:20],
            ["holes", "total cells", "largest", "patch"],
            lambda m: [
                str(m["holes"]["count"]),
                str(m["holes"]["cells"]),
                str(m["holes"]["largest"]),
                f"`{Path(m['path']).name}`",
            ],
        ),
        "",
    ]
    (OUT / "deep_audit.md").write_text("\n".join(md) + "\n")
    print("done", flush=True)


if __name__ == "__main__":
    main()
