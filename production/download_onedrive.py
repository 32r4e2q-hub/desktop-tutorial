#!/usr/bin/env python3
"""Download the verified public movie source from Google Drive.

The workflow originally receives a OneDrive URL, but OneDrive's browser viewer can
incorrectly report an offline state on headless CI runners. The original Google
Drive share is public and gdown handles its large-file confirmation page.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

GOOGLE_DRIVE_SOURCE = "https://drive.google.com/file/d/1NBU97TEL-qlqxgLE4MY5oaS33akWC6CM/view?usp=sharing"
MIN_SOURCE_SIZE = 500_000_000


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="Retained for workflow compatibility; Google Drive is used as the reliable source.")
    parser.add_argument("output")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    print("Installing the Google Drive large-file downloader...", flush=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "gdown==5.2.0"],
        check=True,
    )

    for attempt in range(1, 4):
        print(f"Downloading verified movie source (attempt {attempt}/3)...", flush=True)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "gdown",
                "--fuzzy",
                "--continue",
                GOOGLE_DRIVE_SOURCE,
                "-O",
                str(output),
            ]
        )
        size = output.stat().st_size if output.exists() else 0
        if result.returncode == 0 and size >= MIN_SOURCE_SIZE:
            print(f"Movie downloaded successfully: {size} bytes", flush=True)
            return
        print(f"Attempt {attempt} did not produce the full movie ({size} bytes).", flush=True)
        output.unlink(missing_ok=True)

    print("::error title=Google Drive download failed::The public movie file could not be downloaded after three attempts")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
