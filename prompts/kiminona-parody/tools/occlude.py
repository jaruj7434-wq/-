import sys,cv2,numpy as np
plate,comp,out=sys.argv[1:4]
p=cv2.imread(plate); c=cv2.imread(comp)
g=cv2.cvtColor(p,cv2.COLOR_BGR2GRAY)
m=np.zeros(g.shape,np.uint8)
roi=(slice(90,445),slice(900,1200))
m[roi]=(g[roi]<75).astype(np.uint8)*255
# metal tip: polygon around nib
cv2.fillPoly(m,[np.array([[924,432],[930,398],[948,398],[952,408],[936,434]],np.int32)],255)
m=cv2.morphologyEx(m,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
m=cv2.GaussianBlur(m,(0,0),1.2).astype(np.float32)[...,None]/255
o=c*(1-m)+p*m
cv2.imwrite(out,o.astype(np.uint8)); cv2.imwrite(out+'.mask.png',(m*255).astype(np.uint8))
