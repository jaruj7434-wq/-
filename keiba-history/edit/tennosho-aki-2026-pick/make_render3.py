# render2.py (天皇賞・秋 データ検証 v3 の編集) の部品を流用して、本命予想編の render3.py を組み立てる
# 使い方: python3 make_render3.py <render2.py> <scenes3.py> <出力 render3.py>
import sys
r2, sc, out = sys.argv[1:4]
s = open(r2).read()
head = s[:s.index('# ---------- HUD')]
tail = s[s.index('# ---------- render ----------'):]
head = head.replace("open(f'{A}/vo2/timingB.txt')", "open(os.path.expanduser('~/aki/pick/vo/timingB.txt'))")
# 谷上の動画は先頭 0.1 秒 (Wan の無音) を飛ばして再生できるようにする
head = head.replace("    def __init__(self, path, dur, mode):", "    def __init__(self, path, dur, mode, ss=0.0):")
head = head.replace("['ffmpeg', '-v', 'quiet', '-i', path,", "['ffmpeg', '-v', 'quiet', '-ss', f'{ss:.2f}', '-i', path,")
# 谷上の動画 (ss>0) は口の動きが音声とずれないよう引き延ばさず等速で再生し、足りない分は最後のコマで止める
head = head.replace("        slow = max(1.0, (dur + 0.3) / (src - 0.1))", "        slow = 1.0 if ss > 0 else max(1.0, (dur + 0.3) / (src - 0.1))")
tail = tail.replace("Vid(f\"{A}/vids/{e['src']}.mp4\", e['t1'] - e['t0'], 'cover' if e['kind'] == 'cover' else 'blur')",
                    "Vid(f\"{P}/vids/{e['src']}.mp4\", e['t1'] - e['t0'], 'cover' if e['kind'] == 'cover' else 'blur', e.get('ss', 0.0))")
tail = tail.replace("'~/aki/ed/video_noaudio.mp4'", "'~/aki/pick/video_noaudio.mp4'").replace("f'~/aki/ed/st_{t:06.2f}.jpg'", "f'~/aki/pick/st_{t:06.2f}.jpg'")
assert "P}/vids" in tail and "pick/video_noaudio" in tail and "ss=0.0" in head and "1.0 if ss > 0" in head
open(out, 'w').write(head + open(sc).read() + '\n' + tail)
print('ok')
