#!/usr/bin/env python3
"""Check a directory against the reviewer's documented input contract.

The reviewer needs exactly two correspondences to hold:

    ROI row i  ->  pixels (or weights) in the displayed FOV coordinate frame
    ROI row i  ->  fluorescence trace row i

Most failures are violations of the second one, and they are silent: a mask
whose label order does not match the trace row order produces a viewer in which
every mask is paired with the wrong trace, and nothing in the interface flags
it. This script checks what can be checked mechanically and names what cannot.

    python scripts/validate_inputs.py /path/to/session

Exit status is 0 when no errors were found, 1 otherwise. Warnings do not
affect exit status.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

GEOMETRY_DENSE = ["roi_mask.npy", "roi_masks.npy", "label_mask.npy", "masks.npy"]
GEOMETRY_SPARSE = ["spatial_components.npz", "roi_spatial_components.npz", "A.npz"]
GEOMETRY_STAT = ["stat.npy"]
TRACES_RAW = ["F.npy", "fluo.npy"]
TRACES_NEUROPIL = ["Fneu.npy", "neuropil.npy"]
FOV_FUNCTIONAL = ["mean_func.npy", "meanImg.npy", "mean_green.npy", "functional_mean.npy"]
DFF_LIKE = ["dff.npy", "session_dff.npy"]
SPIKES_LIKE = ["spikes.npy", "session_inferred_spikes.npy", "oasis_spikes.npy"]


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.facts: list[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def fact(self, msg: str) -> None:
        self.facts.append(msg)

    def render(self) -> str:
        out = []
        for line in self.facts:
            out.append(f"  {line}")
        for line in self.warnings:
            out.append(f"  WARNING  {line}")
        for line in self.errors:
            out.append(f"  ERROR    {line}")
        if not self.errors:
            out.append("  no errors")
        return "\n".join(out)


def _first_present(root: Path, names: list[str]) -> Path | None:
    for name in names:
        candidate = root / name
        if candidate.exists():
            return candidate
    return None


class ArrayUnreadable(Exception):
    pass


def _load_array(path: Path) -> np.ndarray:
    try:
        return np.load(path, mmap_mode="r", allow_pickle=path.name == "stat.npy")
    except Exception as exc:  # unreadable, truncated, or not a .npy at all
        raise ArrayUnreadable(f"{path.name} could not be read as a NumPy array: {exc}") from exc


def _check_trace_array(path: Path, label: str, rep: Report) -> np.ndarray | None:
    arr = _load_array(path)
    if arr.ndim != 2:
        rep.error(f"{label} ({path.name}) is {arr.ndim}-D; the reviewer expects (n_rois, n_frames)")
        return None
    n_rois, n_frames = arr.shape
    rep.fact(f"{label:<16} {path.name:<28} {n_rois} ROIs x {n_frames} frames, {arr.dtype}")
    if arr.dtype not in (np.float32, np.float64):
        rep.error(f"{label} dtype is {arr.dtype}; the browser reads float32 or float64")
    if n_rois > n_frames:
        rep.warn(
            f"{label} has more rows ({n_rois}) than columns ({n_frames}). "
            "If this array is frames-by-ROIs it is transposed."
        )
    # C-ordering matters: each row must be a contiguous time series.
    if not np.asarray(arr).flags["C_CONTIGUOUS"]:
        rep.error(
            f"{label} is not C-ordered. Rewrite it with "
            f"np.save(path, np.ascontiguousarray(arr, dtype=np.float32))"
        )
    return arr


def validate(root: Path) -> Report:
    rep = Report()
    if not root.is_dir():
        rep.error(f"{root} is not a directory")
        return rep

    # --- geometry -----------------------------------------------------------
    dense = _first_present(root, GEOMETRY_DENSE)
    sparse = _first_present(root, GEOMETRY_SPARSE)
    stat = _first_present(root, GEOMETRY_STAT)
    found = [p for p in (dense, sparse, stat) if p is not None]
    if not found:
        rep.error(
            "no ROI geometry file. Supply exactly one of: "
            f"{', '.join(GEOMETRY_DENSE + GEOMETRY_SPARSE + GEOMETRY_STAT)}"
        )
    elif len(found) > 1:
        rep.error(
            "more than one ROI geometry file present "
            f"({', '.join(p.name for p in found)}); supply exactly one"
        )

    n_rois_geometry: int | None = None
    if dense is not None and len(found) == 1:
        mask = _load_array(dense)
        if mask.ndim != 2:
            rep.error(f"{dense.name} is {mask.ndim}-D; a dense label mask must be 2-D")
        else:
            labels = np.unique(np.asarray(mask))
            positive = labels[labels > 0]
            n_rois_geometry = int(positive.size)
            rep.fact(
                f"{'geometry':<16} {dense.name:<28} {n_rois_geometry} labels, "
                f"image {mask.shape[0]}x{mask.shape[1]}"
            )
            expected = np.arange(1, n_rois_geometry + 1)
            if n_rois_geometry and not np.array_equal(positive, expected):
                rep.warn(
                    f"{dense.name} labels are not a gap-free 1..{n_rois_geometry} run "
                    f"(min {int(positive.min())}, max {int(positive.max())}). Labels convert "
                    "in ascending order, so gaps shift every later ROI relative to the traces."
                )

    if sparse is not None and len(found) == 1:
        try:
            from scipy import sparse as sp
        except ImportError:
            rep.warn(f"scipy not installed; cannot inspect {sparse.name}")
        else:
            A = sp.load_npz(sparse)
            n_rois_geometry = int(min(A.shape))
            rep.fact(f"{'geometry':<16} {sparse.name:<28} sparse {A.shape[0]}x{A.shape[1]}")
            meta_path = root / "external_roi_metadata.json"
            fov = _first_present(root, FOV_FUNCTIONAL)
            if not meta_path.exists() and fov is None:
                rep.error(
                    "sparse components need either a functional image or "
                    'external_roi_metadata.json with {"image_shape": [Ly, Lx], "flatten_order": "F"}'
                )
            elif meta_path.exists():
                meta = json.loads(meta_path.read_text())
                if "image_shape" not in meta:
                    rep.error("external_roi_metadata.json has no image_shape")
                order = meta.get("flatten_order", "F")
                if order not in ("C", "F"):
                    rep.error(f'flatten_order must be "C" or "F", got {order!r}')
                else:
                    rep.fact(
                        f"{'metadata':<16} {'external_roi_metadata.json':<28} "
                        f"image_shape {meta.get('image_shape')}, flatten_order {order}"
                    )

    if stat is not None and len(found) == 1:
        st = np.load(stat, allow_pickle=True)
        n_rois_geometry = int(len(st))
        rep.fact(f"{'geometry':<16} {stat.name:<28} {n_rois_geometry} ROIs")
        missing = [k for k in ("ypix", "xpix") if n_rois_geometry and k not in st[0]]
        if missing:
            rep.error(f"stat.npy entries lack {', '.join(missing)}")

    # --- traces -------------------------------------------------------------
    raw = _first_present(root, TRACES_RAW)
    if raw is None:
        rep.error(f"no raw fluorescence array; expected one of {', '.join(TRACES_RAW)}")
        arr_raw = None
    else:
        arr_raw = _check_trace_array(raw, "fluorescence", rep)

    neuropil = _first_present(root, TRACES_NEUROPIL)
    if neuropil is None:
        rep.warn("no neuropil array; neuropil will be treated as zero")
    else:
        arr_neu = _check_trace_array(neuropil, "neuropil", rep)
        if arr_raw is not None and arr_neu is not None and arr_raw.shape != arr_neu.shape:
            rep.error(
                f"neuropil shape {arr_neu.shape} does not match fluorescence {arr_raw.shape}"
            )

    dff = _first_present(root, DFF_LIKE)
    arr_dff = _check_trace_array(dff, "dF/F", rep) if dff is not None else None
    spikes = _first_present(root, SPIKES_LIKE)
    arr_spk = _check_trace_array(spikes, "inferred spikes", rep) if spikes is not None else None
    if arr_dff is not None and arr_spk is not None and arr_dff.shape != arr_spk.shape:
        rep.error(
            f"inferred-spike shape {arr_spk.shape} does not match dF/F {arr_dff.shape}; "
            "the two must agree row for row"
        )
    if arr_spk is not None and float(np.asarray(arr_spk[: min(64, arr_spk.shape[0])]).min()) < 0:
        rep.warn(
            "inferred spikes contain negative values; the reviewer treats amplitudes as "
            "non-negative, with larger meaning stronger evidence"
        )

    # --- the correspondence that actually bites -----------------------------
    for arr, name in ((arr_raw, raw), (arr_dff, dff), (arr_spk, spikes)):
        if arr is not None and n_rois_geometry is not None and arr.shape[0] != n_rois_geometry:
            rep.error(
                f"{name.name} has {arr.shape[0]} rows but the geometry defines "
                f"{n_rois_geometry} ROIs"
            )

    # --- field of view ------------------------------------------------------
    if _first_present(root, FOV_FUNCTIONAL) is None:
        rep.warn(
            "no functional mean image; the reviewer will draw masks on a blank background. "
            "Seeing outlines land on visible cells is the only available check that masks "
            "and imaging share a coordinate frame."
        )

    for filename, dataset, label in (("dff.h5", "dff", "dF/F"), ("spikes.h5", "spikes", "inferred spikes")):
        path = root / filename
        stray = [p for p in (root / (filename[:-3] + ".npy"), root / "spks.npy") if p.exists()]
        if path.exists():
            try:
                import h5py

                with h5py.File(path, "r") as handle:
                    if dataset not in handle:
                        rep.error(filename + " has no " + dataset + " dataset, so the reviewer will ignore it")
                    else:
                        shape = handle[dataset].shape
                        rep.fact(filename + " carries " + dataset + " of shape " + str(shape))
                        if n_rois_geometry is not None and shape[0] != n_rois_geometry:
                            rep.error(filename + " has " + str(shape[0]) + " rows but the masks define "
                                      + str(n_rois_geometry) + " ROIs")
            except ImportError:
                rep.fact("h5py not installed, so " + filename + " was not inspected")
        elif stray:
            rep.error("found " + ", ".join(p.name for p in stray) + " but no " + filename
                      + ". The reviewer reads " + label + " only from " + filename + " (dataset "
                      + dataset + ") and will silently ignore a .npy. Convert with"
                      + " scripts/make_standard_inputs.py")
        elif label == "inferred spikes":
            rep.fact("no inferred spikes supplied; spike metrics and overlays will be unavailable")
    if n_rois_geometry is not None and arr_raw is not None:
        rep.fact(
            "row order between geometry and traces cannot be verified mechanically; "
            "spot-check a known-active ROI in the reviewer before trusting the session"
        )
    return rep


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("session", type=Path, help="directory of standard-format inputs")
    args = parser.parse_args()
    try:
        report = validate(args.session)
    except ArrayUnreadable as exc:
        print(f"{args.session}\n  ERROR {exc}")
        return 1
    print(f"{args.session}")
    print(report.render())
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
