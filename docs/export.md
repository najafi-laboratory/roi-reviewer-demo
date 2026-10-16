# Export and downstream use

The reviewer opens with every detected ROI, none labeled and no filter applied. The
review path is:

```
all detected ROIs
      |
      v  optional metric filters (Apply Filters labels failing ROIs Bad)
      v  manual Good / Bad / Unsure / Not labeled review
      v
reviewed HTML, roi_manual_labels.npy, metric spreadsheet CSV, thresholds JSON
```

## What each export contains

<div class="screenshot" markdown>
![The Save Labels dialog.](img/export-save.png)
</div>

| Export | Contents | Use it for |
|:---|:---|:---|
| **Save current state into HTML** | A new self-contained reviewer with the current labels, thresholds, saved filter sets and uploaded metrics or labels embedded | Stopping and resuming; sending a reviewed session to someone else |
| **Export metric spreadsheet CSV** | One row per ROI: original index, label, every metric, and a `reason` column naming the thresholds the ROI failed ([columns](metrics.md)) | Analysis; recording why each ROI was excluded |
| **Export labels NPY** | `roi_manual_labels.npy`, one value per original ROI index | Loading reviewed ROIs downstream |
| **Export QC thresholds JSON** | The active filter thresholds | Reusing a rule on another session; citing it alongside a figure |

The page never writes back to the file it was opened from. Saving state downloads a
new copy. Arrays loaded by hand with **Load dF/F file** or **Load inferred spikes file**
are not embedded in the saved copy; keep the sidecars beside it.

## Saving and reusing filters

Filter sets can be saved under a name inside the open page, exported as JSON, and
imported into another session with **Import QC thresholds JSON**. A threshold file is
small and diffable, which makes it the record to keep for provenance.

## Loading reviewed ROIs

`roi_manual_labels.npy` is a one-dimensional array with one entry per original ROI
index: `NaN` not labeled, `0` bad, `1` good, `2` unsure. `roi_manual_labels[i]` is
always the label for ROI `i`, whatever filtering or sorting happened during review.
Placed beside the Suite2p files, it is read by the loader shipped with the package:

```python
from roi_reviewer.roi_metrics import load_reviewed_dff

session = load_reviewed_dff("/path/to/session")
dff         = session["dff"]          # (selected_rois, frames)
roi_indices = session["roi_indices"]  # original ROI indices
```

| `policy` | ROIs returned |
|:---|:---|
| `"good_only"` (default) | Good |
| `"good_or_unsure"` | Good and Unsure |
| `"not_bad"` | Good, Unsure and Not labeled |

`label_path=` reads the labels from elsewhere, including an interactive reviewer JSON
export. Suite2p's original `iscell.npy` is never used implicitly.

## What to archive

The combination worth depositing alongside a result is the reviewed HTML (it shows
exactly what the reviewer saw), the thresholds JSON (it states the rule), and the metric
spreadsheet CSV (it records every ROI's metrics, label and exclusion reason at export).
