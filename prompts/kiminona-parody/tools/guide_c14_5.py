from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys, random
im=Image.open(sys.argv[1]).convert("RGB").resize((1920,1080))
im=im.filter(ImageFilter.GaussianBlur(2)).quantize(colors=22).convert("RGB")
base=im.copy()
d=ImageDraw.Draw(im)
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",26)
def lab(t,x,y): d.text((x,y),t,font=f,fill=(255,255,0),stroke_width=2,stroke_fill=(0,0,0))
lit=im.getpixel((960,400))
# fatter: wide parka shoulders + round cheeks/double chin (lit from below)
d.ellipse([520,470,1400,800],fill=(95,100,80))
d.ellipse([770,330,1150,560],fill=lit)
d.ellipse([820,500,1100,600],fill=lit)
d.ellipse([925,415,995,455],fill=(120,60,50))               # mouth slightly open
random.seed(5)
for _ in range(9):
    x=960+random.gauss(0,45); y=440+random.gauss(0,18); r=random.uniform(10,20)
    d.ellipse([x-r,y-r,x+r,y+r],fill=(80,42,22))             # chocolate smears
d.ellipse([925,415,995,455],outline=(120,60,50),width=6)
# put the foreground head silhouette back in front
import numpy as np
b=np.array(base).astype(int); m=(b.sum(2)<170); m[:600,:]=False
arr=np.array(im); arr[m]=b[m]; im.paste(Image.fromarray(arr.astype('uint8')))
d=ImageDraw.Draw(im)
lab("STATIC 1.42s, dim library between bookshelves",20,10)
lab("KEITA (very fat, rimless glasses), gray-green parka",1130,120)
lab("leaning forward, looking DOWN at an open book,",1130,155)
lab("shocked: eyes wide, mouth open",1130,190)
lab("CHOCOLATE smeared around his mouth",1180,450)
lab("warm light from BELOW (the open book) on the lower face",20,330)
lab("blurred dark-haired head silhouette (friend), foreground",560,1000)
lab("window light gradient",20,700)
im.save("/home/user/-/assets/source/kiminona/cut14-5-library-guide.png")
