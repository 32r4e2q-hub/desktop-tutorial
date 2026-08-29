#!/usr/bin/env python3
"""Download Colony from OneDrive using the temporary item API token supplied by the user."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

SOURCE_ITEM_API = 'https://onedrive.live.com/_api/v2.0/drives/b!8CGwIeTW9UOMBN7bDXIXSGyINjJWHwNIrnuHIGwgU9I8I7ew4QkfQpur8Xfy2CxW/items/01BIVNJFW2O3VS57M6RVF3QRIIXSLZM7TF?tempauth=v1e.eyJzaXRlaWQiOiIyMWIwMjFmMC1kNmU0LTQzZjUtOGMwNC1kZWRiMGQ3MjE3NDgiLCJhdWQiOiIwMDAwMDAwMy0wMDAwLTBmZjEtY2UwMC0wMDAwMDAwMDAwMDAvb25lZHJpdmUubGl2ZS5jb21AOTE4ODA0MGQtNmM2Ny00YzViLWIxMTItMzZhMzA0YjY2ZGFkIiwiZXhwIjoiMTc4ODAzMDczOSJ9.rMsAjQFyCgZIEMe1-ftm1uUo4PZ80QaU63KSKkSetodsJug_aT8LkFmvGYyKWq07ivID3uT8jKgIZ5zjoavEO5fdLJKmj0fzk9Co_IyRL7Rgaft2uLuMkETR9Jq42a3m7jvAtD3u6c_xn1Wb4vycZk2EV98fiQTdLu8xihh71jHrSZ81Ory2qeybzP-hZrG-G3AHIvneUIXppyXbBAqFldrh-hCBkzrAn1E5bF3K-_cPTxpBsGR9PpxaCx6U4mQPiaDn5sCXksrN0G9fC0yAAtuIalBiO49GLV1FVDG260BpvXtCngbms3lPFy1t7YIahTHEu21vqMP1G3aC4S8yKeyo7w5ugWWHlCvanIOcC-3jxPokuq8B04ip615XBSoBXUpsla0ShhRjsBnAWi4QTD2ASoGZaeH_6zHgAhnltRR1JQt4NdDL6FNprddrsDCiNJxbIoSQ6Y6Ts9mUnCF30tUBSl-rUNqioWwTH15OV8o._ntqknK7sdDAFTH6DS3IeYwNCt9vzUGLcYxASZgrA4g&version=Published&VroomTakeover=1'
REFERENCE_GOOGLE_DRIVE = "https://drive.google.com/file/d/1HtUQyrpBSwYLJvqMXSa5kz_E2cjOmmcR/view?usp=sharing"
EXPECTED_NAME = "Colony.2026.1080p.mp4"
EXPECTED_SIZE = 3_805_764_950
EXPECTED_SHA1 = "6BB98ACDB12B77B5B8DCADCF78200784983FB72E"


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Retained for workflow compatibility")
    parser.add_argument("output")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    request = urllib.request.Request(SOURCE_ITEM_API, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        metadata = json.load(response)
    if metadata.get("name") != EXPECTED_NAME or int(metadata.get("size", 0)) != EXPECTED_SIZE:
        raise RuntimeError(f"Unexpected OneDrive item metadata: {metadata.get('name')} / {metadata.get('size')}")
    download_url = metadata.get("@content.downloadUrl")
    if not download_url:
        raise RuntimeError("OneDrive item API did not return @content.downloadUrl")

    print(f"Downloading {EXPECTED_NAME} ({EXPECTED_SIZE} bytes) from signed OneDrive content URL...", flush=True)
    subprocess.run(
        [
            "curl", "-fL", "--retry", "4", "--retry-delay", "4", "--connect-timeout", "30",
            "--output", str(output), download_url,
        ],
        check=True,
    )
    size = output.stat().st_size
    if size != EXPECTED_SIZE:
        raise RuntimeError(f"Source size mismatch: {size} != {EXPECTED_SIZE}")
    actual_sha1 = sha1(output)
    if actual_sha1 != EXPECTED_SHA1:
        raise RuntimeError(f"Source SHA1 mismatch: {actual_sha1} != {EXPECTED_SHA1}")
    print(f"SOURCE VERIFIED: {EXPECTED_NAME} / {size} bytes / SHA1 {actual_sha1}", flush=True)

    # Download the user's original Douyin commentary example for rhythm analysis.
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "gdown==5.2.0"], check=True)
    reference = output.parent / "reference.mp4"
    reference.unlink(missing_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "gdown", "--fuzzy", REFERENCE_GOOGLE_DRIVE, "-O", str(reference)]
    )
    if result.returncode != 0 or not reference.exists() or reference.stat().st_size < 20_000_000:
        print("::warning title=Reference download::Douyin reference unavailable; using measured 3.7s rhythm")
        reference.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
