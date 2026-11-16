import re,subprocess,pyopenjtalk,json,sys
sys.path.insert(0,'.')
exec(open('mora.py').read().split('import re')[0])  # segs
out=subprocess.run(['ffmpeg','-hide_banner','-i','zutsu/narr.mp3','-af','silencedetect=noise=-35dB:d=0.15','-f','null','-'],capture_output=True,text=True).stderr
st=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',out)]; en=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',out)]
END=41.56
chunks=[]; prev=en[0]
for s,e in zip(st[1:],en[1:]): chunks.append((prev,s)); prev=e
if prev<END-0.1: chunks.append((prev,END))
phr=[]  # (seg index, text, mora)
for i,s in enumerate(segs):
    for p in re.findall(r'[^、。?]+[、。?]?',s):
        k=re.sub(r'[ャュョァィゥェォ、。?’]','',pyopenjtalk.g2p(p,kana=True)); phr.append((i,p,len(k)))
N,M=len(chunks),len(phr)
rate=sum(m for *_,m in phr)/sum(b-a for a,b in chunks)
import functools
INF=1e18
dp=[[INF]*(M+1) for _ in range(N+1)]; bk=[[0]*(M+1) for _ in range(N+1)]; dp[0][0]=0
for c in range(1,N+1):
    d=chunks[c-1][1]-chunks[c-1][0]
    for j in range(1,M+1):
        for k in range(max(0,j-8),j):
            if dp[c-1][k]==INF: continue
            m=sum(x[2] for x in phr[k:j]); cost=dp[c-1][k]+(d-m/rate)**2
            if cost<dp[c][j]: dp[c][j]=cost; bk[c][j]=k
j=M; assign=[]
for c in range(N,0,-1):
    k=bk[c][j]; assign.append((c-1,k,j)); j=k
assign.reverse()
print('rate',round(rate,2))
segstart={}
for c,k,j in assign:
    a,b=chunks[c]; print(f'{a:6.2f}-{b:6.2f}', ''.join(p for _,p,_ in phr[k:j]))
    for x in phr[k:j]: segstart.setdefault(x[0],a)
print(json.dumps(segstart))
