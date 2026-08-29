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

SOURCE_ITEM_API = 'https://onedrive.live.com/_api/v2.0/drives/b!8CGwIeTW9UOMBN7bDXIXSGyINjJWHwNIrnuHIGwgU9I8I7ew4QkfQpur8Xfy2CxW/items/01BIVNJFRWZH3DX35NYFHKFWBGDFBQGPN5?tempauth=v1e.eyJzaXRlaWQiOiIyMWIwMjFmMC1kNmU0LTQzZjUtOGMwNC1kZWRiMGQ3MjE3NDgiLCJhdWQiOiIwMDAwMDAwMy0wMDAwLTBmZjEtY2UwMC0wMDAwMDAwMDAwMDAvb25lZHJpdmUubGl2ZS5jb21AOTE4ODA0MGQtNmM2Ny00YzViLWIxMTItMzZhMzA0YjY2ZGFkIiwiZXhwIjoiMTc4ODAzNTAzNCJ9.-FwFn9Y2jL64Yc6OD2-pC8tReestuGVmov19bQeQP5S9BBThm5JerY93HXuR1lV5k2wYDC2h225NWuL0inLIx1M-Mn2fHNbo5jd6JqF2_nVb5K8A9X7do2WARYeQ1meGZF020uEwIjxbenU4EeVbglk5b7ld2F_8cHlHjGAiIuJhq9L302gn3Pn7sSQGIlOQTuMp6r_wMtM0cKJ_rJT_dC7QmGPZ_9Ad2I2fmz9NnsugTnT2lR1zqsx5e4iIlhKxTp8yj8rNCQAmpgVvL19uBbjr32QY10WovQEIKIfxEEsHBwtf__yrivwxeps3cQrSzGWOmHtB5GkiSpaMhadWi4d-ryDocWAfZCnD7WzAaR5bERewDWklh0iI2MtQWu30wxG4xnsSVkolAFwacdXg9fzKUVdarGCEnT_rTXyC3WeMqfclPNI0MLF8dcTWeF2iIoj1xnmFMzf_zQXm9dZb5bBC2wwbIHAeLMeQidpESYY.rsV8h87yL5ZWS8Gp42WWO7NpbRqLzQiFRHFlgsjYPK8&version=Published&VroomTakeover=1'
EXPECTED_NAME = '@shincyan666=dd9cac.mp4'
EXPECTED_SIZE = 182_506_802
EXPECTED_SHA1 = 'A3EBAD8411FDB5231B5F56B03C050DEC4D8CCF35'


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



if __name__ == "__main__":
    main()
