"""Pixel-only socket occupancy and ordered run detection."""
import cv2
import numpy as np


def measure(image):
    rgb=np.asarray(image.convert('RGB'))
    # Pale plastic housings on a darker neutral bench. No unique part colors.
    light=((rgb.min(axis=2)>176)&((rgb.max(axis=2)-rgb.min(axis=2))<50)).astype(np.uint8)*255
    light=cv2.morphologyEx(light,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8))
    contours,_=cv2.findContours(light,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    bodies=[]
    for c in contours:
        rect=cv2.minAreaRect(c); a,b=rect[1]
        if min(a,b)>65 and max(a,b)/min(a,b)>3.4 and cv2.contourArea(c)>20000:
            bodies.append((float(rect[0][0]),rect))
    bodies=sorted(bodies,key=lambda b:b[0])
    if len(bodies)!=2:
        raise ValueError('Ambiguous housing detection: '+str(len(bodies)))
    result=[]
    for x,rect in bodies:
        box=cv2.boxPoints(rect).astype(np.float32)
        top=box[np.argsort(box[:,1])[:2]]; bottom=box[np.argsort(box[:,1])[2:]]
        tl,tr=top[np.argsort(top[:,0])]; bl,br=bottom[np.argsort(bottom[:,0])]
        w=int(round((np.linalg.norm(tr-tl)+np.linalg.norm(br-bl))/2))
        h=int(round((np.linalg.norm(bl-tl)+np.linalg.norm(br-tr))/2))
        transform=cv2.getPerspectiveTransform(np.array([tl,tr,br,bl],np.float32),np.array([[0,0],[w-1,0],[w-1,h-1],[0,h-1]],np.float32))
        patch=cv2.warpPerspective(rgb,transform,(w,h))
        dark=(patch.max(axis=2)<150).astype(np.uint8)
        dark[:int(h*.055)]=0; dark[int(h*.945):]=0
        dark[:,:int(w*.16)]=0; dark[:,int(w*.84):]=0
        n,labels,stats,centers=cv2.connectedComponentsWithStats(dark,8)
        parts=[]
        for i in range(1,n):
            xx,yy,ww,hh,area=stats[i]
            if area>=10:
                parts.append(dict(y=float(centers[i][1]),area=int(area),bbox=[int(xx),int(yy),int(ww),int(hh)]))
        parts.sort(key=lambda p:p['y'])
        if len(parts)<5:
            raise ValueError('Not enough visible stations')
        gaps=[parts[i+1]['y']-parts[i]['y'] for i in range(len(parts)-1)]
        cuts=sorted(sorted(range(len(gaps)),key=lambda i:gaps[i],reverse=True)[:4])
        groups=[]; start=0
        for end in cuts+[len(parts)-1]:
            groups.append(parts[start:end+1]); start=end+1
        stations=[]
        for g in groups:
            area=sum(p['area'] for p in g)
            ratio=area/(w*w)
            if .06<ratio<.16:
                raise ValueError('Ambiguous occupancy area')
            stations.append(dict(y=float(np.mean([p['y'] for p in g])),dark_area=area,normalized_area=round(ratio,4),occupied=bool(ratio>.11)))
        empty=[not s['occupied'] for s in stations]
        pairs=[i for i in range(4) if empty[i] and empty[i+1]]
        result.append(dict(center_x=x,housing_size=[w,h],stations=stations,empty_neighbor_pairs=pairs,qualifies=bool(pairs)))
    good=[i for i,s in enumerate(result) if s['qualifies']]
    if len(good)!=1:
        raise ValueError('Expected one unambiguous free pair')
    return dict(strips=result,decision='left' if good[0]==0 else 'right',trace='Detect housings; rectify rows; group dark bores or plug bodies into five ordered stations; classify occupancy by area; find consecutive empty stations.')


def answer_from_image(image,question,choices):
    m=measure(image)
    word='Left' if m['decision']=='left' else 'Right'
    matches=[c for c in choices if c.lower().startswith(word.lower())]
    if len(matches)!=1:
        raise ValueError('Unrecognized choices')
    return matches[0]


def explain_from_image(image,question,choices):
    m=measure(image)
    m['answer']=answer_from_image(image,question,choices)
    return m
