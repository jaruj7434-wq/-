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
# red braided cords exactly where the ref has them
for pts in [[(1200,195),(1270,262),(1342,338),(1372,480),(1380,645)],[(1072,330),(1070,480),(1068,638)]]:
    d.line(pts,fill=(200,30,40),width=10,joint="curve")
# reflected face: mouth visible just right of the raised sleeve, smeared with chocolate, drool
d.ellipse([800,470,875,515],fill=(150,90,80))                 # open-ish mouth
for (x,y,r) in [(790,475,22),(880,480,20),(835,505,26),(815,455,14),(865,455,12),(770,500,12)]:
    d.ellipse([x-r,y-r,x+r,y+r],fill=(85,45,25))              # chocolate smears
d.line([(845,512),(848,560),(852,610),(850,650)],fill=(225,235,240),width=7,joint="curve")  # drool string
d.ellipse([840,640,862,668],fill=(225,235,240))
lab("STATIC shot, 1.75s: she ties her hair, small hand movements",20,10)
lab("HEROINE from behind (very fat), knit vest + white shirt",960,900)
lab("tying her hair with the RED BRAIDED CORD exactly as in the ref",960,935)
lab("(no change)",960,970)
lab("REFLECTION: chocolate smeared all around her mouth,",20,800)
lab("a long string of drool dripping from her mouth",20,835)
lab("bright window",210,300)
lab("dark coat",10,560)
lab("wooden pillar / closet with hangers",1300,40)
im.save("/home/user/-/assets/source/kiminona/cut14-3-mirror-guide.png")
