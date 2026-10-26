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


def test_shallow_checkpoint_rebases_after_concurrent_remote_update(tmp_path):
    """Depth one still retains the common tip needed by checkpoint fetch/rebase."""
    if not shutil.which('git'):
        pytest.skip('git required')
    branch = 'arena/3c0c229a-desktop-tutorial'
    remote, writer, client = [tmp_path/name for name in ('remote.git','writer','client')]

    def git(cwd, *args, check=True):
        return subprocess.run(['git', *args], cwd=cwd, check=check, capture_output=True, text=True)

    git(tmp_path, 'init','--bare',str(remote))
    git(tmp_path, 'init','-b',branch,str(writer))
    for repo in (writer,):
        git(repo,'config','user.name','Fixture')
        git(repo,'config','user.email','fixture@example.invalid')
    (writer/'base.txt').write_text('base')
    git(writer,'add','.'); git(writer,'commit','-m','base')
    (writer/'base.txt').write_text('current source plan')
    git(writer,'commit','-am','current plan')
    git(writer,'remote','add','origin',remote.as_uri())
    git(writer,'push','-u','origin',branch)
    git(tmp_path,'clone','--depth','1','--branch',branch,remote.as_uri(),str(client))
    assert git(client,'rev-parse','--is-shallow-repository').stdout.strip() == 'true'
    git(client,'config','user.name','Fixture')
    git(client,'config','user.email','fixture@example.invalid')
    (writer/'upstream.txt').write_text('concurrent review')
    git(writer,'add','.'); git(writer,'commit','-m','concurrent review')
    git(writer,'push','origin',branch)
    (client/'qa.txt').write_text('new checkpoint receipt')
    git(client,'add','.'); git(client,'commit','-m','checkpoint')
    assert git(client,'push','origin',branch,check=False).returncode != 0
    git(client,'fetch','origin',branch)
    git(client,'rebase','FETCH_HEAD')
    git(client,'push','origin',branch)
    assert (client/'qa.txt').read_text() == 'new checkpoint receipt'
    assert (client/'upstream.txt').read_text() == 'concurrent review'
