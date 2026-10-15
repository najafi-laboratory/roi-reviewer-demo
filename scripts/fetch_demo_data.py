#!/usr/bin/env python3
"""Download the demo sessions from the public archive into data/demo/.

Lab-specific; delete this script together with config/demo/ for a clean start.

    python scripts/fetch_demo_data.py --all
    python scripts/fetch_demo_data.py cerebellum_dendrite
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

# Set once the deposit is published. Until then this script explains itself
# rather than guessing a record that does not exist.
ZENODO_RECORD_ID: str | None = None
ZENODO_API = "https://zenodo.org/api/records/{record_id}"

DATASETS = {
    "cerebellum_dendrite": "Dendrite-targeted cerebellar recording, Suite2p input path",
    "ppc_multi_indicator": "Multiple-indicator PPC recording with cell-type labels",
}
DEST = Path(__file__).resolve().parent.parent / "data" / "demo"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(name: str) -> None:
    if ZENODO_RECORD_ID is None:
        raise SystemExit(
            "No archive record is configured yet.\n"
            "Set ZENODO_RECORD_ID at the top of this script once the deposit is "
            "published, or point the config's session_path at a local directory."
        )
    import json

    with urllib.request.urlopen(ZENODO_API.format(record_id=ZENODO_RECORD_ID)) as response:
        record = json.load(response)
    files = {entry["key"]: entry for entry in record.get("files", [])}
    matching = [key for key in files if key.startswith(name)]
    if not matching:
        raise SystemExit(f"record {ZENODO_RECORD_ID} has no files for {name!r}; found {sorted(files)}")
    target_dir = DEST / name
    target_dir.mkdir(parents=True, exist_ok=True)
    for key in matching:
        entry = files[key]
        out = target_dir / key
        if out.exists():
            print(f"  have {key}")
            continue
        print(f"  downloading {key} ({entry['size'] / 1e6:.0f} MB)")
        urllib.request.urlretrieve(entry["links"]["self"], out)
        expected = entry.get("checksum", "").removeprefix("md5:")
        print(f"    sha256 {_sha256(out)[:16]}... (archive checksum {expected[:16]}...)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("datasets", nargs="*", choices=sorted(DATASETS) or None, default=[])
    parser.add_argument("--all", action="store_true", help="fetch every demo dataset")
    parser.add_argument("--list", action="store_true", help="list the demo datasets and exit")
    args = parser.parse_args()

    if args.list or (not args.datasets and not args.all):
        for name, description in DATASETS.items():
            print(f"{name:<24} {description}")
        return 0
    for name in sorted(DATASETS) if args.all else args.datasets:
        print(name)
        fetch(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
