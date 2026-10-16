# Vendored generator

This repository does not install or import the laboratory's `2p_imaging` package. The
generator is copied into `roi_reviewer/`:

| File here | Copied from |
|---|---|
| `roi_reviewer/summary.py` | `utils_2p/processing_summary.py` |
| `roi_reviewer/roi_metrics.py` | `utils_2p/roi_labels.py` |

Those two modules were the whole import closure; everything else the generator needs is
a third-party package. The only edit applied to the copied source is one import
rewrite, from `utils_2p.roi_labels` to `roi_reviewer.roi_metrics`. `VENDOR.md` in the
repository root records the source commit for each file and the re-sync procedure.

## Why a copy

A demonstration repository that depends on a private laboratory package is not a
demonstration anyone outside the laboratory can run. Vendoring makes `pip install -e .`
sufficient, at the cost of a copy that can drift from its source.

Continuous integration guards the property that motivated the copy: it generates a
reviewer from a synthetic session with `utils_2p` blocked at import, so any residual
dependency fails the build rather than silently resolving from an installed copy.

## Deliberate divergences

Two things still point at the laboratory package on purpose.

* The saved-filter schema identifier is unchanged, so filter files written here and by
  the laboratory pipeline remain interchangeable.
* The in-page help links point at the `2p_imaging` documentation site, which is where
  the long-form metric documentation lives.

## Keeping it in sync

A change to the generator has to be applied in both places, or the copy re-taken. The
procedure in `VENDOR.md` is to copy the upstream file again, reapply the single import
rewrite, and run the smoke workflow, which will catch a new dependency on the
laboratory package immediately.
