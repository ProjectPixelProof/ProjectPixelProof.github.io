"""Pixel-only pivot recovery followed by full-cycle four-bar closure."""
import math
import numpy as np
import cv2


def measure(image):
    rgb=np.asarray(image.convert('RGB'))
    # Dark circular pin heads are ordinary visible mechanical fasteners.
    gray=cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    mask=(gray<90).astype(np.uint8)*255
    # Remove narrow cast-shadow bridges/tails while retaining round pin cores.
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7)))
    count,labels,stats,centers=cv2.connectedComponentsWithStats(mask)
    pins=[]
    for k in range(1,count):
        x,y,w,h,area=map(int,stats[k])
        if not (350<area<1100 and 18<w<36 and 18<h<36): continue
        if max(w,h)/min(w,h)>1.45: continue
        if area/(w*h)<.60: continue
        pins.append([float(centers[k][0]),float(centers[k][1])])
    if len(pins)!=8:
        raise ValueError('Expected eight unoccluded round pin heads; recovered '+str(len(pins)))
    pins.sort(key=lambda p:p[0])
    groups=[pins[:4],pins[4:]]
    measurements=[]
    for group in groups:
        # In this supported upright configuration both fixed pivots lie below
        # both moving pivots. Infer the grounded pair from visible image order.
        by_y=sorted(group,key=lambda p:p[1],reverse=True)
        ground=sorted(by_y[:2],key=lambda p:p[0])
        moving=sorted(by_y[2:],key=lambda p:p[0])
        A,D=ground; B,C=moving
        a=math.dist(A,B); b=math.dist(B,C); c=math.dist(C,D); g=math.dist(D,A)
        lower=abs(g-a)-abs(b-c)
        upper=b+c-g-a
        margin=min(lower,upper)
        if abs(margin)<12: raise ValueError('Full-cycle closure too close to boundary')
        measurements.append({'pivots_px':[A,B,C,D], 'lengths_px':{'input':a,'coupler':b,'output':c,'ground':g},
                             'crank_distance_range_px':[abs(g-a),g+a],
                             'closure_annulus_px':[abs(b-c),b+c],
                             'endpoint_clearances_px':[lower,upper],
                             'margin_px':margin,'full_turn':margin>0})
    valid=[m['full_turn'] for m in measurements]
    if sum(valid)!=1: raise ValueError('Expected one uniquely feasible full-turn linkage')
    return {'objects':measurements,'decision':'left' if valid[0] else 'right',
            'trace':'The complete crank distance interval must lie strictly inside the two-link closure annulus.'}


def answer_from_image(image,question,choices):
    m=measure(image)
    wanted='Left linkage' if m['decision']=='left' else 'Right linkage'
    if wanted not in choices: raise ValueError('Unsupported choices')
    return wanted


def explain_from_image(image,question,choices):
    result=measure(image)
    result['answer']='Left linkage' if result['decision']=='left' else 'Right linkage'
    return result
