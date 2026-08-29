#!/usr/bin/env python3
"""Reconstruct and download a complete OneDrive playback stream from its manifest."""
from __future__ import annotations

import argparse
import json
import subprocess
import urllib.parse
import uuid
from pathlib import Path

SOURCE_ITEM_API = 'https://onedrive.live.com/_api/v2.0/drives/b!8CGwIeTW9UOMBN7bDXIXSGyINjJWHwNIrnuHIGwgU9I8I7ew4QkfQpur8Xfy2CxW/items/01BIVNJFRWZH3DX35NYFHKFWBGDFBQGPN5?tempauth=v1e.eyJzaXRlaWQiOiIyMWIwMjFmMC1kNmU0LTQzZjUtOGMwNC1kZWRiMGQ3MjE3NDgiLCJhdWQiOiIwMDAwMDAwMy0wMDAwLTBmZjEtY2UwMC0wMDAwMDAwMDAwMDAvb25lZHJpdmUubGl2ZS5jb21AOTE4ODA0MGQtNmM2Ny00YzViLWIxMTItMzZhMzA0YjY2ZGFkIiwiZXhwIjoiMTc4ODAzNTAzNCJ9.-FwFn9Y2jL64Yc6OD2-pC8tReestuGVmov19bQeQP5S9BBThm5JerY93HXuR1lV5k2wYDC2h225NWuL0inLIx1M-Mn2fHNbo5jd6JqF2_nVb5K8A9X7do2WARYeQ1meGZF020uEwIjxbenU4EeVbglk5b7ld2F_8cHlHjGAiIuJhq9L302gn3Pn7sSQGIlOQTuMp6r_wMtM0cKJ_rJT_dC7QmGPZ_9Ad2I2fmz9NnsugTnT2lR1zqsx5e4iIlhKxTp8yj8rNCQAmpgVvL19uBbjr32QY10WovQEIKIfxEEsHBwtf__yrivwxeps3cQrSzGWOmHtB5GkiSpaMhadWi4d-ryDocWAfZCnD7WzAaR5bERewDWklh0iI2MtQWu30wxG4xnsSVkolAFwacdXg9fzKUVdarGCEnT_rTXyC3WeMqfclPNI0MLF8dcTWeF2iIoj1xnmFMzf_zQXm9dZb5bBC2wwbIHAeLMeQidpESYY.rsV8h87yL5ZWS8Gp42WWO7NpbRqLzQiFRHFlgsjYPK8&version=Published&VroomTakeover=1'
PLAYBACK_SESSION_DATA = 'eyJDYW5Vc2VJdGVyYXRpdmVTZWVrRm9yTWV0YWRhdGFEZXJpdmF0aW9uIjpmYWxzZSwiRnJhbWVSYXRlMTAwMEZwcyI6Mjk5OTgsIkhhc01mcmFJbmRleCI6ZmFsc2UsIklucHV0RnJhbWVIZWlnaHRQaXhlbHMiOjEyODAsIklucHV0RnJhbWVXaWR0aFBpeGVscyI6NzIwLCJWaWRlb0JpdHJhdGVCcHMiOjUwNDQ2N30='
EXPECTED_DURATION = 2539.266


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='Retained for workflow compatibility')
    parser.add_argument('output')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.unlink(missing_ok=True)

    params = {
        'provider': 'Spo',
        'farmid': '207253',
        'docId': SOURCE_ITEM_API,
        'cTag': '"c:{3BF6C936-ADEF-4EC1-A2D8-261943033DBD},2"',
        'format': 'fmp4',
        'InputFormat': 'mp4',
        'correlationid': str(uuid.uuid4()),
        'psi': str(uuid.uuid4()),
        'pn': 'OneUpLightSpeed-LeanPlayer-Web',
        'ccat': '2',
        'PlaybackSessionData': PLAYBACK_SESSION_DATA,
        'headerOffset': '32',
        'headerSize': '2085619',
        'msvb': '4294967295',
        'altTranscode': '1',
    }
    manifest_url = (
        'https://canadaeast1-mediap.svc.ms/transform/videomanifest?'
        + urllib.parse.urlencode(params)
    )
    print('Downloading the complete 42-minute source through OneDrive videomanifest...', flush=True)
    result = subprocess.run(
        [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning',
            '-user_agent', 'Mozilla/5.0', '-headers', 'Referer: https://onedrive.live.com/\r\n',
            '-i', manifest_url, '-map', '0:v:0', '-map', '0:a:0',
            '-c', 'copy', '-movflags', '+faststart', str(output),
        ]
    )
    if result.returncode != 0 or not output.exists():
        print(f'::error title=OneDrive manifest download failed::FFmpeg exited with {result.returncode}')
        raise SystemExit(result.returncode or 1)

    probe_raw = subprocess.check_output(
        [
            'ffprobe', '-v', 'error', '-show_entries',
            'format=duration,size:stream=codec_name,width,height,r_frame_rate',
            '-of', 'json', str(output),
        ],
        text=True,
    )
    probe = json.loads(probe_raw)
    duration = float(probe['format']['duration'])
    streams = probe.get('streams', [])
    video = next((stream for stream in streams if stream.get('codec_name') == 'h264'), None)
    audio = next((stream for stream in streams if stream.get('codec_name') == 'aac'), None)
    if not video or not audio or abs(duration - EXPECTED_DURATION) > 3.0:
        print(f'::error title=Manifest media validation failed::{probe_raw}')
        raise RuntimeError('Downloaded manifest media does not match the 42:19 source')
    print(f'MANIFEST SOURCE VERIFIED: {duration:.3f}s / {probe["format"]["size"]} bytes / {video["width"]}x{video["height"]}', flush=True)


if __name__ == '__main__':
    main()
