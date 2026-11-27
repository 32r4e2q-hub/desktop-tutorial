# 事故复盘：参考图修订号导致 30 镜被判「与分镜不符」（2026-11-27）

## 现象

两次 `mode=render` 出片失败：

1. 第一次：`Render requested but these clips are not completed: S01…S30`。
2. 恢复 provenance 之后：`S01: request hash differs from the approved storyboard`。

素材本身没有消失，Agnes 回执（video_url + sha256 + bytes）都在 `results.json` 里。

## 两个独立原因

### 1. 分支被重置，`results.json` 退回只含 S18/S27 的版本

第一次失败时，远端 `results.json` 只有 `S18`、`S27` 两条记录。30 镜的回执一度存在于提交 `f0f28b3`，
后续的 S18/S27 单镜重做把文件覆盖成只剩两镜。渲染闸门要 30 镜全部 `completed`，于是直接拒绝。

处理：从 `f0f28b3` 取回 30 镜回执，把 S18/S27 换成重做后的新回执（sha256 变了，符合「真重做」），
逐条核对 `status=completed` 且 `video_url`/`sha256`/`bytes` 齐全。

### 2. 参考图 URL 带提交号，改 `revision.txt` 等于改全部 30 镜的请求

`generate.py` 拼参考图 URL 用的是 `reference/revision.txt` 钉的提交号：

```
https://raw.githubusercontent.com/<repo>/<revision>/production/<slug>/reference/S01.png
```

为 S27 补一张空白横线纸参考图 S11 时，修订号从 `711c447e…` 前移到 `28ceac9c…`。
PNG 字节完全没变，但 30 镜的 URL 前缀全变了，旧的 `request_hash` 把整条 URL 算进去，
闸门于是把已生成的素材判成不符合分镜。

试过两条错路（都已回退）：

- **按图片登记各自的提交号**：S09 在两批素材里分别用了两个提交号（S17/S21 用旧的、S18 用新的），
  单值登记无法同时复现，仍有 2 镜对不上。
- **只改哈希算法不重算 `results.json`**：`request_hash` 是提交时写进回执的，改了算法但回执里还是旧值，照样不一致。

最终做法：`request_hash()` 把 `images` 规整成「repo 内路径 + approvals.json 的 sha256」再哈希。
提交号不参与，图片内容或批准记录真变了哈希仍会变；`results.json` 的 30 条 `request_hash` 按同一算法
重算并记入 `previous_request_hashes` 留痕。

## 验证

- 同一镜在 `revision=28ceac9c…` 与 `revision=000000…` 两种情况下哈希相同（修订号无关）。
- 30 镜 `request_hash` 与 `results.json` 全部一致（0 条不符）。
- `preflight.py` READY（14 张参考图全部 approved）；`generate.py --validate --clips-only` VALID；`pytest` 113 passed。

## 教训

1. **不要用提交号当素材身份**。素材身份只能是内容哈希；提交号只是取文件的地址。
2. 新增参考图会让 `revision.txt` 前移，这是正常操作；它不该触发全部镜头重做。
3. `results.json` 是出片的唯一凭据，单镜重做时必须合并而不是覆盖已有回执。
