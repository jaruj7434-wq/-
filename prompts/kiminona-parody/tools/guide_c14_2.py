from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys
src,which,out=sys.argv[1:4]
im=Image.open(src).convert("RGB").resize((1920,1080))
im=im.filter(ImageFilter.GaussianBlur(2)).quantize(colors=18).convert("RGB")
d=ImageDraw.Draw(im)
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",26)
skin=(214,170,140); jacket=(110,120,110); dark=(40,30,30)
def lab(t,x,y): d.text((x,y),t,font=f,fill=(255,255,0),stroke_width=2,stroke_fill=(0,0,0))
def nikuman(x,y,r):
    d.ellipse([x-r,y-int(r*.8),x+r,y+int(r*.8)],fill=(245,240,228),outline=(180,170,150),width=2)
    d.pieslice([x-r//2,y-int(r*.5),x+r//2,y+int(r*.5)],-60,40,fill=(150,90,60))  # bitten, filling
def karaage(x,y,r):
    d.ellipse([x-r,y-int(r*.8),x+r,y+int(r*.8)],fill=(200,125,45),outline=(120,70,20))
if which=="start":
    # fat Keita, front-left 3/4, looking UP-LEFT
    d.ellipse([1060,700,1760,1400],fill=jacket)            # huge body
    d.rectangle([1380,720,1420,1080],fill=(200,200,195))   # zipper stripe
    d.ellipse([1180,400,1470,700],fill=skin)               # chubby head (double chin)
    d.ellipse([1200,610,1440,740],fill=skin)
    d.pieslice([1170,380,1480,560],180,360,fill=dark)      # hair
    for ex in (1255,1355):
        d.ellipse([ex-28,505,ex+28,545],outline=(230,230,230),width=3)  # rimless glasses
        d.ellipse([ex-8,500,ex+6,516],fill=dark)                        # pupils looking up-left
    d.ellipse([1270,600,1330,650],fill=(90,30,30))         # open mouth
    nikuman(1150,980,70)
    lab("KEITA: very fat, rimless glasses, sweaty",960,230)
    lab("chest-up, LOW ANGLE",960,265)
    lab("face UP toward upper-LEFT sky, mouth open",960,300)
    lab("half-eaten NIKUMAN in hand",900,1060-40)
    lab("TV antenna + building",1560,120)
    lab("comet glow / aurora (top)",900,60)
    lab("many KARAAGE meteors streaking down-right",20,520)
    for x,y in [(160,250),(420,350),(640,430),(330,560),(900,560),(980,930)]:
        karaage(x,y,16); d.line([x-90,y-40,x-16,y-6],fill=(255,240,200),width=3)
    lab("camera ORBITS LEFT around him + slow tilt DOWN (3.0s)",20,10)
else:
    # end: seen from behind-left, head in profile looking LEFT
    d.ellipse([1180,560,1900,1300],fill=jacket)
    d.ellipse([1300,250,1590,560],fill=skin)
    d.pieslice([1290,230,1600,520],150,390,fill=dark)       # hair covers back of head
    d.rectangle([1300,420,1330,440],fill=(230,230,230))     # glasses temple / lens edge on left
    d.ellipse([1292,480,1330,520],fill=(90,30,30))          # open mouth at left edge of face
    lab("KEITA from behind-left,",1150,150)
    lab("head turned LEFT watching the comet",1150,185)
    lab("main comet tail = long glowing stream of KARAAGE going down-LEFT",20,120)
    for i in range(9):
        x=900-i*45; y=40+i*72; karaage(x,y,14+i)
    karaage(600,640,12)
    lab("one piece splits off",620,670)
    lab("city skyline at the bottom (night lights)",20,1030)
    lab("END of the orbit, tilted down",20,10)
im.save(out)
