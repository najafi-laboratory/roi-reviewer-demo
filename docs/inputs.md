# Preparing your inputs

The reviewer needs four things: where each ROI is, what its fluorescence did over
time, optionally what a spike-inference method made of that, and optionally what kind
of cell it is. Anything that can express those can be reviewed.

## The documented layout

`scripts/make_standard_inputs.py` writes a directory in this form, and
`scripts/validate_inputs.py` checks one against it.

| File | Meaning |
|---|---|
| `roi_mask.npy` | dense 2-D integer label image; 0 is background, label *k* is ROI row *k−1* |
| `spatial_components.npz` | alternative to the above: sparse `(pixels, n_rois)` component matrix |
| `F.npy`, `Fneu.npy` | raw fluorescence and neuropil, `(n_rois, n_frames)` float32, C-ordered |
| `dff.h5` (dataset `dff`) | optional precomputed dF/F, `(n_rois, n_frames)` float32 |
| `spikes.h5` (dataset `spikes`) | optional inferred spike amplitudes, same shape |
| `mean_func.npy` | optional functional mean image, `(Ly, Lx)` |
| `roi_cell_type_labels.npy` | optional per-ROI codes: −1 excitatory, 0 unsure, 1 inhibitory, NaN unknown |
| `external_roi_metadata.json` | `image_shape` and `flatten_order`, needed for sparse components without an image |

Sparse component matrices from CaImAn-style pipelines are accepted directly; supply
`flatten_order: "F"` in the metadata file unless your pixel indices are row-major.

!!! danger "HDF5 for dF/F and spikes, not .npy"
    The generator reads dF/F and inferred spikes **only** from HDF5, at the dataset
    names above. A `dff.npy` or `spikes.npy` placed beside them is ignored without
    warning, which is why the validator reports one as an error.

    ```python
    import h5py
    import numpy as np

    with h5py.File("dff.h5", "w") as handle:
        handle.create_dataset("dff", data=np.ascontiguousarray(dff, dtype=np.float32))

    with h5py.File("spikes.h5", "w") as handle:
        handle.create_dataset("spikes", data=np.ascontiguousarray(spikes, dtype=np.float32))
    ```

    These are HDF5 on the input side because they are multi-array stage outputs that
    carry companion arrays and file attributes. The `.npy` form appears only on the
    output side, in the sidecars the browser reads, where a header simple enough to
    parse in a few lines of JavaScript is what keeps the reviewer self-contained.

If `dff.h5` is absent the generator computes dF/F from `F.npy` and `Fneu.npy`.
Inferred spikes have no such fallback: without `spikes.h5`, the spike overlay and
every inferred-spike metric are unavailable, and the reviewer says so rather than
showing an empty panel.

## Motion offsets

One value per frame, `shape = (n_frames,)`. The generator reads `xoff` and `yoff` from a
session-level `move_offset.h5`, and otherwise from Suite2p's `ops.npy`. Where the
lengths differ the viewer uses the overlap with the dF/F frame count; where no offsets
exist the motion panels report their absence.

## Cell-type labels

Optional, and independent of the Good/Bad/Unsure review labels. The generator looks
for `suite2p/plane0/roi_cell_type_labels.npy`, then `roi_cell_type_labels.npy` at the
session root, then a `labels` dataset in `masks.h5`. Use one value per ROI:
`1` inhibitory/red, `-1` excitatory/non-red, `0` unsure, `NaN` unavailable.

```python
cell_type_labels = np.full(n_rois, np.nan, dtype=np.float32)
cell_type_labels[red_roi_indices]       =  1
cell_type_labels[non_red_roi_indices]   = -1
cell_type_labels[uncertain_roi_indices] =  0
np.save("roi_cell_type_labels.npy", cell_type_labels)
```

The same labels can be uploaded into an open reviewer with **Upload Custom ROI Metric
or Label**, as a CSV with `cell_type_code,cell_type_label` columns and optionally a
`suite2p_index`, `roi` or `index` column. Without an index column, rows are taken in ROI
order and the file needs exactly one row per ROI.

## ROI model scores

Optional per-ROI classifier output, read from the first of `roi_model_scores.h5`,
`roi_qc_predictions.h5` or `roi_predictions.h5` at the session root.

| Dataset or attribute | Content |
|:---|:---|
| `probability` | float per ROI: the classifier's P(Good) |
| `state` | string per ROI: `good`, `bad`, or `gray` for undetermined |
| `suite2p_roi` or `roi` | optional original ROI index per row; otherwise rows are in ROI order |
| attributes `good_threshold`, `bad_threshold` | the thresholds that produced `state` |
| attributes `target_structure`, `model_source`, `model_path` | provenance carried into the reviewer |

```python
import h5py
import numpy as np

with h5py.File("roi_model_scores.h5", "w") as handle:
    handle.create_dataset("probability", data=probability.astype(np.float64))
    handle.create_dataset("state", data=np.array(states, dtype="S"))
    handle.create_dataset("suite2p_roi", data=np.arange(len(probability)))
    handle.attrs["good_threshold"] = 0.85
    handle.attrs["bad_threshold"] = 0.15
```

The probability appears under **Model Derived Metrics** in the filter and sort menus. The
states are used only when the build sets `initialize_labels_from_model_scores: true`,
in which case ROIs open as Good, Bad or Unsure.

## Converting from another pipeline

```bash
python scripts/make_standard_inputs.py \
    --masks  segmentation/cell_masks.npy \
    --traces segmentation/traces.npy \
    --out    data/my_session
```

| Option | Use |
|---|---|
| `--masks` | dense 2-D integer label image (`.npy`, `.npz`, `.csv`) |
| `--traces` | raw fluorescence, ROIs by frames or frames by ROIs |
| `--neuropil` | optional neuropil traces, same shape as `--traces` |
| `--spikes` | optional inferred spike amplitudes, same shape as `--traces` |
| `--dff` | optional precomputed dF/F; omit to let the generator compute it |
| `--fov` | optional functional mean image |
| `--cell-types` | optional per-ROI codes |
| `--row-order` | the mask label belonging to each trace row, in row order |
| `--out` | output directory |

The converter transposes a frames-by-ROIs trace matrix, compacts mask labels that are
not a gap-free run from 1, and writes dF/F and spikes as HDF5.

## Validate before you build

```bash
python scripts/validate_inputs.py data/my_session
```

It reports shape disagreements, a mask label count that does not match the trace row
count, arrays that are not C-ordered, a stray `.npy` where HDF5 is expected, and files
it cannot read at all. It exits non-zero when it finds an error, so it can gate a
pipeline step. `build_reviewer.py` runs the same checks unless you pass
`--skip-validation`.

## The one thing no tool can check

Whether mask label *k* really belongs to trace row *k−1*.

A mismatch produces a reviewer in which every mask is paired with the wrong trace.
Every array has the right shape, every check passes, and nothing in the interface
flags it. Pass `--row-order` if your segmentation numbers masks and traces
differently, and spot-check one known-active ROI before trusting a session: select it
in the field of view and confirm the trace panel shows the activity you expect in the
place you expect it.
