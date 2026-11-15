"""Pixel-only rope incidence measurement for exposed planar tackles."""
import numpy as np
import cv2


def _runs(row):
    ids=np.flatnonzero(row)
    if len(ids)==0:return []
    groups=np.split(ids,np.where(np.diff(ids)>1)[0]+1)
    return [(int(g[0]),int(g[-1])) for g in groups if len(g)>=3]


def measure(image):
    rgb=np.asarray(image.convert('RGB'))
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    # Natural tan rope is the sole warm material, not an answer code.
    mask=((hsv[:,:,0]>=8)&(hsv[:,:,0]<=35)&(hsv[:,:,1]>85)&(hsv[:,:,2]>65)).astype(np.uint8)
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    yy,xx=np.nonzero(mask)
    if len(xx)<300:raise ValueError('No sufficiently visible rope')
    ymin,ymax=int(yy.min()),int(yy.max())
    # Long repeated vertical runs define the clear region between fixed and
    # moving sheaves; curved wrap bands are short and fail this persistence test.
    lo=ymin+int(.18*(ymax-ymin)); hi=ymin+int(.70*(ymax-ymin))
    records=[]
    for y in range(lo,hi):
        groups=_runs(mask[y]>0)
        groups=[g for g in groups if g[1]-g[0]<22]
        if 3<=len(groups)<=6:
            records.append((y,tuple(round((a+b)/2) for a,b in groups)))
    best=[]; current=[]
    for rec in records:
        if current and (rec[0]!=current[-1][0]+1 or len(rec[1])!=len(current[-1][1]) or max(abs(a-b) for a,b in zip(rec[1],current[-1][1]))>3):
            if len(current)>len(best):best=current
            current=[]
        current.append(rec)
    if len(current)>len(best):best=current
    if len(best)<35:raise ValueError('Ambiguous rope runs in inter-block gap')
    centers=np.median(np.asarray([p[1] for p in best]),axis=0)
    if min(np.diff(centers))<25:raise ValueError('Unresolved adjacent rope runs')
    # The rightmost rope is followed below the moving sheave band to its free
    # grip; all other vertical strands terminate on or wrap the moving block.
    x=int(centers[-1]); other=[int(c) for c in centers[:-1]]
    bottom=[]
    for cx in [*other,x]:
        rows=np.flatnonzero(np.any(mask[:,max(0,cx-3):cx+4]>0,axis=1))
        bottom.append(int(rows.max()) if len(rows) else -1)
    if bottom[-1]<max(bottom[:-1])+25:raise ValueError('Hauling tail not visibly separate below moving block')
    supports=len(centers)-1
    return {'vertical_rope_x':centers.tolist(),'gap_rows':[best[0][0],best[-1][0]],
       'rope_bottom_rows':bottom,'free_tail_x':x,'supporting_runs':supports,
       'decision':str(supports)+' times',
       'trace':'Identify separate downward hauling tail; exclude it. Each remaining taut vertical run applies one upward tension to the moving assembly.'}


def answer_from_image(image,question,choices):
    result=measure(image)['decision']
    if result not in choices:raise ValueError('Unsupported answer choices')
    return result


def explain_from_image(image,question,choices):
    return measure(image)
