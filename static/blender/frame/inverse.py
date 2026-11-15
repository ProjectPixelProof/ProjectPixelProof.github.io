"""Pixel-only pin detection, bar recovery, and pinned rigidity computation."""
import itertools
import cv2
import numpy as np


def _measure(image):
    rgb=np.asarray(image.convert('RGB'))
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    # Brass hue is a material cue. It does not encode linkage state.
    mask=((hsv[:,:,0]>8)&(hsv[:,:,0]<39)&(hsv[:,:,1]>75)&(hsv[:,:,2]>65)).astype(np.uint8)*255
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    n,labels,stats,centers=cv2.connectedComponentsWithStats(mask)
    pins=[]
    for k in range(1,n):
        x,y,w,h,area=stats[k]
        if 80<area<2200 and .55<w/max(h,1)<1.8 and 10<w<55 and 10<h<55:
            pins.append([float(centers[k][0]),float(centers[k][1])])
    if len(pins)!=8: raise ValueError('ambiguous pivot segmentation: '+str(len(pins)))
    pins.sort(key=lambda p:p[0])
    groups=[pins[:4],pins[4:]]
    # Neutral dark steel bars contrast with the pale mounting plates.
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    dark=gray<175
    records=[]
    for ps in groups:
        p=np.array(ps,float)
        fixed=list(np.argsort(p[:,1])[-2:])
        free=[i for i in range(4) if i not in fixed]
        edges=[]; scores=[]
        for i,j in itertools.combinations(range(4),2):
            d=p[j]-p[i]; length=np.linalg.norm(d); normal=np.array([-d[1],d[0]])/length
            # End exclusion removes heads; a small transverse band tolerates
            # the visible height offset between the pin cap and the steel bar.
            ts=np.linspace(.19,.81,90)
            profiles=[]
            for offset in range(-10,11):
                q=p[i][None,:]+ts[:,None]*d+normal[None,:]*offset
                xy=np.rint(q).astype(int)
                profiles.append(dark[xy[:,1],xy[:,0]])
            support=np.max(np.array(profiles),axis=0)
            score=float(support.mean())
            if .40<score<.80: raise ValueError('ambiguous bar support')
            if score>=.80: edges.append([i,j])
            scores.append({'pair':[i,j],'support':score})
        rows=[]
        for i,j in edges:
            d=p[i]-p[j]; d=d/np.linalg.norm(d)
            row=np.zeros(4)
            if i in free: row[2*free.index(i):2*free.index(i)+2]=d
            if j in free: row[2*free.index(j):2*free.index(j)+2]=-d
            rows.append(row)
        if len(edges) not in (4,5): raise ValueError('unsupported recovered linkage')
        singular=np.linalg.svd(np.array(rows),compute_uv=False)
        rank=int(np.sum(singular>.015))
        records.append({'pivots':ps,'fixed':list(map(int,fixed)),'bars':edges,'bar_scores':scores,'singular_values':singular.tolist(),'constraint_rank':rank,'internal_dof':4-rank})
    mobile=[i for i,r in enumerate(records) if r['internal_dof']>0]
    if len(mobile)!=1: raise ValueError('ambiguous mobility comparison')
    return {'objects':records,'decision':'left' if mobile[0]==0 else 'right','trace':'Recover brass pivot centers; measure continuous steel bars; fix lower two centers; rank bar-length constraints on upper pivots.'}


def explain_from_image(image,question,choices):
    result=_measure(image)
    if result['decision'] not in choices: raise ValueError('unsupported choices')
    return result


def answer_from_image(image,question,choices):
    return explain_from_image(image,question,choices)['decision']
