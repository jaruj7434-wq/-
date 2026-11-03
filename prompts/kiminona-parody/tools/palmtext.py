# usage: palmtext.py plate.png out.png cx top size nchars [skew]
import sys, numpy as np, cv2
GL={
 'お':[[(14,30),(40,28),(62,26)],
       [(38,8),(39,40),(39,72),(35,86),(24,89),(15,82),(20,70),(38,63),(60,64),(76,72),(75,85),(60,91)],
       [(72,20),(84,32)]],
 'デ':[[(26,16),(46,15),(66,13)],
       [(10,42),(45,41),(82,39)],
       [(48,42),(49,60),(43,76),(32,90)],
       [(82,-7),(86,6)],[(101,-11),(105,2)]],
 'ぶ':[[(12,24),(36,22.5),(60,21)]],
 'ブ':[[(12,24),(45,22),(76,20),(76,36),(68,60),(55,78),(40,92)],
       [(88,-6),(92,7)],[(107,-10),(111,3)]],
}
def cr(pts,n=24):
    p=[pts[0]]+pts+[pts[-1]];out=[]
    for i in range(1,len(p)-2):
        p0,p1,p2,p3=map(np.array,(p[i-1],p[i],p[i+1],p[i+2]))
        for t in np.linspace(0,1,n,endpoint=False):
            out.append(0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t**3))
    out.append(np.array(pts[-1]));return np.array(out,float)
def render(img,text,cx,cy,size,ang=0,gap=0.25,seed=3,tex=None):
    rng=np.random.default_rng(seed)
    H,W=img.shape[:2]; ink=np.zeros((H,W),np.float32)
    w=size/6.5
    a=np.radians(ang); ux=np.array([np.cos(a),-np.sin(a)]); uy=np.array([np.sin(a),np.cos(a)])
    for k,ch in enumerate(text):
        c=np.array([cx,cy])+uy*(k-1)*size*(1+gap)
        for st in GL[ch]:
            wf=0.72 if len(st)==2 and abs(st[1][1]-st[0][1])>abs(st[1][0]-st[0][0]) else 1.0
            pts=cr([(x+rng.normal(0,1.1),y+rng.normal(0,1.1)) for x,y in st])
            n=len(pts)
            for i,(x,y) in enumerate(pts):
                tt=min(i,n-1-i)/max(1,n*0.12); r=wf*w/2*(0.8+0.2*min(1,tt))*(1+0.05*np.sin(i*0.21+k*1.7+len(st)))
                q=c+ux*(x-50)*size/100+uy*(y-50)*size/100
                cv2.circle(ink,(int(q[0]),int(q[1])),max(1,int(r)),1.0,-1,cv2.LINE_AA)
    rng2=np.random.default_rng(7)
    # foreshortening of the palm surface (seen at an angle)
    M=cv2.getAffineTransform(np.float32([[cx,cy],[cx+100,cy],[cx,cy+100]]),np.float32([[cx,cy],[cx+100,cy-4],[cx+2,cy+94]]))
    ink=cv2.warpAffine(ink,M,(W,H))
    f=img.astype(np.float32)/255
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY).astype(np.float32)/255
    # rough, slightly bled edges
    n_hi=cv2.GaussianBlur(rng2.normal(0,1,ink.shape).astype(np.float32),(0,0),1.2)
    edge=cv2.GaussianBlur(ink,(0,0),2.0)
    ink=np.clip(edge+0.08*n_hi*(edge*(1-edge))*4,0,1)
    ink=np.clip((ink-0.35)/0.3,0,1)
    ink=cv2.GaussianBlur(ink,(0,0),0.9)
    # ink skips over fine creases, pools on ridges; uneven coverage
    hp=g-cv2.GaussianBlur(g,(0,0),3)
    lo=cv2.GaussianBlur(rng2.normal(0,1,ink.shape).astype(np.float32),(0,0),size/12)
    lo=lo/ (np.abs(lo).max()+1e-6)
    a=ink*np.clip(0.84+0.12*lo+9.0*np.minimum(hp,0)+2.0*np.maximum(hp,0),0.35,0.97)
    # multiply blend: ink inherits palm shading
    tint=np.array([0.20,0.19,0.22],np.float32)  # BGR transmittance (dark brown-black)
    out=f*(1-a[...,None]*(1-tint))
    # keep a little of the skin's specular sheen on top of the ink
    spec=np.maximum(g-cv2.GaussianBlur(g,(0,0),8),0)
    out+=(spec*0.6*a)[...,None]
    out+=(rng2.normal(0,0.008,out.shape).astype(np.float32))*a[...,None]
    return np.clip(out*255,0,255).astype(np.uint8)
if __name__=='__main__':
    plate,out,cx,cy,size,ang,n=sys.argv[1:8]
    img=cv2.imread(plate); txt={'2':'おデ','s':'おデぶ','3':'おデブ'}[n]
    cv2.imwrite(out,render(img,txt,float(cx),float(cy),float(size),float(ang)))
