
import pathlib, base64
out_dir=pathlib.Path(__file__).parent
chunks=sorted(out_dir.glob('chunk_*.b64'))
data=b''.join(base64.b64decode(p.read_text()) for p in chunks)
(pathlib.Path(__file__).parent.parent/'dbcooper_22M_direct_reassembled.mp4').write_bytes(data)
print(f"Reassembled {len(data)} bytes")
