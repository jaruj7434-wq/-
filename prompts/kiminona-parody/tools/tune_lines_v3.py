# v3:長さ合わせ+声ごとの明瞭化 EQ+ステレオで2人の叫びを左右に分ける
import subprocess, numpy as np, librosa, soundfile as sf, json, sys
KEITA={'1a','1c','03','06','09','10','12','14','17','20','19'}
FRIEND={'02'}
DB={'1a':-21,'1b':-20,'1c':-21,'02':-19,'03':-19,'04':-15,'05':-13,'06':-22,'07':-18,'08':-19,'09':-20,'10':-17,'11':-17,
    '12':-19,'13':-18,'14':-15,'15':-15,'16':-17,'17':-17,'18':-21,'20':-19,'19':-21}
# 男声:こもり(250-400Hz)を削り、輪郭(2.5-4kHz)と空気感を足す / 女声:軽く明るく
EQ_M='highpass=f=90,equalizer=f=320:t=q:w=1.0:g=-4,equalizer=f=2800:t=q:w=1.2:g=6,equalizer=f=5500:t=q:w=1.5:g=4,highshelf=f=9000:g=3,acompressor=threshold=-24dB:ratio=2.5:attack=8:release=120'
EQ_F='highpass=f=120,equalizer=f=280:t=q:w=1.0:g=-2,equalizer=f=3500:t=q:w=1.2:g=3,highshelf=f=8000:g=2,acompressor=threshold=-24dB:ratio=2:attack=8:release=120'
EXTRA={'02','03','06','19'}
PAN={'14':-0.35,'15':0.35}           # 2人同時の叫び:慶太を左、ヒロインを右
OFFSET={'03':0.42,'07':0.40,'10':0.28,'20':0.33}
res={}
for line in open(sys.argv[1]):
    n,f,a,b=line.split(); a,b=float(a),float(b)
    y,sr=librosa.load(f'L{n}.mp3',sr=48000); y,_=librosa.effects.trim(y,top_db=38)
    cur=len(y)/sr; tempo=float(np.clip(cur/(b-a),0.88,1.3)); sf.write('tmp.wav',y,sr)
    eq=EQ_M if (n in KEITA or n in FRIEND) else EQ_F
    if n in EXTRA: eq+=',equalizer=f=450:t=q:w=1.0:g=-4,equalizer=f=3200:t=q:w=1.0:g=5,equalizer=f=6500:t=q:w=1.2:g=4'
    af=(f'rubberband=tempo={tempo:.3f}:formant=preserved,' if abs(tempo-1)>0.02 else '')+eq
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i','tmp.wav','-af',af,'T'+n+'.wav'],check=True)
    z,_=librosa.load('T'+n+'.wav',sr=48000)
    g=10**((DB[n]-20*np.log10(np.percentile(librosa.feature.rms(y=z)[0],90)+1e-9))/20); z=np.clip(z*g,-0.99,0.99)
    sf.write('T'+n+'.wav',z,48000)
    S=np.abs(librosa.stft(z))**2; fr=librosa.fft_frequencies(sr=48000)
    res[n]=dict(start=round(a+OFFSET.get(n,0),2),ref_len=round(b-a,2),out_len=round(len(z)/48000,2),tempo=round(tempo,2),
                clarity=round(float(S[fr>3000].sum()/S[(fr>200)&(fr<3000)].sum()),3))
    print(n,res[n],flush=True)
json.dump(res,open('tuned_v3.json','w'),indent=1)
tr=np.zeros((int(92.2*48000),2),np.float32)
for n,r in res.items():
    z,_=sf.read('T'+n+'.wav'); p=PAN.get(n,0.0); i=int(r['start']*48000); k=min(len(z),len(tr)-i)
    tr[i:i+k,0]+=z[:k]*np.cos((p+1)*np.pi/4)*1.414; tr[i:i+k,1]+=z[:k]*np.sin((p+1)*np.pi/4)*1.414
sf.write('dialogue_v3.wav',np.clip(tr,-0.99,0.99),48000)
