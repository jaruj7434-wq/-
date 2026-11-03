# usage: palmtext.py plate.png out.png cx top size nchars [skew]
import sys, numpy as np, cv2
GL={
 'お':[[(14,30),(40,28),(62,26)],
       [(38,8),(39,40),(39,72),(35,86),(24,89),(15,82),(20,70),(38,63),(60,64),(76,72),(75,85),(60,91)],
       [(72,20),(84,32)]],
 'デ':[[(26,16),(46,15),(66,13)],
       [(10,42),(45,41),(82,39)],
       [(48,42),(49,60),(43,76),(32,90)],
       [(76,2),(79,11)],[(96,-2),(99,7)]],
 'ぶ':[[(12,24),(36,22.5),(60,21)]],
 'ブ':[[(12,24),(45,22),(76,20),(76,36),(68,60),(55,78),(40,92)],
       [(84,2),(87,11)],[(104,-2),(107,7)]],
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
            pts=cr([(x+rng.normal(0,0.8),y+rng.normal(0,0.8)) for x,y in st])
            n=len(pts)
            for i,(x,y) in enumerate(pts):
                tt=min(i,n-1-i)/max(1,n*0.12); r=w/2*(0.8+0.2*min(1,tt))
                q=c+ux*(x-50)*size/100+uy*(y-50)*size/100
                cv2.circle(ink,(int(q[0]),int(q[1])),max(1,int(r)),1.0,-1,cv2.LINE_AA)
    ink=cv2.GaussianBlur(ink,(0,0),size/180+0.6)
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY).astype(np.float32)
    hp=g-cv2.GaussianBlur(g,(0,0),size/40)
    ink=np.clip(ink*(0.93+hp/60),0,1)[...,None]  # skin creases show through ink
    col=np.array([30,34,45],np.float32)  # BGR dark brown-black
    out=img.astype(np.float32)*(1-ink)+ (img.astype(np.float32)*col/255*0.6+col*0.4)*ink
    return np.clip(out,0,255).astype(np.uint8)
if __name__=='__main__':
    plate,out,cx,cy,size,ang,n=sys.argv[1:8]
    img=cv2.imread(plate); txt={'2':'おデ','s':'おデぶ','3':'おデブ'}[n]
    cv2.imwrite(out,render(img,txt,float(cx),float(cy),float(size),float(ang)))
