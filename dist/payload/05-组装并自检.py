# 各段都报 ✓ 之后运行：整包校验 → 解出项目 → 用仓库自带的校验器自检
import base64, hashlib, io, lzma, pathlib, tarfile
N, WHOLE_SHA = 4, "57f9495af201"
blob = ''.join(''.join(pathlib.Path(f'/content/p{i}.b64').read_text().split()) for i in range(1, N + 1))
raw = base64.b64decode(blob)                     # 这是 xz 压缩后的整包字节
assert hashlib.sha256(raw).hexdigest()[:12] == WHOLE_SHA, "整包校验不过：有一段贴坏了，回面板重贴那一段"
data = lzma.decompress(raw)
tarfile.open(fileobj=io.BytesIO(data)).extractall('/content/proj')
files = [p for p in pathlib.Path('/content/proj').rglob('*') if p.is_file()]
print(f"解出 {len(files)} 个文件 → /content/proj（xz {len(raw)} → {len(data)} 字节）· 包体完好")
# 注意：此刻配音还没生成（6 段 mp3 不在这个包里，下一格用 edge-tts 现做），
# 所以这里不跑 generate.py --validate —— 它会在配音就位后由下一格自动跑。
