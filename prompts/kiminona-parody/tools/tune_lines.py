# 各セリフを参考の長さ・高さ・大きさに合わせる(ffmpeg rubberband、フォルマント保持)
import subprocess, numpy as np, librosa, json, sys
# n: (参考の高さHz or None, 目標の大きさdBFS)
T={'01':(250,-24),'02':(None,-20),'03':(None,-19),'04':(365,-15),'05':(474,-12),'06':(None,-23),'07':(297,-19),
   '08':(293,-19),'09':(None,-21),'10':(None,-17),'11':(361,-17),'12':(None,-18),'13':(257,-18),'14':(None,-13),
   '15':(None,-13),'16':(330,-18),'17':(None,-18),'18':(335,-22),'20':(None,-20),'19':(None,-21)}
res={}
for line in open(sys.argv[1]):
    n,f,a,b=line.split(); a,b=float(a),float(b)
    y,sr=librosa.load(f'L{n}.mp3',sr=48000); y,_=librosa.effects.trim(y,top_db=35)
    cur=len(y)/sr; tgt=b-a
    tempo=float(np.clip(cur/tgt,0.82,1.35))
    f0,v,_=librosa.pyin(librosa.resample(y,orig_sr=sr,target_sr=16000),fmin=70,fmax=600,sr=16000,frame_length=1024)
    cf=np.nanmedian(f0[v]) if v.any() else None
    ref_f,db=T[n]; pitch=1.0
    if ref_f and cf: pitch=float(np.clip(ref_f/cf,1.0,2**(6/12)))   # 最大+6半音
    import soundfile as sf; sf.write('tmp.wav',y,sr)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i','tmp.wav','-af',
        f'rubberband=tempo={tempo:.3f}:pitch={pitch:.3f}:formant=preserved','T'+n+'.wav'],check=True)
    z,_=librosa.load('T'+n+'.wav',sr=48000)
    rms=np.percentile(librosa.feature.rms(y=z)[0],90); g=10**((db-20*np.log10(rms+1e-9))/20)
    sf.write('T'+n+'.wav',np.clip(z*g,-0.99,0.99),48000)
    res[n]=dict(start=a,ref_len=round(tgt,2),gen_len=round(cur,2),out_len=round(len(z)/48000,2),tempo=round(tempo,2),pitch_st=round(12*np.log2(pitch),1),f0=round(float(cf),0) if cf else None)
    print(n,res[n],flush=True)
json.dump(res,open('tuned.json','w'))
