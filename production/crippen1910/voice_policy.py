"""Fail closed rather than silently replace the user's auditioned narrator with Edge TTS."""
import hashlib,json
from pathlib import Path


def selected_voice_ready(here: Path, shots: list[dict]) -> bool:
    path=here/'audio/voice-selection.json'
    if not path.exists():return False  # Legacy default is allowed only if no explicit user choice.
    selected=json.loads(path.read_text())
    if selected.get('provider')!='Arena speech':return False
    voice_path=here/'audio/voice.json';timing_path=here/'audio/timing.json'
    if not voice_path.exists() or not timing_path.exists():
        raise RuntimeError('SELECTED_VOICE_REQUIRED: user chose Arena voice-00; do not silently use Yunjian. Generate the selected narrator after all thirty video approvals.')
    voice=json.loads(voice_path.read_text());timing=json.loads(timing_path.read_text())
    if voice.get('provider')!='Arena speech' or voice.get('voice_id')!=selected['voice_id']:
        raise RuntimeError('SELECTED_VOICE_REQUIRED: existing narrator does not match the user selection')
    for shot in shots:
        sid=shot['id'];audio=here/'audio'/f'{sid}.mp3';row=timing.get(sid,{})
        if not audio.is_file() or not row.get('captions') or row.get('sha256')!=hashlib.sha256(audio.read_bytes()).hexdigest():
            raise RuntimeError('SELECTED_VOICE_REQUIRED: missing measured selected-voice clip '+sid)
    return True
