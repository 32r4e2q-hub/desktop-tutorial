#!/usr/bin/env python3
"""Rebuild a complete OneDrive playback file from signed fMP4 segments."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

SOURCE_ITEM_API = 'https://onedrive.live.com/_api/v2.0/drives/b!8CGwIeTW9UOMBN7bDXIXSGyINjJWHwNIrnuHIGwgU9I8I7ew4QkfQpur8Xfy2CxW/items/01BIVNJFRWZH3DX35NYFHKFWBGDFBQGPN5?tempauth=v1e.eyJzaXRlaWQiOiIyMWIwMjFmMC1kNmU0LTQzZjUtOGMwNC1kZWRiMGQ3MjE3NDgiLCJhdWQiOiIwMDAwMDAwMy0wMDAwLTBmZjEtY2UwMC0wMDAwMDAwMDAwMDAvb25lZHJpdmUubGl2ZS5jb21AOTE4ODA0MGQtNmM2Ny00YzViLWIxMTItMzZhMzA0YjY2ZGFkIiwiZXhwIjoiMTc4ODAzNTAzNCJ9.-FwFn9Y2jL64Yc6OD2-pC8tReestuGVmov19bQeQP5S9BBThm5JerY93HXuR1lV5k2wYDC2h225NWuL0inLIx1M-Mn2fHNbo5jd6JqF2_nVb5K8A9X7do2WARYeQ1meGZF020uEwIjxbenU4EeVbglk5b7ld2F_8cHlHjGAiIuJhq9L302gn3Pn7sSQGIlOQTuMp6r_wMtM0cKJ_rJT_dC7QmGPZ_9Ad2I2fmz9NnsugTnT2lR1zqsx5e4iIlhKxTp8yj8rNCQAmpgVvL19uBbjr32QY10WovQEIKIfxEEsHBwtf__yrivwxeps3cQrSzGWOmHtB5GkiSpaMhadWi4d-ryDocWAfZCnD7WzAaR5bERewDWklh0iI2MtQWu30wxG4xnsSVkolAFwacdXg9fzKUVdarGCEnT_rTXyC3WeMqfclPNI0MLF8dcTWeF2iIoj1xnmFMzf_zQXm9dZb5bBC2wwbIHAeLMeQidpESYY.rsV8h87yL5ZWS8Gp42WWO7NpbRqLzQiFRHFlgsjYPK8&version=Published&VroomTakeover=1'
PLAYBACK_SESSION_DATA = 'eyJDYW5Vc2VJdGVyYXRpdmVTZWVrRm9yTWV0YWRhdGFEZXJpdmF0aW9uIjpmYWxzZSwiRnJhbWVSYXRlMTAwMEZwcyI6Mjk5OTgsIkhhc01mcmFJbmRleCI6ZmFsc2UsIklucHV0RnJhbWVIZWlnaHRQaXhlbHMiOjEyODAsIklucHV0RnJhbWVXaWR0aFBpeGVscyI6NzIwLCJWaWRlb0JpdHJhdGVCcHMiOjUwNDQ2N30='
EXPECTED_DURATION = 2539.266
LOCAL_PARTS = Path(__file__).resolve().parent / 'source_parts'
LOCAL_SIZE = 182_506_802
LOCAL_SHA256 = 'F2DAD2D76B01C5F648CCC7B6107BF50B76952237FA5EC18DB8B038C6958D54D8'
BASE = 'https://canadaeast1-mediap.svc.ms/transform/videotranscode'
COMMON = {
    'provider': 'Spo',
    'farmid': '207253',
    'docId': SOURCE_ITEM_API,
    'cTag': '"c:{3BF6C936-ADEF-4EC1-A2D8-261943033DBD},2"',
    'format': 'fmp4',
    'InputFormat': 'mp4',
    'correlationid': '7a08dcfd-c97f-4e8f-b0d3-caf1666fc1b0',
    'psi': '6ace3031-f2d4-4efc-991b-cee84d84c2e5',
    'pn': 'OneUpLightSpeed-LeanPlayer-Web',
    'ccat': '2',
    'PlaybackSessionData': PLAYBACK_SESSION_DATA,
    'headerOffset': '32',
    'headerSize': '2085619',
    'msvb': '4294967295',
    'altTranscode': '1',
}
TRACKS = {
    'video': {'quality': 'v720p', 'wsd': 149_990, 'ppd': 76_173_000, 'cacheVersion': '15'},
    'audio': {'quality': 'audhigh', 'wsd': 221_184, 'ppd': 111_981_660},
}


def make_url(track: str, part: str, segment_time: int | None = None) -> str:
    spec = TRACKS[track]
    params = dict(COMMON)
    params.update({'part': part, 'track': track, 'quality': spec['quality']})
    if 'cacheVersion' in spec:
        params['cacheVersion'] = spec['cacheVersion']
    # Window duration and presentation duration are valid only for media
    # fragments. Including them on the initialization request returns HTTP 400.
    if part == 'mediasegment':
        params.update(
            {
                'wsd': str(spec['wsd']),
                'ppd': str(spec['ppd']),
                'ppst': '0',
            }
        )
    if segment_time is not None:
        params['segmentTime'] = str(segment_time)
    return BASE + '?' + urllib.parse.urlencode(params)


def fetch(url: str, label: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0',
            'Referer': 'https://onedrive.live.com/',
            'Accept': '*/*',
        },
    )
    last_error = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = response.read()
            if not data:
                raise RuntimeError(f'empty response for {label}')
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f'failed to fetch {label}: {last_error}')


def download_track(track: str, output: Path) -> None:
    spec = TRACKS[track]
    print(f'Downloading {track} initialization segment...', flush=True)
    header = None
    header_error = None
    for part, segment_time in (('header', None), ('initsegment', None), ('header', 0)):
        try:
            candidate = fetch(
                make_url(track, part, segment_time),
                f'{track} {part}' + (f' {segment_time}' if segment_time is not None else ''),
            )
            if b'ftyp' in candidate[:128] or b'moov' in candidate:
                header = candidate
                print(f'{track}: initialization obtained via part={part}', flush=True)
                break
            header_error = RuntimeError(f'part={part} returned {len(candidate)} bytes without MP4 init atoms')
        except Exception as exc:
            header_error = exc
    starts = list(range(0, spec['ppd'], spec['wsd']))
    if header is None:
        # Some OneDrive variants prepend initialization atoms to segment zero.
        first = fetch(make_url(track, 'mediasegment', 0), f'{track} segment zero')
        if b'ftyp' in first[:128] or b'moov' in first:
            header = first
            starts = starts[1:]
            print(f'{track}: segment zero contains initialization atoms', flush=True)
        else:
            raise RuntimeError(f'no usable {track} initialization segment: {header_error}')
    print(f'Downloading {len(starts)} signed {track} media segments...', flush=True)
    with output.open('wb') as handle:
        handle.write(header)
        for batch_start in range(0, len(starts), 18):
            batch = starts[batch_start : batch_start + 18]
            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
                futures = [
                    executor.submit(
                        fetch,
                        make_url(track, 'mediasegment', segment_time),
                        f'{track} segment {segment_time}',
                    )
                    for segment_time in batch
                ]
                for future in futures:
                    handle.write(future.result())
            print(f'{track}: {min(batch_start + len(batch), len(starts))}/{len(starts)}', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='Retained for workflow compatibility')
    parser.add_argument('output')
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    video = output.parent / 'reference-video.fmp4'
    audio = output.parent / 'reference-audio.fmp4'
    for path in (output, video, audio):
        path.unlink(missing_ok=True)

    local_manifest = LOCAL_PARTS / 'manifest.json'
    if local_manifest.exists():
        manifest = json.loads(local_manifest.read_text(encoding='utf-8'))
        digest = hashlib.sha256()
        with output.open('wb') as destination:
            for part_name in manifest['parts']:
                part = LOCAL_PARTS / part_name
                print(f'Assembling uploaded source part: {part.name}', flush=True)
                with part.open('rb') as source:
                    while True:
                        block = source.read(8 * 1024 * 1024)
                        if not block:
                            break
                        destination.write(block)
                        digest.update(block)
        if output.stat().st_size != LOCAL_SIZE:
            raise RuntimeError(f'Uploaded source size mismatch: {output.stat().st_size} != {LOCAL_SIZE}')
        if digest.hexdigest().upper() != LOCAL_SHA256:
            raise RuntimeError(f'Uploaded source checksum mismatch: {digest.hexdigest()}')
        print(
            f'LOCAL UPLOAD VERIFIED: {output.stat().st_size} bytes / SHA256 {digest.hexdigest()}',
            flush=True,
        )
    else:
        try:
            download_track('video', video)
            download_track('audio', audio)
        except Exception as exc:
            print(f'::error title=OneDrive segment reconstruction failed::{type(exc).__name__}: {exc}')
            raise
        subprocess.run(
            [
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning',
                '-i', str(video), '-i', str(audio), '-map', '0:v:0', '-map', '1:a:0',
                '-c', 'copy', '-movflags', '+faststart', str(output),
            ],
            check=True,
        )
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
    if len(streams) < 2 or abs(duration - EXPECTED_DURATION) > 4.0:
        print(f'::error title=Reconstructed media validation failed::{probe_raw}')
        raise RuntimeError('Reconstructed media does not match the 42:19 source')
    original_size = output.stat().st_size
    print(
        f'UPLOADED SOURCE VERIFIED: {duration:.3f}s / {original_size} bytes',
        flush=True,
    )


if __name__ == '__main__':
    main()
