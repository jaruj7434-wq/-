python3 - <<'EOF'
import sys, numpy as np
sys.path.insert(0,'tools/showa_film'); import film
from PIL import Image, ImageDraw
S=1080; CREAM=(248,238,214); INK=(40,26,20)
im=Image.new('RGB',(S,S),(20,20,20)); d=ImageDraw.Draw(im)
cols=[(200,200,200),(200,200,40),(40,200,200),(40,200,40),(200,40,200),(200,40,40),(40,40,200)]
w=S/len(cols)
for i,c in enumerate(cols): d.rectangle([i*w,0,(i+1)*w,S*0.62],fill=c)
for i,c in enumerate([(40,40,200),(20,20,20),(200,40,200),(20,20,20),(40,200,200),(20,20,20),(200,200,200)]): d.rectangle([i*w,S*0.62,(i+1)*w,S*0.70],fill=c)
d.rectangle([0,S*0.70,S,S],fill=(28,26,30))
R=330; cx,cy=S/2,S*0.40
d.ellipse([cx-R,cy-R,cx+R,cy+R],fill=CREAM,outline=INK,width=12)
film.draw_text_center(d,cx,cy-190,"昭和の",film.font('tokumin',90),INK,spacing=8)
film.draw_text_center(d,cx,cy-75,"まぼろし",film.font('tokumin',138),(170,40,30),spacing=2)
film.draw_text_center(d,cx,cy+95,"映像",film.font('tokumin',120),INK,spacing=12)
film.draw_text_center(d,cx,S*0.79,"しばらくお待ちください",film.font('antique',60),CREAM,spacing=6)
a=np.asarray(im,np.float32)/255; rng=np.random.default_rng(5)
a+=rng.standard_normal(a.shape[:2])[...,None]*0.035; a[1::3]*=0.95
yy,xx=np.mgrid[0:S,0:S]; r=np.sqrt(((xx-S/2)/(S/2))**2+((yy-S/2)/(S/2))**2); a*=np.clip(1-0.3*(r/1.41)**2,0,1)[...,None]
Image.fromarray((np.clip(a,0,1)*255).astype(np.uint8)).save('assets/output/showa_pr/account/icon_D_colorbar_eizo.png')
EOF
