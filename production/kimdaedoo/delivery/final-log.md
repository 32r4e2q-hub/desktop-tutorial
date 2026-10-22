# 出片日志（failure，2026-10-22T08:03:45Z）

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
[finalize]   S01 +0% 仍 8.59s，再提速
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.wav
[finalize]   S01 +5% 仍 8.19s，再提速
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.wav
[finalize]   S01 +10% 仍 7.82s，再提速
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.wav
[finalize]   S01 +15% 仍 7.49s，再提速
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.wav
[finalize]   S01 +20% 仍 7.17s，再提速
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.raw.mp3 -af silenceremove=start_periods=1:start_silence=0.02:start_threshold=-38dB,areverse,silenceremove=start_periods=1:start_silence=0
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.wav
[finalize]   S01 +25% 仍 6.89s，再提速
[finalize] $ ffmpeg -y -v error -i /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.wav -filter:a atempo=1.1800 -ar 48000 -ac 2 /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.fit.wav
[finalize] $ ffprobe -v error -show_entries format=duration -of json /home/runner/work/desktop-tutorial/desktop-tutorial/work/kimdaedoo-final/tts/S01.fit.wav
[finalize] FATAL: S01 配音仍超出镜头窗：5.84s
```
