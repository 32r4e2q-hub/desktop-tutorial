#!/usr/bin/env bash
# ipcheck.sh —— 线路"纯净度"体检（多源交叉验证，全部免费、无需 API key）
#
# 用法:
#   ./ipcheck.sh                      # 检测当前默认出口
#   ./ipcheck.sh -x socks5://127.0.0.1:1080   # 走指定代理检测
#   ./ipcheck.sh -i 1.2.3.4           # 直接查某个 IP（不走该 IP 出口）
#
# 判读标准（业界通用区间）:
#   ASN type = ISP / Consumer      → 基线  0-20   最优
#   ASN type = Mobile / Cellular   → 基线  0-30   很好
#   ASN type = Business            → 基线 20-40   可用
#   ASN type = HOSTING / Datacenter→ 基线 50-85   高风控，多账号场景不可用
#
set -uo pipefail

PROXY=""
TARGET_IP=""
while getopts "x:i:h" opt; do
  case $opt in
    x) PROXY="--proxy $OPTARG" ;;
    i) TARGET_IP="$OPTARG" ;;
    h) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "用法: $0 [-x proxy_url] [-i ip]"; exit 1 ;;
  esac
done

CURL="curl -s --max-time 12 $PROXY"

C_R=$'\e[31m'; C_G=$'\e[32m'; C_Y=$'\e[33m'; C_B=$'\e[36m'; C_0=$'\e[0m'; C_BOLD=$'\e[1m'

hr() { printf '%.0s─' {1..62}; echo; }

echo
echo "${C_BOLD}线路纯净度体检${C_0}  $(date '+%Y-%m-%d %H:%M:%S')"
[ -n "$PROXY" ] && echo "代理: ${PROXY#--proxy }"
hr

# ---------- 1. 取出口 IP ----------
if [ -n "$TARGET_IP" ]; then
  IP="$TARGET_IP"
  echo "查询指定 IP: ${C_BOLD}$IP${C_0}"
