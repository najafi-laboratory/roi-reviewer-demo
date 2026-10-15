# Vendored code

`roi_reviewer/` is a copy of the summary-generation stage from
[najafi-laboratory/2p_imaging](https://github.com/najafi-laboratory/2p_imaging),
not a dependency on it. Nothing here imports `utils_2p`, and the repository runs
for anyone, with or without access to that repository.

| file | copied from | at |
|---|---|---|
| `roi_reviewer/summary.py` | `utils_2p/processing_summary.py` | `d24d1ab776` (claude/reviewer-updates) |
| `roi_reviewer/roi_metrics.py` | `utils_2p/roi_labels.py` | `d24d1ab776` (claude/reviewer-updates) |

Copied on 2026-10-15. The only edit applied was the import rewrite
`utils_2p.roi_labels` to `roi_reviewer.roi_metrics`.

## Re-syncing

A copy drifts. To pull a later version:

```bash
git -C /path/to/2p_imaging log --oneline -- utils_2p/processing_summary.py utils_2p/roi_labels.py
cp /path/to/2p_imaging/utils_2p/processing_summary.py roi_reviewer/summary.py
cp /path/to/2p_imaging/utils_2p/roi_labels.py        roi_reviewer/roi_metrics.py
sed -i 's/from utils_2p.roi_labels import/from roi_reviewer.roi_metrics import/' roi_reviewer/summary.py
```

Then restore the header comment on each file, update the commits in the table
above, and run the smoke test in `.github/workflows/smoke.yml` before committing.

## Deliberate divergences

- The saved-filter schema identifier is still `utils_2p_roi_metric_filter_v1`.
  It is left unchanged so filter files are interchangeable between this tool and
  the laboratory pipeline.
- Help links inside the generated HTML point at the `2p_imaging` documentation
  site, which is where the reviewer is documented in depth.
