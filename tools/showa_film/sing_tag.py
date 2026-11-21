import numpy as np,subprocess,pyworld as pw,wave
fs=24000
x=np.frombuffer(subprocess.run(['ffmpeg','-v','error','-i','voice.wav','-f','s16le','-'],capture_output=True).stdout,np.int16)/32768.
x=x.astype(np.float64); fp=5.0
f0,t=pw.harvest(x,fs,frame_period=fp); sp=pw.cheaptrick(x,f0,t,fs); ap=pw.d4c(x,f0,t,fs)
N=lambda n:440*2**((n-69)/12)
G4,A4,B4,C5,D5=67,69,71,72,74
beat=0.27
# (src_start,src_end, [(dur_beats,note)...]) ; note None = rest
morae=[(0.05,0.47,[(1,G4)]),(0.47,0.66,[(1,G4)]),(0.66,0.90,[(1,A4)]),(0.90,1.16,[(1,B4)]),(1.16,1.66,[(2,B4)]),
       (None,None,[(1,None)]),
       (2.05,2.42,[(1,D5)]),(2.42,2.50,[(1,D5)]),(2.50,2.80,[(2,C5)]),(2.80,3.10,[(1.5,B4),(4.5,G4)])]
F0=[];SP=[];AP=[]
for s,e,notes in morae:
    tot=sum(d for d,_ in notes)*beat; n=int(tot*1000/fp)
    if s is None:
        F0+= [0]*n; SP+=[sp[0]*1e-6]*n; AP+=[ap[0]]*n; continue
    si,ei=int(s*1000/fp),int(e*1000/fp)
    # consonant keep natural speed for first 30%, then stretch vowel
    src=np.concatenate([np.linspace(si,si+(ei-si)*0.3,max(1,min(n//3,int((ei-si)*0.3)))),np.linspace(si+(ei-si)*0.3,ei-1,n)])[:n]
    if len(src)<n: src=np.pad(src,(0,n-len(src)),mode='edge')
    k=0
    for d,note in notes:
        m=int(d*beat*1000/fp)
        for j in range(m):
            idx=int(src[min(k,n-1)]); voiced=f0[idx]>0
            tt=j*fp/1000
            vib=1+0.012*np.sin(2*np.pi*5.5*tt)*min(1,tt/0.3)
            # glide into note
            F0.append(N(note)*vib if voiced else 0); SP.append(sp[idx]); AP.append(ap[idx]); k+=1
F0=np.array(F0,dtype=np.float64);SP=np.array(SP);AP=np.array(AP)
# smooth f0 transitions (portamento) on voiced frames
sm=F0.copy()
for i in range(1,len(sm)):
    if sm[i]>0 and sm[i-1]>0: sm[i]=sm[i-1]+(F0[i]-sm[i-1])*0.35
np.save("sm.npy",sm)
y=pw.synthesize(sm,np.ascontiguousarray(SP),np.ascontiguousarray(AP),fs,fp)
# chorus: 3 voices slightly detuned/delayed
def shift(f,c): return pw.synthesize(sm*2**(c/1200),np.ascontiguousarray(SP),np.ascontiguousarray(AP),fs,fp)
v=y+0.6*np.roll(shift(sm,9),int(0.012*fs))+0.6*np.roll(shift(sm,-8),int(0.02*fs))
v/=np.abs(v).max()
L=len(v)+int(1.4*fs); out=np.zeros(L); out[:len(v)]+=v*0.8
T=np.arange(L)/fs
def tone(f,st,dur,kind,amp):
    i0=int(st*fs);n=int(dur*fs);tt=np.arange(n)/fs
    if kind=='glock': w=(np.sin(2*np.pi*f*tt)+0.3*np.sin(2*np.pi*f*2.76*tt))*np.exp(-tt*4)
    elif kind=='bass': w=np.sin(2*np.pi*f*tt)*np.exp(-tt*3)
    elif kind=='brass':
        w=sum(np.sin(2*np.pi*f*h*tt)/h for h in range(1,8))*np.minimum(1,tt/0.04)*np.exp(-tt*1.2)
    elif kind=='chord': w=sum(np.sin(2*np.pi*f*h*tt)/(h*h) for h in range(1,4))*np.minimum(1,tt/0.02)*np.exp(-tt*2.5)
    e=min(L,i0+n); out[i0:e]+=amp*w[:e-i0]
# melody doubled on glock
pos=0
for s,e,notes in morae:
    for d,note in notes:
        if note: tone(N(note+12),pos,1.2,'glock',0.12)
        pos+=d*beat
# bass + chords on each beat: G (beats0-6), D7 (6-10), G (10-)
total_beats=int(pos/beat)+4
for b in range(total_beats):
    st=b*beat
    root= 43 if b<6 else (38 if b<10 else 43)
    if b%2==0 and b<14: tone(N(root),st,0.5,'bass',0.35)
    ch=[67,71,74] if (b<6 or b>=10) else [66,69,72]
    if b%2==1 and b<14:
        for c in ch: tone(N(c-12),st,0.3,'chord',0.06)
# brass stab at end and bell
endt=pos-4.5*beat
for c in [55,59,62,67]: tone(N(c),endt,2.0,'brass',0.05)
tone(N(91),pos-0.2,1.5,'glock',0.3); tone(N(86),pos-0.2,1.5,'glock',0.2)
out=np.tanh(out*1.2); out/=np.abs(out).max(); out*=0.9
fade=int(0.4*fs); out[-fade:]*=np.linspace(1,0,fade)
w=wave.open('jingle3_asanebou.wav','wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(fs)
w.writeframes((out*32767).astype(np.int16).tobytes()); w.close()
print('dur',L/fs,'sung',pos)
