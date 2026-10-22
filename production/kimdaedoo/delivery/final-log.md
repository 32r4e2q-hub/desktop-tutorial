# 出片日志（success，2026-10-22T08:34:54Z）

```
[finalize] 1/7 下载 30 镜并校验 SHA-256 …
[finalize]   S01 OK 2,564,031 B
[finalize]   S02 OK 4,654,190 B
[finalize]   S03 OK 2,076,351 B
[finalize]   S04 OK 2,107,612 B
[finalize]   S05 OK 1,330,684 B
[finalize]   S06 OK 2,510,873 B
[finalize]   S07 OK 7,777,906 B
[finalize]   S08 OK 2,564,611 B
[finalize]   S09 OK 2,460,565 B
[finalize]   S10 OK 2,054,109 B
[finalize]   S11 OK 1,862,446 B
[finalize]   S12 OK 1,950,285 B
[finalize]   S13 OK 2,144,324 B
[finalize]   S14 OK 2,439,996 B
[finalize]   S15 OK 3,304,333 B
[finalize]   S16 OK 1,745,442 B
[finalize]   S17 OK 1,945,611 B
[finalize]   S18 OK 2,138,008 B
[finalize]   S19 OK 2,618,157 B
[finalize]   S20 OK 1,763,497 B
[finalize]   S21 OK 2,246,679 B
[finalize]   S22 OK 2,499,962 B
[finalize]   S23 OK 1,401,172 B
[finalize]   S24 OK 2,267,678 B
[finalize]   S25 OK 2,137,011 B
[finalize]   S26 OK 1,991,965 B
[finalize]   S27 OK 2,640,011 B
[finalize]   S28 OK 2,636,025 B
[finalize]   S29 OK 3,862,554 B
[finalize]   S30 OK 3,039,224 B
[finalize] 2/7 edge-tts 逐镜配音（zh-CN-YunjianNeural, pitch -4Hz）…
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.wav
[finalize]   S01 4.20s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S02.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S02.wav
[finalize]   S02 2.83s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S03.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S03.wav
[finalize]   S03 3.74s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S04.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S04.wav
[finalize]   S04 3.25s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S05.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S05.wav
[finalize]   S05 3.37s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S06.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S06.wav
[finalize]   S06 3.83s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S07.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S07.wav
[finalize]   S07 3.32s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S08.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S08.wav
[finalize]   S08 2.95s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S09.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S09.wav
[finalize]   S09 3.77s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S10.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S10.wav
[finalize]   S10 4.02s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S11.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S11.wav
[finalize]   S11 3.91s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S12.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S12.wav
[finalize]   S12 3.66s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S13.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S13.wav
[finalize]   S13 3.04s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S14.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S14.wav
[finalize]   S14 3.67s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S15.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S15.wav
[finalize]   S15 3.62s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S16.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S16.wav
[finalize]   S16 3.50s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S17.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S17.wav
[finalize]   S17 3.35s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S18.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S18.wav
[finalize]   S18 3.84s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S19.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S19.wav
[finalize]   S19 4.09s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S20.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S20.wav
[finalize]   S20 3.51s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S21.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S21.wav
[finalize]   S21 4.00s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S22.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S22.wav
[finalize]   S22 4.05s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S23.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S23.wav
[finalize]   S23 3.33s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S24.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S24.wav
[finalize]   S24 3.72s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S25.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S25.wav
[finalize]   S25 4.20s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S26.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S26.wav
[finalize]   S26 3.32s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S27.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S27.wav
[finalize]   S27 3.82s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S28.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S28.wav
[finalize]   S28 3.85s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S29.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S29.wav
[finalize]   S29 3.57s @ +12%
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S30.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S30.wav
[finalize]   S30 4.05s @ +12%
[finalize]   解说总时长 109.4s；成片 180s；平均 305 字/分钟
[finalize] 3/7 生成字幕 …
[finalize] 4/7 生成原创悬疑 BGM …
Generated original thriller music loop: /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/bgm.wav (180.00s)
[finalize]   BGM bgm.wav 31.8 MB / 180s
[finalize] 5/7 合成成片 …
[finalize] $ ffmpeg -y -v warning -stats -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/bgm.wav -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.wav -i /home/runner/work/desktop-tutorial/de
[finalize]   合成完成 214s → 126.3 MB
[finalize] 6/7 程序化 QC …
[finalize] $ ffprobe -v error -show_streams -show_format -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/final.mp4
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/final.mp4 -vf select='not(mod(n,337))',scale=480:270,tile=4x4 -frames:v 1 /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-fina
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/final.mp4 -vf select='eq(n,90)+eq(n,270)+eq(n,450)+eq(n,630)+eq(n,810)+eq(n,990)+eq(n,1170)+eq(n,1350)+eq(n,1530)+eq(n,1710)+eq(n,1890)+eq(n,2070
[finalize] 7/7 写入交付 …
[finalize] $ git config user.name kimdaedoo-final
[finalize] $ git config user.email kimdaedoo-final@users.noreply.github.com
[finalize] $ git add production/kimdaedoo/delivery/final/
[finalize] $ git commit -q -m kimdaedoo: 180 秒成片交付（报告 + 字幕 + 抽检表）
[finalize] $ git push origin HEAD:arena/b726ea5e-desktop-tutorial
[finalize] DONE final=/home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/final.mp4 dur=180.0s size=126.3MB
```
