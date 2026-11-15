"""Pixels only: locate rubber pads and enamel shade, then test support triangle."""
import math
import cv2
import numpy as np


def _components(mask):
    n,l,stats,centroids=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8)
    return [(stats[i],centroids[i],l==i) for i in range(1,n)]


def measure(image):
    a=np.asarray(image.convert('RGB'))
    hsv=cv2.cvtColor(a,cv2.COLOR_RGB2HSV)
    # Yellow enamel is an ordinary material, common to both decisions.
    shade=((hsv[:,:,0]>10)&(hsv[:,:,0]<42)&(hsv[:,:,1]>105)&(hsv[:,:,2]>65))
    shade=cv2.morphologyEx(shade.astype(np.uint8),cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
    shapes=[v for v in _components(shade) if v[0][4]>1500]
    if len(shapes)!=1: raise ValueError('ambiguous shade segmentation')
    st,center,mask=shapes[0]
    contours,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    c=max(contours,key=cv2.contourArea)
    (sx,sy),sr=cv2.minEnclosingCircle(c)
    if sr<35 or sr>110: raise ValueError('shade scale unsupported')
    if cv2.contourArea(c)/(math.pi*sr*sr)<.82: raise ValueError('shade outline not circular')
    # Neutral, very dark rubber. Thin metal legs and small fittings disappear
    # under a disk opening; retain only large compact round support pads.
    gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
    dark=((gray<95)&(hsv[:,:,1]<110)).astype(np.uint8)
    dark=cv2.morphologyEx(dark,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(17,17)))
    pads=[]
    for st,cen,m in _components(dark):
        if st[4]<1800 or st[4]>10000: continue
        cs,_=cv2.findContours(m.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
        cc=max(cs,key=cv2.contourArea)
        (x,y),r=cv2.minEnclosingCircle(cc)
        fill=cv2.contourArea(cv2.convexHull(cc))/(math.pi*r*r)
        if fill>.85 and 25<r<60:
            pads.append([float(x),float(y)])
    if len(pads)!=3: raise ValueError('expected three unoccluded rubber feet, measured %s'%len(pads))
    hub=np.mean(pads,axis=0)
    pads.sort(key=lambda p:math.atan2(p[1]-hub[1],p[0]-hub[0]))
    ds=[]
    for p,q in zip(pads,pads[1:]+pads[:1]):
        dx,dy=q[0]-p[0],q[1]-p[1]
        ds.append((dx*(sy-p[1])-dy*(sx-p[0]))/math.hypot(dx,dy))
    d=min(ds)
    if abs(d)<15: raise ValueError('shade center too near support boundary')
    return {'shade':{'center':[float(sx),float(sy)],'radius':float(sr)},
            'feet':pads,'signed_edge_distances_px':[float(x) for x in ds],
            'margin_px':float(abs(d)), 'decision':'yes' if d>0 else 'no',
            'trace':['segment circular enamel shade','recover three rubber foot centers',
                     'sort feet around centroid','test shade center against all three oriented edges']}


def explain_from_image(image,question,choices):
    return measure(image)


def answer_from_image(image,question,choices):
    d=measure(image)['decision']
    for choice in choices:
        if choice.lower()==d: return choice
    raise ValueError('public choices must contain yes/no')
