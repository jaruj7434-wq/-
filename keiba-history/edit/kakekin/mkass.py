# captions.ass を生成する。d は各セグメント音声の長さ(秒)
d=[3.532042,4.158042,4.135167,2.621979,2.385958,2.591604,2.527771,5.838667]
# (amount, switch_offset or None, amount2, line)
segs=[("100円",1.84,"500円","まあ、しゃあない"),
("1,000円",2.15,"3,000円","騎手が悪い"),
("5,000円",2.14,"1万円","八百長だろ"),
("3万円",None,None,"騎手のインスタどれ？"),
("5万円",None,None,"馬刺し予約しといて"),
("10万円",None,None,"農林水産大臣、出して"),
("50万円",None,None,"家賃って\\N何ヶ月待てる？"),
("100万円",None,None,"嫁にはマグロ漁船\\N乗ったって言っといて")]
def ts(t):
    cs=int(round(t*100)); return f"{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}"
total=sum(d)
out=["[Script Info]","ScriptType: v4.00+","PlayResX: 1080","PlayResY: 1920","WrapStyle: 2","",
"[V4+ Styles]","Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
"Style: H1,Noto Sans JP,130,&H0000E6FF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,4,0,1,9,0,8,40,40,110,1",
"Style: H2,Noto Sans JP,78,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,2,0,1,7,0,8,40,40,270,1",
"Style: Amt,Noto Sans JP,86,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,2,0,1,0,0,5,40,40,0,1",
"Style: Line,Noto Sans JP,92,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,2,0,1,8,0,8,40,40,0,1",
"","[Events]","Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
f"Dialogue: 0,{ts(0)},{ts(total)},H1,,0,0,0,,賭け金別",
f"Dialogue: 0,{ts(0)},{ts(total)},H2,,0,0,0,,馬券が外れた時の反応"]
# rounded black pill drawn behind amount
def pill(w,h,r=40):
    return (f"m {r} 0 l {w-r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h-r} b {w} {h} {w} {h} {w-r} {h} "
            f"l {r} {h} b 0 {h} 0 {h} 0 {h-r} l 0 {r} b 0 0 0 0 {r} 0")
AY=1260
def amt(s,e,txt):
    w=max(300,len(txt)*86+90); h=130
    out.append(f"Dialogue: 0,{ts(s)},{ts(e)},Amt,,0,0,0,,{{\\an7\\pos({540-w//2},{AY-h//2})\\1c&H000000&\\1a&H10&\\p1}}{pill(w,h)}")
    out.append(f"Dialogue: 1,{ts(s)},{ts(e)},Amt,,0,0,0,,{{\\pos(540,{AY})}}{txt}")
t=0
for di,(a1,sw,a2,ln) in zip(d,segs):
    if sw: amt(t,t+sw,a1); amt(t+sw,t+di,a2)
    else: amt(t,t+di,a1)
    out.append(f"Dialogue: 1,{ts(t)},{ts(t+di)},Line,,0,0,0,,{{\\pos(540,1360)\\an8}}{ln}")
    t+=di
open("captions.ass","w").write("\n".join(out)+"\n")
print(total)
