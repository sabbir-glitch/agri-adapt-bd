"""
Attempts to fetch REAL candidate datasets listed in
docs/data-provenance/provenance-register.md. This script is written to
be run from a normal internet-connected machine — NOT the sandboxed
environment this repository was originally built in, which could not
reach most of these hosts (GitHub raw files were reachable) (see provenance register for the specific,
tested reasons why).

This script does not guess at file names or API parameters it hasn't
seen documented. Where a step requires information I could not verify
(e.g. the exact Mendeley download file name), it prints what's needed
and stops, rather than guessing.

Usage:
    pip install kaggle requests
    # Kaggle: place kaggle.json per https://www.kaggle.com/docs/api
    python scripts/fetch_real_data.py --source kaggle
    python scripts/fetch_real_data.py --source nasa_power
    python scripts/fetch_real_data.py --source mendeley_agriclimatebd
    python scripts/fetch_real_data.py --source sajidahmed12     # jute & wheat used by run_real_pipeline.py

POLICY: no function in this file silently falls back to synthetic data
on failure. fetch_kaggle() prints an error and returns; fetch_nasa_power()
uses requests' raise_for_status() so a failed request raises visibly.
If you want synthetic demonstration data, run
scripts/generate_synthetic_demo.py explicitly and separately — this
script never does that for you.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

DATA_RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")


def fetch_kaggle():
    """
    Downloads the verified Kaggle candidates from
    docs/data-provenance/provenance-register.md (#7-#9). Requires the
    Kaggle CLI and your own API credentials.
    """
    datasets = [
        ("firozemaliha/bangladesh-agroclimatic-crop-yield-2000-2024", "MIT"),
        ("arshadrahmanziban/potato-production-in-bangladesh-from-1980-to-2024", "ODbL"),
        ("shuvokumarbasak2030/bangladesh-historical-rainfall-dataset-1948-2014", "MIT"),
    ]
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    for ref, licence in datasets:
        print(f"Downloading {ref} (licence: {licence})...")
        try:
            subprocess.run(["kaggle", "datasets", "download", "-d", ref,
                             "-p", DATA_RAW_DIR, "--unzip"], check=True)
        except FileNotFoundError:
            print("Kaggle CLI not found. Install with: pip install kaggle", file=sys.stderr)
            return
        except subprocess.CalledProcessError as e:
            print(f"Failed to download {ref}: {e}", file=sys.stderr)


def fetch_nasa_power(lat: float = 23.8103, lon: float = 90.4125,
                      start: str = "2010", end: str = "2023"):
    """
    Queries NASA POWER's monthly point API directly. No API key required.
    Default coordinates are Dhaka; pass --lat/--lon for other locations.
    """
    import requests  # local import: only needed for this function
    url = (
        "https://power.larc.nasa.gov/api/temporal/monthly/point"
        f"?parameters=T2M,PRECTOTCORR,RH2M&community=AG"
        f"&longitude={lon}&latitude={lat}&start={start}&end={end}&format=CSV"
    )
    print(f"Requesting: {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    out_path = os.path.join(DATA_RAW_DIR, f"nasa_power_{lat}_{lon}_{start}_{end}.csv")
    with open(out_path, "w") as f:
        f.write(resp.text)
    print(f"Saved to {out_path}")
    print("NOTE: record the exact access date/time and these parameters in "
          "docs/data-provenance/provenance-register.md before using this file.")


SAJID_BASE = ("https://raw.githubusercontent.com/sajidahmed12/"
              "Agricultural-Crop-Yield-Prediction/main/data/")
SAJID_FILES = {
    "jute.csv": "a99a4a2154b45d2ac59a334273eda13ea90eeeb8748a85d12a060d03939bc3bf",
    "wheat.csv": "23a8912ad1d6918d1b22e96f431b42db8c7943394276b7de4a43c9bd3b07ea23",
}


class IntegrityError(RuntimeError):
    pass


def verify_sha256(path: str, expected: str) -> None:
    """Raises IntegrityError if the file's SHA-256 differs from `expected`."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    if h.hexdigest() != expected:
        raise IntegrityError(f"{path}: SHA-256 {h.hexdigest()} != expected {expected}")


def fetch_sajidahmed12(dest_dir: str | None = None):
    """
    Downloads jute.csv and wheat.csv (from github.com/sajidahmed12/
    Agricultural-Crop-Yield-Prediction) into data/raw/sajidahmed12_crop_data/,
    verifies their SHA-256 against the checksums recorded when the files were
    first inspected, and writes RETRIEVAL.json (source URLs + access date).
    Fails explicitly (non-zero exit) on any download or integrity failure and
    removes the unverified file. The primary statistical provenance of these
    figures is NOT resolved — see docs/data-provenance/provenance-register.md.
    """
    import requests
    dest = dest_dir or os.path.join(DATA_RAW_DIR, "sajidahmed12_crop_data")
    os.makedirs(dest, exist_ok=True)
    record = {"access_date_utc": datetime.now(timezone.utc).isoformat(), "files": {}}
    for name, expected in SAJID_FILES.items():
        url = SAJID_BASE + name
        out = os.path.join(dest, name)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        with open(out, "wb") as f:
            f.write(resp.content)
        try:
            verify_sha256(out, expected)
        except IntegrityError:
            os.remove(out)
            raise
        record["files"][name] = {"url": url, "sha256": expected}
        print(f"OK  {name}  sha256 verified")
    with open(os.path.join(dest, "RETRIEVAL.json"), "w") as f:
        json.dump(record, f, indent=2)
    print(f"Files placed in {dest}; see ATTRIBUTION.md (upstream repository: MIT, (c) 2021 Sajid Ahmed; dataset-specific rights unresolved).")


def fetch_mendeley_agriclimatebd():
    print(
        "AgriClimateBD is hosted on Mendeley Data "
        "(DOI 10.17632/tb5x9gw2pt — confirm exact version, /1 vs /2, on the live page).\n"
        "Mendeley does not offer a documented stable public API for this project to call "
        "programmatically. Manual steps:\n"
        "  1. Visit https://data.mendeley.com/datasets/tb5x9gw2pt/ and confirm the current version.\n"
        "  2. Download the file(s) manually (check the licence shown on that page first).\n"
        "  3. Place the downloaded file(s) in data/raw/agriclimatebd/\n"
        "  4. Open the file yourself and record its ACTUAL columns — do not assume they match "
        "the canonical schema in src/data/ingestion.py.\n"
        "  5. Write a column_mapping dict ({source_col: canonical_col}) from what you actually "
        "observed, and use src/data/adapters.py::adapt_generic_wide_csv() to convert it — "
        "do not hand-edit the raw file's column names directly, so the mapping stays auditable.\n"
        "  6. Update docs/data-provenance/provenance-register.md: change this dataset's status "
        "from DOCUMENTED to OBSERVED, with the confirmed version, exact file names, licence "
        "text, and your access date.\n"
        "  7. Re-run: python scripts/run_pipeline.py --source real "
        "--path data/raw/agriclimatebd/<adapted_file>.csv --name agriclimatebd\n\n"
        "IMPORTANT: this function does not download anything automatically and never silently "
        "substitutes synthetic data if you skip these steps — it only prints these instructions."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["kaggle", "nasa_power", "mendeley_agriclimatebd", "sajidahmed12"],
                         required=True)
    parser.add_argument("--lat", type=float, default=23.8103)
    parser.add_argument("--lon", type=float, default=90.4125)
    parser.add_argument("--start", default="2010")
    parser.add_argument("--end", default="2023")
    args = parser.parse_args()

    if args.source == "kaggle":
        fetch_kaggle()
    elif args.source == "nasa_power":
        fetch_nasa_power(args.lat, args.lon, args.start, args.end)
    elif args.source == "mendeley_agriclimatebd":
        fetch_mendeley_agriclimatebd()
    elif args.source == "sajidahmed12":
        try:
            fetch_sajidahmed12()
        except Exception as e:  # explicit failure, never a synthetic fallback
            sys.exit(f"ERROR: retrieval failed: {e}")
