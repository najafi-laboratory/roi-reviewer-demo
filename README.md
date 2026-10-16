# roi-reviewer-demo

A minimal, copyable project layout for generating interactive ROI quality-control
reviewers from two-photon calcium imaging sessions, whatever software produced
the segmentation.

This repository is standalone. It carries its own copy of the generator in
`roi_reviewer/` (see `VENDOR.md` for where that code came from), so nothing here
installs or imports a laboratory package, and it runs for anyone with the
dependencies in `environment.yml`. Around the generator it provides: one configuration file per session, a converter that puts arbitrary
segmentation output into the documented input layout, a validator that catches
the mistakes that otherwise surface as a silently wrong reviewer, and a build
script that records how each output was produced.

## Documentation

The full documentation is in `docs/` and is published as a site at
<https://najafi-laboratory.github.io/roi-reviewer-demo/>: a quickstart, the
input contract, every configuration field, a tour of the reviewer interface,
the mapping between command-line flags, configuration fields and reviewer
controls, and the demo sessions. To read it locally:

```bash
pip install -r requirements-docs.txt
mkdocs serve
```

## Installation

```bash
git clone https://github.com/najafi-laboratory/roi-reviewer-demo
cd roi-reviewer-demo
pip install -e .          # or: conda env create -f environment.yml
```

That is the whole dependency story. The generator is vendored in `roi_reviewer/` (see `VENDOR.md`), so no laboratory package is installed or imported, and `python -m roi_reviewer.summary --help` works immediately.

## Quickstart

```bash
conda env create -f environment.yml && conda activate roi-reviewer-demo

cp config/template.yaml config/my_session.yaml   # edit session_path and output_dir
python scripts/build_reviewer.py config/my_session.yaml --dry-run
python scripts/build_reviewer.py config/my_session.yaml
```

The output directory receives the reviewer HTML, the static summary PDF, and a
`run.json` recording the exact command, so any example here can be regenerated.

## Starting from a clean slate

Everything lab-specific is confined to two directories, both named `demo`:

```bash
rm -rf config/demo data/demo scripts/fetch_demo_data.py
```

Nothing outside them refers to a particular recording. `config/template.yaml`,
the three scripts and the CI workflow are generic.

## If your data did not come from Suite2p

The reviewer needs exactly two correspondences to hold:

```
ROI row i  ->  pixels (or weights) in the displayed field-of-view frame
ROI row i  ->  fluorescence trace row i
```

`scripts/make_standard_inputs.py` builds a directory satisfying that from a
dense label mask plus a trace matrix, transposing traces when they arrive
frames-by-ROIs and compacting mask labels that are not a gap-free run:

```bash
python scripts/make_standard_inputs.py \
    --masks  segmentation/cell_masks.npy \
    --traces segmentation/traces.npy \
    --spikes segmentation/deconvolved.npy \
    --fov    segmentation/mean_image.npy \
    --out    data/my_session

python scripts/validate_inputs.py data/my_session
```

| File written | Meaning |
|---|---|
| `roi_mask.npy` | dense 2-D integer label image; 0 is background, label *k* is ROI row *k−1* |
| `F.npy`, `Fneu.npy` | raw fluorescence and neuropil, `(n_rois, n_frames)` float32, C-ordered |
| `dff.h5` (dataset `dff`), `spikes.h5` (dataset `spikes`) | optional precomputed dF/F and inferred spike amplitudes, `(n_rois, n_frames)` float32. These two are read from HDF5, not `.npy`; a `.npy` of either name is ignored, which `validate_inputs.py` reports as an error |
| `mean_func.npy` | optional functional mean image, `(Ly, Lx)` |
| `roi_cell_type_labels.npy` | optional per-ROI codes: −1 excitatory, 0 unsure, 1 inhibitory, NaN unknown |
| `external_roi_metadata.json` | `image_shape` and `flatten_order`, needed for sparse components without an image |

Sparse `(pixels, n_rois)` component matrices from CaImAn-style pipelines are
accepted directly as `spatial_components.npz`; supply `flatten_order: "F"`
unless your pixel indices are row-major.

**The one thing no tool can check for you** is whether mask label *k* really
belongs to trace row *k−1*. A mismatch produces a reviewer in which every mask
is paired with the wrong trace, and nothing in the interface will flag it. Pass
`--row-order` if your segmentation numbers masks and traces differently, and
spot-check one known-active ROI before trusting a session.

## Demo sessions

| Config | Demonstrates |
|---|---|
| `config/demo/demo_cerebellum_dendrite.yaml` | Suite2p input path; dendrite morphology preset |
| `config/demo/demo_ppc_multi_indicator.yaml` | anatomical second channel; excitatory/inhibitory cell-type labels; sidecar array storage |

The recordings are published separately; `scripts/fetch_demo_data.py` downloads
them into `data/demo/` once the archive record is set at the top of that script.

## Layout

```
config/
  template.yaml              commented starting point, one per session
  demo/                      lab-specific examples; delete for a clean start
scripts/
  build_reviewer.py          config -> reviewer, writes run.json
  make_standard_inputs.py    arbitrary segmentation output -> documented layout
  validate_inputs.py         checks a directory against the contract
  fetch_demo_data.py         demo datasets from the public archive
  demo_assemble_ppc_session.sh   builds the PPC session from laboratory storage
data/                        inputs (git-ignored)
outputs/                     generated reviewers (git-ignored)
```
