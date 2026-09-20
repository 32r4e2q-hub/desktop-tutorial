# 本地 runner（自托管出片机）· 三分钟上手

这台文件夹里的东西只为一件事服务：**把出片从 GitHub 的机器上搬到你自己的机器上**。
仓库已经转成私有了，所以不再有 2000 分钟/月的额度焦虑——自托管的分钟数不计费。

完整背景、原理、为什么顺序不能反，见仓库根目录的
[`转私有与自托管Runner手册.md`](../转私有与自托管Runner手册.md)。
**这里只给最短路径。**

---

## 一、在你自己的机器上跑一句

机器要求是 **Linux 或 WSL2 里的 Ubuntu**（Windows 原生跑不了：出片脚本是 bash +
`apt` + Linux 字体路径）。打开终端：

```bash
git clone https://github.com/32r4e2q-hub/desktop-tutorial.git   # 已有就 git pull
cd desktop-tutorial
bash runner/setup-runner.sh
```

脚本会按顺序做 6 件事，每一步都可以单独跳过：

| 步骤 | 做什么 | 跳过用什么参数 |
|---|---|---|
| 0 | 认系统/架构/磁盘（Windows 原生直接拦下） | — |
| 1 | **查仓库是不是私有**（公开就拒绝注册） | —— 这条不能跳过 |
| 2 | 装 git / python3 / ffmpeg / Noto CJK 中文字体 | `--no-deps` |
| 3 | 下载 runner 安装包并**验校验和** | 已装过会自动跳过 |
| 4 | 预下载 whisper 模型 base + small（~600 MB） | `--no-models` |
| 5 | 注册到仓库（token 现场取，不落盘） | `--no-register` |
| 6 | 装成 systemd 服务（开机自启） | `--no-service` |

想连开关一起拨（gh 已登录且是仓库 admin）：

```bash
bash runner/setup-runner.sh --set-switch
```

它会在确认 runner **online** 之后，把仓库变量一次设好：

| 变量 | 值 | 作用 |
|---|---|---|
| `RUNNER_LABEL` | `self-hosted` | 9 个工作流的 `runs-on` 一起切到你的机器 |
| `WHISPER_CACHE_DIR` | `~/.cache/whisper` | 模型只下一次，之后每个 job 复用 |
| `HF_ENDPOINT` / `HF_HUB_DISABLE_XET` | 仅 `--hf-mirror` 时才设 | 连不上 huggingface.co 时走镜像 |

---

## 二、验证

```bash
bash runner/selfcheck.sh     # 只读自检，不改任何东西；有 ✗ 就照提示修
```

然后 GitHub 上：

1. **Settings → Actions → Runners** 看到这台机器是绿色 **Idle**；
2. **Actions → 离线自检 → Run workflow** —— 日志开头会打印 `Runner name: <你的机器名>`；
3. 真出一次片：**Actions → 解说短片出片 → `project` 填 `dahlia`**；
4. 看 **Billing → Actions**：分钟数**没有**增加，说明真的跑在自己的机器上。

---

## 三、后悔了

| 想怎样 | 怎么做 |
|---|---|
| 临时借 GitHub 的机器 | 删掉仓库变量 `RUNNER_LABEL`，一切回到 `ubuntu-latest` |
| 机器休眠/关机时别排队 | 同上，或者把机器开着——自托管的代价就是"机器得醒着" |
| 彻底卸掉 | `bash runner/uninstall-runner.sh`（`--purge` 连目录一起删） |
| 仓库要改回公开 | **先卸掉 runner 再改公开**，顺序不能反 |

---

## 关于 token 的一句话

注册 token / remove token 都只从 GitHub **现场取一次**（1 小时有效），
脚本拿到就用、用完 `unset`，**不写文件、不打日志、不进 Git**。
gh 自动取不到时，脚本会给你确切的页面地址，让你自己复制、以不回显方式粘贴。

**不要把 token 贴进任何聊天框**（包括和我对话时）——
这也是为什么我（代理）没法替你注册：GitHub App 没有 `administration` 权限，
既取不到注册 token 也写不了仓库变量。注册这一步只能在你自己的机器上完成。

---

## 文件

| 文件 | 作用 |
|---|---|
| `setup-runner.sh` | 一键安装 + 注册 + 装服务（幂等，可反复跑） |
| `selfcheck.sh` | 只读自检：系统 / 依赖 / 字体 / 服务 / 模型 / 磁盘 / 仓库，退出码 0 才可出片 |
| `uninstall-runner.sh` | 反注册 + 停服务 + 可选删目录 |
