from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys, math, random
im=Image.open(sys.argv[1]).convert("RGB").resize((1920,1080))
im=im.filter(ImageFilter.GaussianBlur(2)).quantize(colors=16).convert("RGB")
d=ImageDraw.Draw(im)
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",26)
# erase original comet
d.ellipse([1230,240,1380,380],fill=im.getpixel((1200,380)))
# glow + karaage (lumpy golden blob)
glow=Image.new("L",(1920,1080),0); gd=ImageDraw.Draw(glow); gd.ellipse([1200,215,1410,405],fill=170)
glow=glow.filter(ImageFilter.GaussianBlur(30)); im.paste(Image.new("RGB",(1920,1080),(255,245,215)),(0,0),glow)
d=ImageDraw.Draw(im)
# nikuman: white round bun, pleated top
d.ellipse([1245,262,1365,352],fill=(245,240,228),outline=(200,190,170),width=2)
for k in range(-4,5):
    d.line([1305,272,1305+k*13,300],fill=(205,195,175),width=3)
d.ellipse([1297,266,1313,280],fill=(225,215,195))
for (x,y) in [(652,135),(995,592),(745,765),(1480,485)]:
    d.ellipse([x-11,y-11,x+11,y+11],fill=(255,40,30))
for t,x,y in [("STATIC low-angle night sky, NO camera move (2.0s)",20,10),
              ("glowing giant NIKUMAN (steamed meat bun) = the moon/comet",960,140),("small & distant in the sky",1160,175),
              ("crane 1 lattice mast + red warning lights",20,330),
              ("crane 2 cab + jib to upper right, red lights blink",1110,640),
              ("building top (dark)",1360,1000),
              ("clouds",20,150),("clouds",1560,900)]:
    d.text((x,y),t,font=f,fill=(255,255,0),stroke_width=2,stroke_fill=(0,0,0))
im.save("/home/user/-/assets/source/kiminona/cut14-1-cranes-guide.png")
