#!/usr/bin/env python3
"""Download a publicly shared OneDrive file through its browser UI."""
import argparse
import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ALTERNATE_SOURCE_URL = "https://1drv.ms/v/c/1d2d728940a35022/IQAim5nTaIepRbqA5aF6NUbPAV-f-yLQoXERBDFPeH2TwFQ?e=b85YJZ"
MIN_SOURCE_SIZE = 500_000_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("output")
    args = ap.parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    def finish_download(download, browser):
        download.save_as(str(output))
        size = output.stat().st_size
        print(f"Saved {output} ({size} bytes)", flush=True)
        browser.close()
        if size >= MIN_SOURCE_SIZE:
            return
        if args.url != ALTERNATE_SOURCE_URL:
            print(f"Downloaded file is only {size} bytes; trying the other shared link.", flush=True)
            output.unlink(missing_ok=True)
            os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve()), ALTERNATE_SOURCE_URL, str(output)])
        print(f"::error title=Wrong OneDrive file::Both links were tried; the latest file is only {size} bytes")
        raise RuntimeError(f"OneDrive file is too small: {size} bytes")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        context = browser.new_context(accept_downloads=True, locale="en-US")
        page = context.new_page()
        page.set_default_timeout(30_000)
        print("Opening OneDrive share page...", flush=True)
        page.goto(args.url, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(12_000)

        # Dismiss optional consent/onboarding surfaces.
        for label in ("Accept", "Accept all", "Continue", "Got it", "Not now"):
            try:
                loc = page.get_by_role("button", name=label, exact=True)
                if loc.count() and loc.first.is_visible():
                    loc.first.click(timeout=3_000)
                    page.wait_for_timeout(1_000)
            except Exception:
                pass

        selectors = [
            '[data-automationid="download"]',
            'button[aria-label="Download"]',
            '[role="button"][aria-label="Download"]',
            'button[title="Download"]',
            '[role="button"][title="Download"]',
            'text="Download"',
            'button[aria-label*="下载"]',
            'text="下载"',
        ]
        error = None
        for selector in selectors:
            try:
                loc = page.locator(selector)
                if not loc.count():
                    continue
                for i in range(min(loc.count(), 5)):
                    item = loc.nth(i)
                    if not item.is_visible():
                        continue
                    print(f"Clicking download control: {selector}", flush=True)
                    with page.expect_download(timeout=240_000) as info:
                        item.click(force=True)
                    download = info.value
                    finish_download(download, browser)
                    return
            except Exception as exc:
                error = exc

        # OneDrive advertises Ctrl+D as its own download shortcut when the viewer has focus.
        try:
            page.locator("body").click(position={"x": 500, "y": 300})
            with page.expect_download(timeout=240_000) as info:
                page.keyboard.press("Control+d")
            finish_download(info.value, browser)
            return
        except Exception as exc:
            error = exc

        page.screenshot(path="onedrive-debug.png", full_page=True)
        Path("onedrive-debug.html").write_text(page.content(), encoding="utf-8")
        browser.close()
        raise RuntimeError(f"Could not start the OneDrive download: {error}")


if __name__ == "__main__":
    main()
