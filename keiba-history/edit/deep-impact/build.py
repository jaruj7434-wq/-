# ディープインパクト編 編集: カットをナレーションの長さに合わせてつなぎ、章・字幕・強調テロップを焼き込む
import subprocess, soundfile as sf, numpy as np, os
SR=48000; FIN=os.path.expanduser('~/deep/el/v4/fin')
order=['01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26','27']
gap={n:0.3 for n in order}; gap.update({'06':0.6,'14':0.6,'22':0.6,'26':0.6,'23':0.4,'24':0.0,'27':1.2})
taniue={'03','21','27'}  # Wan clips: line starts at 0.1s
sub={'01':'オッズ1.1倍。','02':'日本中が、この馬を買った。','03':'ディープインパクト。\\N生涯成績、14戦12勝。','04':'2002年、北海道生まれ。\\N父、サンデーサイレンス。','05':'セリ価格は、7000万円。','06':'名前の意味は、「深い衝撃」。','07':'2004年12月、\\N阪神でデビュー勝ち。','08':'若駒ステークス、\\N弥生賞と連勝。','09':'皐月賞。躓いても勝って、\\N1冠目。','10':'ダービー、5馬身差。2冠目。','11':'神戸新聞杯も勝って、\\Nデビュー6連勝。','12':'菊花賞、単勝1.0倍。3冠目。','13':'デビュー7連勝。\\N無敗の三冠馬。','14':'シンボリルドルフ以来、\\N21年ぶり。','15':'2005年、有馬記念。2着。\\N初めての敗戦。','16':'2006年、\\N阪神大賞典で再スタート。','17':'天皇賞・春、世界レコード。\\NGI4勝目。','18':'宝塚記念、4馬身差。\\NGI5勝目。','19':'そして、フランス凱旋門賞。','20':'3位入線。のちに、失格。','21':'それでも、\\Nディープは終わらなかった。','22':'ジャパンカップ、GI6勝目。','23':'そして……\\N2006年12月24日、中山。\\N……ラストラン。','25':'最後も、圧勝。\\N華麗に、有終の美を飾った。','26':'2019年、17歳で天国へ。','27':'あんたの最強馬は誰だ？\\Nコメントで教えてくれ。'}
big={'01':'1.1倍','03':'14戦12勝','05':'7000万円','06':'DEEP IMPACT\\N＝ 深い衝撃','07':'1戦1勝','08':'3連勝','09':'GI 1勝目','10':'GI 2勝目','11':'6連勝','12':'GI 3勝目','13':'無敗の三冠馬','14':'史上2頭目','15':'連勝ストップ','17':'3分13秒4','18':'GI 5勝目','20':'失格','22':'GI 6勝目','23':'2006年 有馬記念','24':'3馬身差'}
chap=[('04','06','第1章 誕生'),('07','14','第2章 無敗の三冠'),('15','18','第3章 初めての敗北'),('19','22','第4章 凱旋門賞'),('23','26','第5章 ラストラン')]
LASTRUN=float(os.environ.get('LASTRUN','10'))
def ts(t): cs=int(round(t*100)); return '%d:%02d:%02d.%02d'%(cs//360000,cs//6000%60,cs//100%60,cs%100)
os.makedirs('seg',exist_ok=True); start={}; dur={}; t=0; audio=[]
for n in order:
    if n=='24': d=LASTRUN; line=np.zeros(int(d*SR))
    else:
        line,_=sf.read(f'{FIN}/{n}.wav'); d=len(line)/SR+gap[n]
        line=np.concatenate([line,np.zeros(int(gap[n]*SR))])
    start[n]=t; dur[n]=d; t+=d; audio.append(line)
sf.write('narration_full.wav', np.concatenate(audio), SR)
vf='scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=3'
for n in order:
    src = 'vid/24.mp4' if n=='24' and os.path.exists('vid/24.mp4') else f'vid/{n}.mp4'
    if n=='24' and not os.path.exists('vid/24.mp4'):
        cmd=['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c=0x101010:s=1080x1920:r=30:d={dur[n]:.3f}','-vf','format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','20',f'seg/{n}.mp4']
    else:
        ss = '0.1' if n in taniue else '0'
        cmd=['ffmpeg','-v','error','-y','-ss',ss,'-i',src,'-t',f'{dur[n]:.3f}','-an','-vf',vf,'-c:v','libx264','-preset','veryfast','-crf','19',f'seg/{n}.mp4']
    subprocess.run(cmd, check=True)
open('list.txt','w').write(''.join(f"file 'seg/{n}.mp4'\n" for n in order))
H=['[Script Info]','ScriptType: v4.00+','PlayResX: 1080','PlayResY: 1920','WrapStyle: 2','','[V4+ Styles]',
'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
'Style: Sub,Noto Sans JP,66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,2,0,1,5,2,5,60,60,0,1',
'Style: Big,Noto Sans JP,124,&H0000E6FF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,4,0,1,9,3,5,40,40,0,1',
'Style: Chap,Noto Sans JP,52,&H00FFFFFF,&H00FFFFFF,&H00202020,&HB4000000,1,0,0,0,100,100,4,0,3,14,0,8,40,40,110,1',
'Style: Place,Noto Sans JP,58,&H00B0B0B0,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,2,0,1,3,0,5,60,60,0,1',
'','[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text']
E=[]
for a,b,txt in chap: E.append(f'Dialogue: 0,{ts(start[a])},{ts(start[b]+dur[b])},Chap,,0,0,0,,{txt}')
for n in order:
    s,e=start[n],start[n]+dur[n]
    if n in sub: E.append(f'Dialogue: 1,{ts(s)},{ts(e-0.05)},Sub,,0,0,0,,{{\\pos(540,1480)\\fad(80,80)}}{sub[n]}')
    bigy = 330 if n in taniue else 560
    if n in big: E.append(f'Dialogue: 2,{ts(s+0.15)},{ts(e-0.05)},Big,,0,0,0,,{{\\pos(540,{bigy})\\fad(120,80)\\t(0,180,\\fscx112\\fscy112)\\t(180,320,\\fscx100\\fscy100)}}{big[n]}')
s=start['25']; m=s+dur['25']/2; e=s+dur['25']
E.append(f'Dialogue: 2,{ts(s+0.15)},{ts(m)},Big,,0,0,0,,{{\\pos(540,560)\\fad(120,80)}}GI 7勝目')
E.append(f'Dialogue: 2,{ts(m)},{ts(e-0.05)},Big,,0,0,0,,{{\\pos(540,560)\\fad(120,80)}}14戦12勝で引退')
if not os.path.exists('vid/24.mp4'):
    E.append(f'Dialogue: 1,{ts(start["24"])},{ts(start["24"]+dur["24"])},Place,,0,0,0,,{{\\pos(540,1000)}}ここに ラストランの映像（約{LASTRUN:.0f}秒）')
s27=start['27']; l27=len(sf.read(f'{FIN}/27.wav')[0])/SR
E.append(f'Dialogue: 2,{ts(s27+0.15)},{ts(s27+l27)},Big,,0,0,0,,{{\\pos(540,330)\\fad(120,80)}}コメントで教えて')
E.append(f'Dialogue: 2,{ts(s27+l27)},{ts(s27+dur["27"])},Big,,0,0,0,,{{\\pos(540,330)\\fad(120,0)}}フォローで\\N次の名馬へ')
open('captions.ass','w').write('\n'.join(H+E)+'\n')
print('total %.1f'%t)
