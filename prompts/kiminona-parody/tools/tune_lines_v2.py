# ElevenLabs のセリフを参考の長さと大きさに合わせる(高さは変えない)。聞き取りやすく明るめに
import subprocess, numpy as np, librosa, soundfile as sf, json, sys
DB={'1a':-22,'1b':-21,'1c':-22,'02':-19,'03':-19,'04':-15,'05':-13,'06':-23,'07':-18,'08':-19,'09':-21,'10':-17,'11':-17,
    '12':-18,'13':-18,'14':-14,'15':-14,'16':-17,'17':-17,'18':-21,'20':-19,'19':-21}
EQ='highpass=f=80,equalizer=f=3500:t=q:w=1.2:g=3,highshelf=f=8000:g=2'
res={}
for line in open(sys.argv[1]):
    n,f,a,b=line.split(); a,b=float(a),float(b)
    y,sr=librosa.load(f'L{n}.mp3',sr=48000); y,_=librosa.effects.trim(y,top_db=38)
    cur=len(y)/sr; tempo=float(np.clip(cur/(b-a),0.88,1.3))
    sf.write('tmp.wav',y,sr)
    af=(f'rubberband=tempo={tempo:.3f}:formant=preserved,' if abs(tempo-1)>0.02 else '')+EQ
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i','tmp.wav','-af',af,'T'+n+'.wav'],check=True)
    z,_=librosa.load('T'+n+'.wav',sr=48000)
    g=10**((DB[n]-20*np.log10(np.percentile(librosa.feature.rms(y=z)[0],90)+1e-9))/20)
    sf.write('T'+n+'.wav',np.clip(z*g,-0.99,0.99),48000)
    res[n]=dict(start=a,ref_len=round(b-a,2),gen_len=round(cur,2),out_len=round(len(z)/48000,2),tempo=round(tempo,2))
    print(n,res[n],flush=True)
json.dump(res,open('tuned.json','w'),indent=1)
L=92.2; tr=np.zeros(int(L*48000),np.float32)
for n,r in res.items():
    z,_=sf.read('T'+n+'.wav'); i=int(r['start']*48000); tr[i:i+len(z)]+=z[:len(tr)-i]
sf.write('dialogue_ref_timing.wav',np.clip(tr,-0.99,0.99),48000)
