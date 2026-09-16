# 把这个网关接进 Windows 版 Hermes（Hermes Desktop）

> 面向"不想读文档、只想照着点"的情况：**从上到下 6 步**，每步一个动作。
> 每步末尾的「期望」不满足就别往下走，回来对第 5 节的坑表。

Hermes 是 Nous Research 的开源 agent，桌面版和 CLI **共用同一份 `config.yaml`**，
接自定义端点靠的是 `provider: custom` + `base_url` + `api_key`。
我们这把 `base_url` 正好就是本网关的 `/v1`（OpenAI 兼容）。

---

## 1. 先决条件：网关这边要满足两条

| 检查 | 怎么验 | 不满足时 |
|---|---|---|
| bundle ≥ **1.3.0**（tools 透传） | 开 `https://<你的worker>.<子域>.workers.dev/healthz` 看 `"version"` | 重贴 `bundle/worker.js`（见 README §3′），**Hermes 不带 tools 会"光说不做"** |
| 第一个能用的家是 OpenAI 风格 | `providers[0].id` 不是 `gemini`/`cloudflare` | `PROVIDER_ORDER` 改成 `openrouter,agnes,mistral,gemini` |

第二条的原因：**`gemini` 那一家不做 function calling 翻译**，带 `tools` 时会被忽略。
Hermes 每一步都要工具调用，所以让 `auto` 的第一跳落在 OpenAI 兼容的那几家上。

## 2. 装 Hermes Desktop

官网下载页：<https://hermes-agent.nousresearch.com/desktop> → Windows 下 `Hermes-Setup.exe`（Win10/11）→ 双击装完启动一次，让它把配置目录建出来，然后**退出**。

## 3. 填配置（绕开 GUI 那个坑）

Windows 上配置文件在：

```
%LOCALAPPDATA%\hermes\config.yaml        （即 C:\Users\<你的用户名>\AppData\Local\hermes\config.yaml）
```

开始菜单/资源管理器地址栏粘上面这行 → 回车 → 用**记事本**打开 → 整份替换成下面这段 → 保存：

```yaml
# ── 主模型：走你自己的 zeroroute-lite 网关 ──
model:
  default: agnes/agnes-2.5-flash          # 想"哪家都行"就填 auto
  provider: custom
  base_url: https://<你的worker>.<子域>.workers.dev/v1
  api_key: <你的 ROUTER_API_KEY>           # Cloudflare 里那把，别写进聊天/截图
  api_mode: chat_completions               # 本网关只做 chat/completions

# ── 把网关的每个 provider 暴露成可切换的"模型" ──
custom_providers:
  - name: zeroroute-lite
    base_url: https://<你的worker>.<子域>.workers.dev/v1
    api_key: <你的 ROUTER_API_KEY>
    context_length: 200000                 # 桌面版对 custom provider 有读错窗口的 bug，显式写死
    models:
      - auto                               # 按 PROVIDER_ORDER 轮转 + 自动降级
      - agnes/agnes-2.5-flash              # 512K 窗口、免费、慢
      - openrouter/openrouter/free         # 快，随机落到某个 :free 模型
      - mistral/mistral-small-latest       # 备用
      - gemini/gemini-3.5-flash-lite       # ⚠️ 这一跳没有 tools，只适合纯聊天

providers: {}                              # 必须清空，否则与 custom_providers 冲突
```

`model.default` 与 `custom_providers[].models` 的关系：Hermes 的模型选择器**只列 `models` 里写过的项**，
所以那五行就是你以后在 Hermes 里按 `/model` 能挑的路由。这就是"把网关的降级链变成 Hermes 的模型列表"。

> ⚠️ 已知 bug（2026-06 实测）：**桌面版 GUI 里填自定义 API 不生效**（表单写进去了但没落到运行时配置）。
> 所以第 3 步用文件而不是 GUI。若你已经在 GUI 里填过，改完后按下面命令强制重选一次。

## 4. 让它生效 + 验证

在 PowerShell 里（开始菜单搜 PowerShell）依次：

```powershell
hermes model                       # 交互菜单里选 Custom endpoint → zeroroute-lite → agnes/agnes-2.5-flash
hermes config get model.base_url   # 期望打印出你的 workers.dev 地址
```

然后**回 Cloudflare 控制台确认网关真的带得动 tools**（这一步与 Hermes 无关，是排掉后患）：
F12 → `>` 里粘这一行（把 `KEY` 换成你的 `ROUTER_API_KEY`）：

```js
fetch("/v1/chat/completions",{method:"POST",headers:{"content-type":"application/json",authorization:"Bearer KEY"},body:JSON.stringify({model:"agnes/agnes-2.5-flash",messages:[{role:"user",content:"北京今天天气怎么样"}],tools:[{type:"function",function:{name:"get_weather",description:"查城市天气",parameters:{type:"object",properties:{city:{type:"string"}},required:["city"]}}}]})}).then(async r=>{const j=await r.json();console.log("HTTP",r.status,"| finish:",j.choices?.[0]?.finish_reason,"| tool_calls:",JSON.stringify(j.choices?.[0]?.message?.tool_calls||null))})
```

**期望**：`HTTP 200 | finish: tool_calls | tool_calls: [{"id":…,"function":{"name":"get_weather","arguments":"{\"city\":\"北京\"}"}}]`
—— 出现 `tool_calls` 才说明 Hermes 能在你这套东西上真正动手；只出现一句"我没法查天气"就说明这一跳不支持 tools。

最后在 Hermes 里发一句需要工具的话（例如"列出当前目录里的文件"）：**它应该去执行工具而不是只回一段文字**。

## 5. 坑表（按出现频率排）

| 现象 | 原因 / 处置 |
|---|---|
| 保存了但还走默认模型 / 报鉴权 | GUI 表单那个 bug；只认 `config.yaml` + `hermes model` 重选。对话里先 `/stop` 中断当前模型再重选 |
| Hermes 光描述动作、不执行 | 那一跳不支持 tools：把 `model.default` 换成 `openrouter/openrouter/free` 或 `agnes/...`；或按第 1 节调 `PROVIDER_ORDER` |
| 长任务超时/断流 | Hermes 侧 `setx HERMES_STREAM_READ_TIMEOUT 300`（秒，重开终端生效）；网关侧 `TIMEOUT_MS=60000`（你已经设过） |
| `401 invalid router api key` | 网关的 `ROUTER_API_KEY` 和 config.yaml 里 `api_key` 不一致（轮换过的话最容易漏改） |
| 上下文窗口显示得比预期小一半 | Windows 桌面版对 custom provider 读的是家族默认值，不是你的配置：`context_length` 已在 YAML 里显式写死 |
| 发图过去模型说"我看不到图" | 有意为之：`image_url` 内容块会被丢掉，本网关只做文字 |
| 429 rate limited | 免费档 RPM，等 60 秒或让 `auto` 降级；频繁出现就把 `RATE_LIMIT_RPM` 抬一档 |

## 6. 两句实话

1. **`config.yaml` 里是明文 key**：别把它贴到网上/截进图里。真泄露了就回 Cloudflare 改 `ROUTER_API_KEY` 的值并重新部署（10 秒，客户端只改一处）。
2. Hermes 是**会真的执行命令**的 agent，而它背后的模型此刻是"几家免费档轮流转、谁挂了换谁"。
   质量会跳变，免费条款也不鼓励这么用。别在重要机器/敏感目录上放权限，把它当实验台用。
