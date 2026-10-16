# Demo sessions

Two configurations under `config/demo/` build reviewers from laboratory recordings,
one per input path worth demonstrating.

| Config | Demonstrates |
|---|---|
| `demo_cerebellum_dendrite.yaml` | Suite2p input path; dendrite morphology preset |
| `demo_ppc_multi_indicator.yaml` | anatomical second channel; excitatory/inhibitory cell-type labels; sidecar array storage |

```yaml
name: demo_ppc_multi_indicator
session_path: data/demo/ppc_multi_indicator
input_layout: suite2p
output_dir: outputs/demo_ppc_multi_indicator
roi_index_label: "Original Index"
target_structure: soma
```

!!! note "Everything here is deletable"
    `config/demo/` and `scripts/demo_assemble_ppc_session.sh` are laboratory-specific.
    Delete both for a clean start; nothing else in the repository depends on them.

## Getting the data

The recordings are published separately from the code. `scripts/fetch_demo_data.py`
downloads them into `data/demo/` once the archive record is set at the top of that
script.

## Assembling the PPC session

The posterior parietal cortex session is not one directory. Its Suite2p outputs, its
inferred spikes and its cell-type labels live in three places, and the labels do not
exist as a file at all until they are derived from the red-channel call.
`scripts/demo_assemble_ppc_session.sh` records that assembly:

```bash
bash scripts/demo_assemble_ppc_session.sh
python scripts/build_reviewer.py config/demo/demo_ppc_multi_indicator.yaml
```

It links the Suite2p outputs and the spikes file into one session directory, derives
per-ROI cell-type codes from `redcell.npy` following the documented coding (1 for
inhibitory/red, −1 for excitatory/non-red), prints the resulting label counts, and
names the build command to run next.

This script assumes the laboratory's storage layout and will not run elsewhere. It is
in the repository as a worked example of the general problem it solves: a processed
session scattered across several locations, with one input that has to be computed
rather than copied.

## Storage mode

The two demos differ in how the trace arrays are stored, which is deliberate. Below the
embedding threshold the arrays go inside the HTML and the file is self-contained on its
own. Above it they are written beside the HTML as `.npy` sidecars, which the browser
reads on demand. The PPC session, at 225 ROIs over 107,135 frames, lands in sidecar
mode, so it also serves as the example of that path.
