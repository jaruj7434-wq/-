# 天皇賞・秋 ナレーション: 前後の無音を切り、文中の0.3秒超の間を0.3秒に詰め、行間をあけてつなぐ (速度変更なし)
import soundfile as sf, numpy as np
SR=48000; W=int(0.01*SR); CAP=0.30
gap={n:0.25 for n in range(1,25)}; gap.update({3:0.5,8:0.5,14:0.5,18:0.5,19:0.45,20:0.35,21:0.45,24:0.8})
def trim(y):
    idx=np.where(np.abs(y)>10**(-45/20))[0]
    return y[max(idx[0]-int(0.03*SR),0):min(idx[-1]+int(0.08*SR),len(y))]
def squeeze(y):
    e=np.array([np.sqrt(np.mean(y[i:i+W]**2)) for i in range(0,len(y)-W+1,W)]); q=e<10**(-40/20)
    keep=np.ones(len(y),bool); i=0
    while i<len(q):
        if q[i]:
            j=i
            while j<len(q) and q[j]: j+=1
            if (j-i)*0.01>CAP:
                c=(i+j)//2; h=int(CAP/0.01/2); keep[(i+0)*W:(c-h)*W]=False; keep[(c+h)*W:j*W]=False
            i=j
        else: i+=1
    return y[keep]
out=[]; t=0; log=[]
for n in range(1,25):
    y,_=sf.read(f'fin/{n:02d}.wav'); y=squeeze(trim(y))
    sf.write(f'fin/{n:02d}_ed.wav',y,SR); log.append(f'{n:02d} start {t:.2f} len {len(y)/SR:.2f}')
    out+=[y,np.zeros(int(gap[n]*SR))]; t+=len(y)/SR+gap[n]
sf.write('narration.wav',np.concatenate(out),SR); open('timing.txt','w').write('\n'.join(log)+'\n'); print('total %.1f'%t)
