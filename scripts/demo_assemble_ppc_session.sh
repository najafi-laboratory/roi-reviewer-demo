#!/usr/bin/env bash
# DEMO SCRIPT -- Najafi laboratory, posterior parietal cortex session.
# Lab-specific: it assumes PACE paths and this laboratory's storage layout.
# Delete it along with config/demo/ for a clean start.
#
# The processed PPC session is spread across three places, which is why this
# script exists rather than a single path in the config:
#
#   1. Suite2p outputs           on project (cedar) storage
#   2. inferred spikes           a separate spikes.h5 written by the pipeline
#   3. cell-type labels          derived here from Suite2p's redcell.npy
#
# It assembles them into one directory of symlinks plus one small derived file,
# leaving the source data untouched, and prints the build command to run next.
#
#   bash scripts/demo_assemble_ppc_session.sh
#   python scripts/build_reviewer.py config/demo/demo_ppc_multi_indicator.yaml

set -euo pipefail

CEDAR="${PPC_PROCESSED:-/storage/cedar/cedar0/cedarp-fnajafi3-0/2p_imaging/processed/passive/YH01VT/VTYH01_PPC_20250212_1451ShortLong}"
SPIKES="${PPC_SPIKES:-$HOME/scratch/2p_imaging_previews/scratch_sessions/VTYH01_PPC_20250212_1451ShortLong/spikes.h5}"
DEST="${PPC_DEST:-$(cd "$(dirname "$0")/.." && pwd)/data/demo/ppc_multi_indicator}"
PYTHON="${PYTHON:-python}"

for path in "$CEDAR/suite2p/plane0/F.npy" "$CEDAR/suite2p/plane0/redcell.npy" "$SPIKES"; do
    [ -e "$path" ] || { echo "missing: $path" >&2; exit 1; }
done

rm -rf "$DEST"
mkdir -p "$DEST"
ln -s "$CEDAR/suite2p" "$DEST/suite2p"
ln -s "$SPIKES" "$DEST/spikes.h5"

# Cell-type codes follow the documented convention:
#   -1 excitatory / non-red, 0 unsure, 1 inhibitory / red, NaN unknown.
# redcell.npy column 0 is Suite2p's thresholded call and column 1 the
# probability behind it. This takes the thresholded call as-is; substitute
# manually curated labels here if you have them, because everything downstream
# treats these as ground truth.
"$PYTHON" - "$CEDAR" "$DEST" <<'PY'
import sys
import numpy as np

cedar, dest = sys.argv[1], sys.argv[2]
redcell = np.load(f"{cedar}/suite2p/plane0/redcell.npy")
codes = np.where(redcell[:, 0] == 1, 1.0, -1.0).astype(np.float32)
np.save(f"{dest}/roi_cell_type_labels.npy", codes)
counts = {int(value): int((codes == value).sum()) for value in np.unique(codes)}
print(f"  cell-type codes written: {counts} (1 = inhibitory/red, -1 = excitatory/non-red)")
PY

echo "assembled $DEST"
echo
echo "next:"
echo "  python scripts/build_reviewer.py config/demo/demo_ppc_multi_indicator.yaml"
