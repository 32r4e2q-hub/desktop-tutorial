"""Generation setup must not hang on apt or require fonts for source inspection."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'production/gacy1978'


def test_generation_setup_avoids_apt_and_bounds_downloads():
    paths = [ROOT/'.github/workflows/gacy1978-cogvideox-gen.yml',
             PROJECT/'workflows/gacy1978-cogvideox-gen.yml']
    for path in paths:
        text = path.read_text()
        assert 'sudo apt-get' not in text
        assert 'fetch-depth: 1' in text
        assert 'fetch-depth: 0' not in text
        assert 'timeout-minutes: 8' in text
        assert 'imageio-ffmpeg==0.6.0' in text
        assert 'timeout-minutes: 12' in text
        assert 'timeout-minutes: 5' in text
        assert 'timeout-minutes: 2' in text
        assert 'PIP_DEFAULT_TIMEOUT:' in text
        assert 'PIP_RETRIES:' in text
        assert 'get_ffmpeg_exe()' in text


def test_bundled_ffmpeg_and_av_inspect_source_without_ffprobe_or_fonts(tmp_path, monkeypatch):
    imageio = pytest.importorskip('imageio_ffmpeg')
    pytest.importorskip('av')
    spec = importlib.util.spec_from_file_location('gacy1978_setup_media', PROJECT/'media.py')
    media = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(media)
    bin_dir = tmp_path/'bin'
    bin_dir.mkdir()
    (bin_dir/'ffmpeg').symlink_to(imageio.get_ffmpeg_exe())
    monkeypatch.setenv('PATH', str(bin_dir)+os.pathsep+os.environ.get('PATH',''))
    actual_which = shutil.which
    monkeypatch.setattr(media.shutil, 'which', lambda name: None if name=='ffprobe' else actual_which(name))
    source = tmp_path/'test-source.mp4'
    subprocess.run([str(bin_dir/'ffmpeg'), '-v','error','-f','lavfi','-i',
                    'testsrc2=size=640x360:rate=10','-t','4.5','-c:v','libx264',
                    '-preset','ultrafast','-pix_fmt','yuv420p',str(source)], check=True)
    info = media.inspect_clip(source, tmp_path/'qa', 'SETUP')
    assert info['decoded_ok'] is True
    assert info['width'] == 640
    assert info['frames'] == 45
    assert info['fps'] == 10
    assert (tmp_path/'qa/SETUP.jpg').is_file()
