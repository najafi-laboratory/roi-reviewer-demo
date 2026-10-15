#!/usr/bin/env python3
"""Convert segmentation output from any package into the reviewer's input layout.

Reads whatever you have (a dense label mask or a sparse component matrix, a
trace matrix, optionally inferred spikes and a field-of-view image), checks the
pieces agree, and writes a directory the generator can read directly.

    python scripts/make_standard_inputs.py \\
        --masks  segmentation/cell_masks.npy \\
        --traces segmentation/traces.npy \\
        --spikes segmentation/deconvolved.npy \\
        --fov    segmentation/mean_image.npy \\
        --out    data/my_session

The one thing this cannot infer is whether mask label k corresponds to trace
row k-1. If your segmentation package numbers masks in a different order than
it writes traces, pass --row-order with a file of ROI indices giving, for each
trace row, the mask label it belongs to; the masks are relabeled to match.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def load_any(path: Path) -> np.ndarray:
    """Load .npy, .npz (first array), or .csv into an ndarray."""
    if path.suffix == ".npy":
        return np.load(path, allow_pickle=False)
    if path.suffix == ".npz":
        with np.load(path, allow_pickle=False) as handle:
            keys = list(handle.keys())
            if len(keys) != 1:
                raise SystemExit(f"{path} holds {len(keys)} arrays ({keys}); extract one first")
            return handle[keys[0]]
    if path.suffix in (".csv", ".txt"):
        return np.loadtxt(path, delimiter="," if path.suffix == ".csv" else None)
    raise SystemExit(f"unsupported file type: {path}")


def as_trace_matrix(arr: np.ndarray, n_rois: int, label: str) -> np.ndarray:
    """Return (n_rois, n_frames) float32, C-ordered, transposing if needed."""
    if arr.ndim != 2:
        raise SystemExit(f"{label} is {arr.ndim}-D; expected 2-D")
    if arr.shape[0] != n_rois and arr.shape[1] == n_rois:
        print(f"  {label}: transposing {arr.shape} to match {n_rois} ROIs")
        arr = arr.T
    if arr.shape[0] != n_rois:
        raise SystemExit(f"{label} has shape {arr.shape}; neither axis matches {n_rois} ROIs")
    return np.ascontiguousarray(arr, dtype=np.float32)


def relabel_mask(mask: np.ndarray, row_order: np.ndarray) -> np.ndarray:
    """Renumber mask labels so that label i+1 is the mask for trace row i."""
    out = np.zeros_like(mask, dtype=np.int32)
    for row, original_label in enumerate(row_order):
        out[mask == original_label] = row + 1
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--masks", type=Path, required=True,
                        help="dense 2-D integer label image (.npy/.npz/.csv)")
    parser.add_argument("--traces", type=Path, required=True,
                        help="raw fluorescence, ROIs x frames or frames x ROIs")
    parser.add_argument("--neuropil", type=Path, default=None,
                        help="optional neuropil traces, same shape as --traces")
    parser.add_argument("--spikes", type=Path, default=None,
                        help="optional inferred spike amplitudes, same shape as --traces")
    parser.add_argument("--dff", type=Path, default=None,
                        help="optional precomputed dF/F; omit to let the generator compute it")
    parser.add_argument("--fov", type=Path, default=None,
                        help="optional functional mean image (Ly, Lx)")
    parser.add_argument("--cell-types", type=Path, default=None,
                        help="optional per-ROI codes: -1 excitatory, 0 unsure, 1 inhibitory, NaN unknown")
    parser.add_argument("--row-order", type=Path, default=None,
                        help="optional: mask label belonging to each trace row, in row order")
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"writing {args.out}")

    mask = load_any(args.masks)
    if mask.ndim != 2:
        raise SystemExit(f"--masks is {mask.ndim}-D; a dense label image must be 2-D")
    mask = mask.astype(np.int32, copy=False)
    labels = np.unique(mask)
    labels = labels[labels > 0]
    n_rois = int(labels.size)
    print(f"  masks: {n_rois} ROIs in a {mask.shape[0]}x{mask.shape[1]} image")

    if args.row_order is not None:
        row_order = load_any(args.row_order).astype(np.int64).ravel()
        if row_order.size != n_rois:
            raise SystemExit(f"--row-order has {row_order.size} entries but the mask has {n_rois} ROIs")
        missing = set(row_order.tolist()) ^ set(labels.tolist())
        if missing:
            raise SystemExit(f"--row-order does not name the same labels as the mask: {sorted(missing)[:8]}")
        mask = relabel_mask(mask, row_order)
        print("  masks: relabeled into trace row order")
    elif not np.array_equal(labels, np.arange(1, n_rois + 1)):
        mask = relabel_mask(mask, labels)
        print(f"  masks: labels were not a gap-free 1..{n_rois} run; compacted in ascending order")

    np.save(args.out / "roi_mask.npy", mask)

    traces = as_trace_matrix(load_any(args.traces), n_rois, "traces")
    np.save(args.out / "F.npy", traces)
    n_frames = traces.shape[1]
    print(f"  traces: {n_rois} x {n_frames} float32")

    if args.neuropil is not None:
        np.save(args.out / "Fneu.npy", as_trace_matrix(load_any(args.neuropil), n_rois, "neuropil"))
    else:
        np.save(args.out / "Fneu.npy", np.zeros_like(traces))
        print("  neuropil: not supplied, written as zeros")

    for src, name, label in ((args.dff, "dff.npy", "dF/F"),
                             (args.spikes, "spikes.npy", "inferred spikes")):
        if src is None:
            continue
        arr = as_trace_matrix(load_any(src), n_rois, label)
        if arr.shape[1] != n_frames:
            raise SystemExit(f"{label} has {arr.shape[1]} frames but traces have {n_frames}")
        np.save(args.out / name, arr)
        print(f"  {label}: {arr.shape[0]} x {arr.shape[1]} float32")

    if args.fov is not None:
        fov = load_any(args.fov)
        if fov.ndim != 2:
            raise SystemExit(f"--fov is {fov.ndim}-D; expected a 2-D image")
        if fov.shape != mask.shape:
            raise SystemExit(f"--fov shape {fov.shape} does not match the mask {mask.shape}")
        np.save(args.out / "mean_func.npy", np.ascontiguousarray(fov, dtype=np.float32))
    else:
        print("  field of view: not supplied; the reviewer will use a blank background")

    if args.cell_types is not None:
        codes = load_any(args.cell_types).ravel()
        if codes.size != n_rois:
            raise SystemExit(f"--cell-types has {codes.size} entries but the mask has {n_rois} ROIs")
        np.save(args.out / "roi_cell_type_labels.npy", codes.astype(np.float32))

    (args.out / "external_roi_metadata.json").write_text(
        json.dumps({"image_shape": list(mask.shape), "flatten_order": "F"}, indent=2) + "\n"
    )

    print("\nnow check it:")
    print(f"  python scripts/validate_inputs.py {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
