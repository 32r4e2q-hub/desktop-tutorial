import os
import sys
import time
import requests
import traceback

print("=== 脚本启动 ===", flush=True)

api_key = os.getenv("ZHIPUAI_API_KEY")
prompt = os.getenv("INPUT_PROMPT")

if not prompt:
    if os.path.exists("trigger_video.txt"):
        with open("trigger_video.txt", "r", encoding="utf-8") as f:
            prompt = f.read().strip()

if not prompt:
    prompt = "一只可爱的小猫咪在阳光下的花园里捉蝴蝶，草地，电影质感，超高清"

if not api_key:
    print("❌ 错误: 未检测到 ZHIPUAI_API_KEY！请确认在 GitHub 仓库 Settings -> Secrets 中添加了该密钥！", flush=True)
    sys.exit(1)

masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
print(f"🔑 检测到 API_KEY: {masked}", flush=True)

try:
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=api_key)
    print(f"🎬 正在向智谱提交任务，Prompt: {prompt}", flush=True)
    
    response = client.videos.generations(
        model="cogvideox-flash",
        prompt=prompt,
        quality="speed"
    )
    print(f"原始提交响应: {response}", flush=True)
    task_id = getattr(response, "id", None) or response.get("id")
    print(f"✅ 任务提交成功！Task ID: {task_id}", flush=True)
except Exception as e:
    print(f"❌ 任务提交异常: {e}", flush=True)
    traceback.print_exc()
    sys.exit(1)

print("⏳ 正在轮询视频状态（约需 50~70 秒，每 8 秒查询一次）...", flush=True)
start_time = time.time()
while True:
    try:
        result = client.videos.retrieve_videos_result(id=task_id)
        status = getattr(result, "task_status", None)
        if status is None and isinstance(result, dict):
            status = result.get("task_status")
        
        elapsed = int(time.time() - start_time)
        print(f"[{elapsed}s] 当前状态: {status}", flush=True)

        if status == "SUCCESS":
            video_result = getattr(result, "video_result", None) or result.get("video_result")
            video_url = None
            if video_result and len(video_result) > 0:
                first = video_result[0]
                video_url = getattr(first, "url", None) or (first.get("url") if isinstance(first, dict) else None)
            
            print(f"\n==========================================", flush=True)
            print(f"🎉 视频生成成功！渲染总耗时: {elapsed} 秒", flush=True)
            print(f"🔗 视频直接下载地址（30天有效）:\n{video_url}", flush=True)
            print(f"==========================================\n", flush=True)
            
            if video_url:
                print("⬇️ 正在下载视频文件保存到 output_video.mp4...", flush=True)
                res = requests.get(video_url, timeout=120)
                with open("output_video.mp4", "wb") as f:
                    f.write(res.content)
                print(f"💾 视频已保存为 output_video.mp4 (文件大小: {len(res.content)} 字节)", flush=True)
            break
        elif status == "FAIL":
            print(f"\n❌ 智谱云端渲染失败: {result}", flush=True)
            sys.exit(1)
        else:
            time.sleep(8)
    except Exception as err:
        print(f"⚠️ 查询出现异常: {err}", flush=True)
        traceback.print_exc()
        time.sleep(8)