else
  IP=$($CURL https://api.ipify.org 2>/dev/null)
  [ -z "$IP" ] && IP=$($CURL https://ifconfig.me/ip 2>/dev/null)
  [ -z "$IP" ] && IP=$($CURL https://icanhazip.com 2>/dev/null | tr -d '\n')
  if [ -z "$IP" ]; then
    echo "${C_R}✗ 无法获取出口 IP —— 检查网络或代理配置${C_0}"
    exit 1
  fi
  echo "出口 IP: ${C_BOLD}$IP${C_0}"
fi
hr

# ---------- 2. ipapi.is：最关键，给 ASN type + 各类布尔标记 ----------
echo "${C_B}[1/4] ipapi.is —— ASN 分类 & 代理检测${C_0}"
$CURL "https://api.ipapi.is/?q=$IP" 2>/dev/null | python3 -c '
import json,sys
G="\033[32m"; R="\033[31m"; Y="\033[33m"; B="\033[1m"; Z="\033[0m"
try:
    d=json.load(sys.stdin)
except Exception:
    print("  (查询失败 / 限流)"); sys.exit()

asn=d.get("asn") or {}
co =d.get("company") or {}
loc=d.get("location") or {}

atype=(asn.get("type") or co.get("type") or "unknown").lower()
org  = asn.get("org") or co.get("name") or "?"
asnum= asn.get("asn") or "?"

# ASN 类型 → 基线分
table={
 "isp":        (G,"消费级 ISP","0-20  最优"),
 "business":   (Y,"商业宽带",  "20-40 可用"),
 "education":  (G,"教育网",    "0-25  良好"),
 "government": (G,"政府",      "0-25  良好"),
 "hosting":    (R,"机房/云",   "50-85 高风控"),
 "banking":    (Y,"金融",      "-"),
}
c,label,base = table.get(atype,(Y,atype,"未知"))

print(f"  AS{asnum}  {org}")
print(f"  类型: {c}{B}{label}{Z}   风控基线: {c}{base}{Z}")
print(f"  位置: {loc.get('country','?')} / {loc.get('city','?')}")

flags=[]
def chk(k,text,bad=True):
    if d.get(k) is True:
        flags.append((R if bad else Y)+"⚠ "+text+Z)
chk("is_datacenter","数据中心 IP")
chk("is_vpn","VPN 出口")
chk("is_proxy","代理")
chk("is_tor","Tor 出口节点")
chk("is_abuser","历史滥用记录")
chk("is_crawler","爬虫")
if d.get("is_mobile") is True:
    flags.append(G+"✓ 移动运营商（基线低，利好）"+Z)

if flags:
    print("  标记:")
    for f in flags: print("    "+f)
else:
    print(f"  标记: {G}✓ 无异常标记{Z}")
' 2>/dev/null || echo "  (不可达)"
echo

# ---------- 3. ipquery.io：独立第二源 ----------
echo "${C_B}[2/4] ipquery.io —— 独立交叉验证${C_0}"
$CURL "https://api.ipquery.io/$IP" 2>/dev/null | python3 -c '
import json,sys
G="\033[32m"; R="\033[31m"; Z="\033[0m"
try: d=json.load(sys.stdin)
except Exception: print("  (查询失败)"); sys.exit()
isp=d.get("isp") or {}
risk=d.get("risk") or {}
print(f"  ISP: {isp.get('"'"'isp'"'"','"'"'?'"'"')}  (AS: {isp.get('"'"'asn'"'"','"'"'?'"'"')})")
score=risk.get("risk_score")
if score is not None:
    c = G if score<=20 else ("\033[33m" if score<=50 else R)
    print(f"  风险分: {c}{score}/100{Z}")
hits=[k.replace("is_","") for k in ("is_mobile","is_vpn","is_tor","is_proxy","is_datacenter") if risk.get(k)]
print(f"  命中: {(R+', '.join(hits)+Z) if hits else G+'"'"'无'"'"'"+Z}")
' 2>/dev/null || echo "  (不可达)"
echo

# ---------- 4. AbuseIPDB 网页版（无需 key，看是否有举报历史） ----------
echo "${C_B}[3/4] 滥用举报历史${C_0}"
AB=$($CURL -H "User-Agent: Mozilla/5.0" "https://www.abuseipdb.com/check/$IP" 2>/dev/null \
     | grep -oE 'reported [0-9,]+ times|was not found in our database' | head -1)
if [ -n "$AB" ]; then
  case "$AB" in
    *"not found"*) echo "  ${C_G}✓ AbuseIPDB 无记录${C_0}" ;;
    *)             echo "  ${C_R}⚠ AbuseIPDB: $AB${C_0}" ;;
  esac
else
  echo "  (需手动查看 https://www.abuseipdb.com/check/$IP)"
fi
echo

# ---------- 5. DNSBL 黑名单抽查 ----------
echo "${C_B}[4/4] DNSBL 黑名单抽查${C_0}"
if command -v dig >/dev/null 2>&1 && [[ "$IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  REV=$(echo "$IP" | awk -F. '{print $4"."$3"."$2"."$1}')
  HIT=0
  for bl in zen.spamhaus.org bl.spamcop.net dnsbl.sorbs.net b.barracudacentral.org; do
    r=$(dig +short +time=3 +tries=1 "$REV.$bl" A 2>/dev/null | head -1)
    if [ -n "$r" ]; then echo "  ${C_R}⚠ 命中 $bl  ($r)${C_0}"; HIT=1; fi
  done
  [ $HIT -eq 0 ] && echo "  ${C_G}✓ 4 个主流黑名单均未命中${C_0}"
else
  echo "  (需要 dig: apt install dnsutils)"
fi

hr
cat <<'TIP'
判读速查:
  ASN type = ISP / Mobile        → 可用于养号、注册
  ASN type = Business            → 一般服务可用，敏感平台谨慎
  ASN type = HOSTING/Datacenter  → 多账号/养号场景基本无解，换 ASN 而非换 IP
命中任一 VPN/Proxy/Abuser 标记 → 该线路已被打标，换线
TIP
echo
