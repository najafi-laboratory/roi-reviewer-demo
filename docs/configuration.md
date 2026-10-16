# Build configuration

One session, one configuration file. Copy `config/template.yaml`, edit the paths, and
pass it to `scripts/build_reviewer.py`. The template ships with every field commented;
this page is the same information in reference form.

```yaml
name: my_session
session_path: /path/to/processed/session
input_layout: auto
output_dir: outputs/my_session
roi_index_label: "Original Index"
target_structure: null
initialize_labels_from_model_scores: false
notes: ""
```

| Field | Meaning |
|---|---|
| `name` | free text, used for output filenames and in the run log |
| `session_path` | directory the generator reads: a session root containing `suite2p/plane0/`, the plane directory itself, or a directory of standard-format inputs |
| `input_layout` | `auto`, `suite2p`, `external_rois`, `qc_results` or `manual_qc_results` |
| `output_dir` | where the reviewer HTML and summary PDF are written |
| `roi_index_label` | label shown for each ROI's original index |
| `target_structure` | `soma`, `dendrite` or `null`, selecting which built-in morphology preset is offered |
| `initialize_labels_from_model_scores` | open with every ROI unlabeled, or pre-labeled from a stored classifier score file when one is present |
| `notes` | free text copied into the run log beside the resolved paths |

## Choosing an input layout

`auto` infers the layout and prints what it chose, which is the right setting for most
sessions. Name the layout explicitly when a session directory contains more than one
candidate.

!!! warning "Deprecated pre-filtered layouts"
    `qc_results` and `manual_qc_results` describe pre-filtered ROI sets. Select them
    explicitly rather than relying on `auto`, because a session containing both a full
    and a pre-filtered set will silently resolve to the pre-filtered one, and the
    reviewer will then show fewer ROIs than the segmentation produced with nothing to
    indicate it.

## roi_index_label

Each ROI carries the index it had in the upstream segmentation, and the reviewer shows
that index in the selected-ROI header, the labeler and the exported table. The default
wording names Suite2p because that is the common case; set `roi_index_label` to
`"Original Index"`, or to whatever your pipeline calls it, when the ROIs came from
somewhere else. It is presentation only and changes no data.

## target_structure

The preset windows select a built-in set of morphology thresholds. They were
calibrated on Suite2p's own morphology values, and the external-mask path recomputes
those quantities with definitions that do not share the same scale, so a preset
calibrated on one can reject well-formed masks scored under the other.

Leave `target_structure: null` for external masks and set thresholds from the
distribution preview beside each field instead. See [Interface Tour](interface.md) for
what that preview shows.

## Checking a configuration

```bash
python scripts/build_reviewer.py config/my_session.yaml --dry-run
```

This resolves every path, reports the layout that would be used, and writes nothing.
Add `--skip-validation` only when you have already validated the inputs and want to
skip the repeat check.
