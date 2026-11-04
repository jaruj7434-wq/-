from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys
im=Image.open(sys.argv[1]).convert("RGB").resize((1920,1080))
im=im.filter(ImageFilter.GaussianBlur(2)).quantize(colors=20).convert("RGB")
d=ImageDraw.Draw(im)
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",26)
def lab(t,x,y): d.text((x,y),t,font=f,fill=(255,255,0),stroke_width=2,stroke_fill=(0,0,0))
vest=(214,160,70)
# fatter back: widen the vest silhouette
d.ellipse([780,520,1420,1300],fill=vest)
d.ellipse([990,470,1240,560],fill=(232,236,236))  # collar
# red gummy rope: thick glossy red candy strands
for pts in [[(1210,200),(1300,280),(1380,360),(1390,480),(1385,650)],[(1075,330),(1072,480),(1070,640)]]:
    d.line(pts,fill=(205,25,40),width=16,joint="curve")
    d.line([(x-4,y) for x,y in pts],fill=(255,120,130),width=4,joint="curve")
lab("STATIC shot, 1.75s: she ties her hair, small hand movements",20,10)
lab("HEROINE from behind (very fat), knit vest + white shirt",900,700)
lab("tying her hair with a long RED GUMMY CANDY rope",900,735)
lab("instead of a braided cord",900,770)
lab("her own face reflected in the mirror",430,520)
lab("(tall standing mirror, wooden frame)",430,555)
lab("bright window",210,300)
lab("dark coat",10,560)
lab("wooden pillar / closet with hangers",1300,40)
im.save("/home/user/-/assets/source/kiminona/cut14-3-mirror-guide.png")
