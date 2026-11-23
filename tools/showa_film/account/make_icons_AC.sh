mkdir -p /home/user/-/assets/output/showa_pr/account && cd /home/user/- && python3 - <<'EOF'
import sys, math, numpy as np
sys.path.insert(0,'tools/showa_film'); import film
from PIL import Image, ImageDraw, ImageFilter
OUT='assets/output/showa_pr/account'
S=1080
CREAM=(248,238,214); INK=(40,26,20)
def F(n,s): return film.font(n,s)
def center(d,cx,y,t,f,fill,sp=0): film.draw_text_center(d,cx,y,t,f,fill,spacing=sp)
def finish(im,name):
    a=np.asarray(im,np.float32)/255
    rng=np.random.default_rng(3)
    a+= (rng.standard_normal(a.shape[:2])[...,None]*0.035)
    a[1::3]*=0.97
    yy,xx=np.mgrid[0:S,0:S]; r=np.sqrt(((xx-S/2)/(S/2))**2+((yy-S/2)/(S/2))**2)
    a*=np.clip(1-0.28*(r/1.41)**2,0,1)[...,None]
    Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8)).save(f'{OUT}/{name}.png')
def tv(d,cx,cy,w,body,screen):
    h=int(w*0.78)
    d.rounded_rectangle([cx-w/2,cy-h/2,cx+w/2,cy+h/2],radius=60,fill=body,outline=INK,width=10)
    sw,sh=w*0.66,h*0.70
    d.rounded_rectangle([cx-w/2+40,cy-sh/2,cx-w/2+40+sw,cy+sh/2],radius=70,fill=screen,outline=INK,width=8)
    kx=cx+w/2-80
    for k in (-60,40): d.ellipse([kx-34,cy+k-34,kx+34,cy+k+34],fill=CREAM,outline=INK,width=6)
    for k in range(4): d.line([kx-30,cy+110+k*16,kx+30,cy+110+k*16],fill=INK,width=5)
    d.line([cx-60,cy-h/2,cx-170,cy-h/2-170],fill=INK,width=10); d.line([cx+40,cy-h/2,cx+150,cy-h/2-160],fill=INK,width=10)
    d.ellipse([cx-190,cy-h/2-190,cx-150,cy-h/2-150],fill=INK); d.ellipse([cx+130,cy-h/2-180,cx+170,cy-h/2-140],fill=INK)
    d.rectangle([cx-w/2+60,cy+h/2,cx-w/2+90,cy+h/2+70],fill=INK); d.rectangle([cx+w/2-90,cy+h/2,cx+w/2-60,cy+h/2+70],fill=INK)
    return (cx-w/2+40,cy-sh/2,sw,sh)

# A: レトロテレビ + 「まぼろしCM」
im=Image.new('RGB',(S,S),(214,96,48)); d=ImageDraw.Draw(im)
for i in range(0,S,90): d.rectangle([0,i,S,i+45],fill=(222,110,58))
x,y,sw,sh=tv(d,S/2,S/2+50,760,(150,96,60),(236,226,196))
cx=x+sw/2
center(d,cx,y+55,"昭和の",F("tokumin",70),INK,6)
center(d,cx,y+140,"まぼろし",F("tokumin",112),(170,40,30),4)
center(d,cx,y+268,"映像",F("tokumin",88),INK,10)
finish(im,'icon_A_tv_eizo')

# C: 縦書き風の看板ロゴ
im=Image.new('RGB',(S,S),CREAM); d=ImageDraw.Draw(im)
d.rectangle([60,60,S-60,S-60],outline=(160,36,30),width=18); d.rectangle([92,92,S-92,S-92],outline=(160,36,30),width=5)
f=F('tokumin',150)
for i,ch in enumerate("まぼろし"): center(d,S/2+150,150+i*190,ch,f,(160,36,30))
fs=F('tokumin',96)
for i,ch in enumerate("昭和の"): center(d,S/2-140,160+i*130,ch,fs,INK)
d.rounded_rectangle([S/2-260,610,S/2-20,840],radius=20,fill=INK)
center(d,S/2-140,648,"映像",F('tokumin',104),CREAM,4)
finish(im,'icon_C_kanban_eizo')
print('ok')
EOF
