# 第 {IDX} 格：把 dist/payload/p{IDX}.b64 的**全部内容**粘进下面三引号之间，然后运行本格
import hashlib
EXPECT_CHARS = {CHARS}
EXPECT_SHA = "{SHA12}"
PART = """
（把 p{IDX}.b64 整段粘到这里，替换本行）
"""
blob = ''.join(PART.split())
open('/content/p{IDX}.b64', 'w').write(blob)
got = hashlib.sha256(blob.encode()).hexdigest()[:12]
ok = len(blob) == EXPECT_CHARS and got == EXPECT_SHA
print(f"第 {IDX} 段：{len(blob)} 字符 / {got}",
      "✓ 对上了" if ok else f"✗ 应为 {EXPECT_CHARS} 字符 / {EXPECT_SHA} —— 回面板把 p{IDX}.b64 整段重新复制一次")
assert ok, "这段没对上，先重贴这段再往下走"
