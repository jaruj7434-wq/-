python3 - <<'EOF'
import sys, numpy as np
sys.path.insert(0,'tools/showa_film'); import film
from PIL import Image, ImageDraw
CREAM=(248,238,214); INK=(40,26,20)
COLS=[(200,200,200),(200,200,40),(40,200,200),(40,200,40),(200,40,200),(200,40,40),(40,40,200)]
def bars(w=400,h=300):
    im=Image.new('RGB',(w,h),(20,20,20)); d=ImageDraw.Draw(im); bw=w/7
    for i,c in enumerate(COLS): d.rectangle([i*bw,0,(i+1)*bw,h*0.68],fill=c)
    for i,c in enumerate([(40,40,200),(20,20,20),(200,40,200),(20,20,20),(40,200,200),(20,20,20),(200,200,200)]): d.rectangle([i*bw,h*0.68,(i+1)*bw,h*0.77],fill=c)
    return im
def glow(w=400,h=300):
    a=np.full((h,w,3),[226,214,186],np.float32)/255
    yy,xx=np.mgrid[0:h,0:w]; r=np.sqrt(((xx-w/2)/(w/2))**2+((yy-h/2)/(h/2))**2)
    a*=np.clip(1-0.35*r**2,0,1)[...,None]; return Image.fromarray((a*255).astype(np.uint8))
def tvset(screen, w, body=(150,96,60)):
    h=int(w*0.80); im=Image.new('RGBA',(w,h+int(w*0.12)),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.rounded_rectangle([0,0,w-1,h-1],radius=int(w*0.08),fill=body+(255,),outline=INK+(255,),width=max(4,w//60))
    sw,sh=int(w*0.70),int(h*0.74); sx,sy=int(w*0.06),int((h-sh)/2)
    a=np.asarray(screen.resize((sw,sh)),np.float32)/255; a[1::3]*=0.86
    scr=Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8))
    m=Image.new('L',(sw,sh),0); ImageDraw.Draw(m).rounded_rectangle([0,0,sw-1,sh-1],radius=int(sw*0.12),fill=255)
    im.paste(scr,(sx,sy),m); d.rounded_rectangle([sx,sy,sx+sw,sy+sh],radius=int(sw*0.12),outline=INK+(255,),width=max(3,w//80))
    kx=int(w*0.88)
    for k in (0.32,0.52): d.ellipse([kx-w*0.045,h*k-w*0.045,kx+w*0.045,h*k+w*0.045],fill=CREAM+(255,),outline=INK+(255,),width=3)
    for k in range(3): d.line([kx-w*0.04,h*0.72+k*w*0.025,kx+w*0.04,h*0.72+k*w*0.025],fill=INK+(255,),width=3)
    lg=int(w*0.04); d.rectangle([w*0.1,h,w*0.1+lg,h+w*0.12],fill=INK+(255,)); d.rectangle([w*0.9-lg,h,w*0.9,h+w*0.12],fill=INK+(255,))
    return im
def bg(W,H):
    im=Image.new('RGB',(W,H),(214,96,48)); d=ImageDraw.Draw(im); st=max(40,H//16)
    for y in range(0,H,st*2): d.rectangle([0,y,W,y+st],fill=(222,110,58))
    bh=int(H*0.05); bw=W/7
    for i,c in enumerate(COLS): d.rectangle([i*bw,H-bh,(i+1)*bw,H],fill=c)
    return im
def finish(im):
    a=np.asarray(im.convert('RGB'),np.float32)/255; rng=np.random.default_rng(9)
    a+=rng.standard_normal(a.shape[:2])[...,None]*0.03; a[1::3]*=0.975
    return Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8))
def title(d,cx,y,size):
    f=film.font('tokumin',size); ft=film.font('antique',int(size*0.30))
    for dx,dy in ((5,6),(3,4)): film.draw_text_center(d,cx+dx,y+dy,'昭和のまぼろし映像',f,INK,spacing=int(size*0.05))
    film.draw_text_center(d,cx,y,'昭和のまぼろし映像',f,CREAM,spacing=int(size*0.05))
    film.draw_text_center(d,cx,y+size*1.42,'ありそうでなかった、昭和のテレビをお届けします',ft,CREAM,spacing=4)
    return d.textlength('昭和のまぼろし映像',font=f)+size*0.05*8
scr=[bars(),glow(),glow(),bars()]
OUT='assets/output/showa_pr/account/'
W,H=2560,1440; im=bg(W,H); d=ImageDraw.Draw(im)
tw_=title(d,W/2,H/2-95,118); tw=260; half=tw_/2+30; top=int(H/2-130)
for x,s in [(W/2-half-tw,scr[1]),(W/2-half-2*tw-30,scr[0]),(W/2+half,scr[2]),(W/2+half+tw+30,scr[3])]:
    t=tvset(s,tw); im.paste(t,(int(x),top),t)
finish(im).save(OUT+'header_youtube_2560x1440_eizo.png')
W,H=1500,500; im=bg(W,H); d=ImageDraw.Draw(im); title(d,W/2,150,92)
for x,s in [(30,scr[0]),(1500-30-220,scr[3])]:
    t=tvset(s,220); im.paste(t,(int(x),140),t)
finish(im).save(OUT+'header_x_1500x500_eizo.png')
EOF
python3 -c "
from PIL import Image
a=Image.open('/home/user/-/assets/output/showa_pr/account/header_youtube_2560x1440_eizo.png').resize((960,540))
b=Image.open('/home/user/-/assets/output/showa_pr/account/header_x_1500x500_eizo.png').resize((960,320))
c=Image.new('RGB',(960,870),'white');c.paste(a,(0,0));c.paste(b,(0,550));c.save('/tmp/claude-0/-home-user--/81012a35-c59b-5353-a957-ebe6f442d7a8/scratchpad/headers.png')"