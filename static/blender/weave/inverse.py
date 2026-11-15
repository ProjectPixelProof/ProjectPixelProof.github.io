"""Pixel-only occlusion measurement followed by sequence inspection."""
import numpy as np
import cv2


def measure(image):
    rgb=np.asarray(image.convert('RGB')).astype(np.float32)
    R,G,B=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
    blue=(B>R*1.30)&(B>G*1.12)&(B-R>24)&(B>55)
    wood=(R>G*1.12)&(G>B*1.16)&(R-B>25)
    yy,xx=np.nonzero(blue)
    if len(xx)<1500: raise ValueError('Insufficient visible strap')
    pts=np.column_stack([xx,yy]).astype(float)
    origin=np.mean(pts,axis=0)
    cov=np.cov(pts.T); val,vec=np.linalg.eigh(cov); axis=vec[:,-1]
    if axis[1]<0:axis=-axis
    normal=np.array([axis[1],-axis[0]])
    H,W=blue.shape
    gy,gx=np.indices((H,W))
    px=(gx-origin[0])*axis[0]+(gy-origin[1])*axis[1]
    qx=(gx-origin[0])*normal[0]+(gy-origin[1])*normal[1]
    # Width is estimated from the strap pixels, independent of bar count.
    qblue=(pts-origin)@normal
    width=float(np.percentile(qblue,97)-np.percentile(qblue,3))
    if width<20:raise ValueError('Strap too narrow')
    side=(np.abs(qx)>width*.85)&(np.abs(qx)<width*1.5)
    bins=np.floor(px+H).astype(np.int32)
    sw=np.bincount(bins[side&wood],minlength=3*H)
    st=np.bincount(bins[side],minlength=3*H)
    profile=sw/np.maximum(st,1)
    active=(profile>.58).astype(np.uint8)
    # Separate rung bands, rejecting isolated pixels and end-clamp supports.
    runs=[];beg=None
    for i,v in enumerate(active):
        if v and beg is None:beg=i
        if beg is not None and (not v or i==len(active)-1):
            stop=i
            if stop-beg>=8:runs.append((beg-H,stop-H))
            beg=None
    # Frame rails lie outside the side strips; actual rungs span both sides.
    states=[]; measured=[]
    for lo,hi in runs:
        mid=(lo+hi)/2
        region=(np.abs(px-mid)<max(2,(hi-lo)*.20))&(np.abs(qx)<width*.27)
        score=float(np.mean(blue[region])) if np.any(region) else .5
        if .15<score<.85:raise ValueError('Ambiguous crossing')
        state='over' if score>=.85 else 'under'
        states.append(state)
        measured.append(dict(position=float(mid),band_width=float(hi-lo),blue_fraction=score,state=state))
    if not 5<=len(states)<=7:raise ValueError('Expected five to seven exposed bars; found '+str(len(states)))
    alternating=all(a!=b for a,b in zip(states,states[1:]))
    return dict(strap_width_px=width,axis=axis.tolist(),crossings=measured,
                states=states,violations=[i for i in range(len(states)-1) if states[i]==states[i+1]],
                decision='yes' if alternating else 'no')


def answer_from_image(image,question,choices):
    d=measure(image)['decision']
    for choice in choices:
        if choice.lower()==d:return choice
    raise ValueError('Unsupported choices')


def explain_from_image(image,question,choices):
    return measure(image)
