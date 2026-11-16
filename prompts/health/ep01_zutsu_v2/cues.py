import pyopenjtalk,re,subprocess,json
def mora(s): return len(re.sub(r'[ャュョァィゥェォ、。?’]','',pyopenjtalk.g2p(s,kana=True)))
def speech_spans(f):
    o=subprocess.run(['ffmpeg','-hide_banner','-i',f,'-af','silencedetect=noise=-40dB:d=0.12','-f','null','-'],capture_output=True,text=True).stderr
    st=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',o)];en=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',o)]
    d=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f],capture_output=True,text=True).stdout)
    # build voiced spans
    ev=sorted([(s,'s') for s in st]+[(e,'e') for e in en]);spans=[];cur=0.0;on=True
    for t,k in ev:
        if k=='s' and on: spans.append((cur,t));on=False
        if k=='e': cur=t;on=True
    if on: spans.append((cur,d))
    return [(a,b) for a,b in spans if b-a>0.05],d
def at(f,text,key):
    i=text.index(key); frac=mora(text[:i])/mora(text)
    spans,d=speech_spans(f); tot=sum(b-a for a,b in spans); tgt=frac*tot
    for a,b in spans:
        if tgt<=b-a: return a+tgt
        tgt-=(b-a)
    return d
S2="頭全体が、ぎゅーっと締めつけられる痛みは、緊張型頭痛。首や肩の筋肉がこわばって、血の巡りが悪くなることが関係しています。このタイプは、温めて、軽くストレッチ。同じ姿勢を続けないのがポイントです。"
S3="ズキンズキンと脈打つように痛み、動くと悪化する。光や音がつらい。それは、片頭痛かもしれません。脳の血管が広がり、まわりの神経が刺激されると考えられています。このタイプは、冷やして、暗く静かな場所で休みましょう。"
S4="そして、意外な落とし穴。頭痛薬を、月に十日以上飲んでいると、かえって頭痛が増えることがあります。思い当たる人は、医師や薬剤師に相談を。"
S5="ただし、突然の激しい頭痛。手足のしびれや、ろれつが回らない。熱と、首のこわばりがある。こんなときは、すぐに救急へ。"
dur={i:float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f'v2/t{i}.wav'],capture_output=True,text=True).stdout) for i in range(1,7)}
start={};t=1.2
for i in range(1,7): start[i]=round(t,2); t+=dur[i]+0.35
c={'s1':start[1],'s2':start[2],'s3':start[3],'s4':start[4],'s5':start[5],'s6':start[6],'fin':round(start[6]+dur[6]+1.6,2)}
c['ten']=round(start[2]+at('v2/t2.wav',S2,'緊張型'),2);c['warm']=round(start[2]+at('v2/t2.wav',S2,'温めて'),2);c['str']=round(start[2]+at('v2/t2.wav',S2,'軽く'),2);c['pos']=round(start[2]+at('v2/t2.wav',S2,'同じ'),2)
c['migName']=round(start[3]+at('v2/t3.wav',S3,'片頭痛'),2);c['cool']=round(start[3]+at('v2/t3.wav',S3,'冷やして'),2);c['rest']=round(start[3]+at('v2/t3.wav',S3,'暗く'),2)
c['pill']=round(start[4]+at('v2/t4.wav',S4,'頭痛薬'),2);c['ask']=round(start[4]+at('v2/t4.wav',S4,'思い'),2)
c['d1']=round(start[5]+at('v2/t5.wav',S5,'突然'),2);c['d2']=round(start[5]+at('v2/t5.wav',S5,'手足'),2);c['d3']=round(start[5]+at('v2/t5.wav',S5,'熱と'),2);c['d4']=round(start[5]+at('v2/t5.wav',S5,'こんな'),2)
print(json.dumps(c))
