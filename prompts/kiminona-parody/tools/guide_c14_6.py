from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys
im=Image.open(sys.argv[1]).convert("RGB").resize((1920,1080))
im=im.filter(ImageFilter.GaussianBlur(2)).quantize(colors=20).convert("RGB")
d=ImageDraw.Draw(im)
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",26)
def lab(t,x,y): d.text((x,y),t,font=f,fill=(255,255,0),stroke_width=2,stroke_fill=(0,0,0))
white=(225,232,235); dark=(40,45,55)
# heroine (left) fatter: wide blouse + skirt
d.ellipse([380,580,640,800],fill=white); d.ellipse([370,730,650,960],fill=dark)
# keita (right) fatter
d.ellipse([1220,510,1520,780],fill=white); d.rectangle([1300,720,1510,1080],fill=dark); d.ellipse([1270,700,1530,860],fill=dark)
# red cord in heroine's hair
d.line([(600,520),(598,570),(602,600)],fill=(210,30,30),width=8)
# onigiri-shaped cloud hint (top right sky)
lab("EXTREME LOW ANGLE from below, bright blue summer sky",20,10)
lab("camera slowly PULLS BACK (they get smaller) + slight tilt up, ends in white fade (1.5s)",20,45)
lab("HEROINE (EXTREMELY fat) from behind-left, ponytail w/ red cord",250,1000)
lab("blowing in the wind, looking up at the sky",250,1035)
lab("KEITA (EXTREMELY fat) from behind,",1100,330)
lab("hands in pockets, looking up",1100,365)
lab("sky and clouds EXACTLY as in the reference",20,520)
im.save("/home/user/-/assets/source/kiminona/cut14-6-sky-guide.png")
