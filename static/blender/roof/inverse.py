"""Image-only roof silhouette recovery and joined-slope computation."""
from __future__ import annotations
import numpy as np
import cv2


def measure(image):
    rgb=np.asarray(image.convert('RGB'),dtype=np.float32)
    # Natural dark blue-gray roof material versus warm timber and neutral ground.
    mask=((rgb[:,:,2]-rgb[:,:,0]>12)&(rgb[:,:,1]-rgb[:,:,0]>5)&
          (rgb[:,:,0]<165)).astype(np.uint8)
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    n,labels,stats,_=cv2.connectedComponentsWithStats(mask,8)
    if n<2:
        raise ValueError('No roof surface recovered')
    idx=1+int(np.argmax(stats[1:,cv2.CC_STAT_AREA]))
    mask=labels==idx
    yy,xx=np.nonzero(mask)
    if len(xx)<15000:
        raise ValueError('Roof surface too small')
    lo,hi=int(xx.min()),int(xx.max())
    xs=np.arange(lo+0.08*(hi-lo),hi-0.08*(hi-lo),1).astype(int)
    ys=np.array([np.flatnonzero(mask[:,x])[0] if mask[:,x].any() else np.nan for x in xs])
    valid=np.isfinite(ys);xs=xs[valid].astype(float);ys=ys[valid].astype(float)
    # Fit continuous two-line roof edge with an unknown seam position.
    # y = intercept + tilt*x + fold*|x-seam|. This removes common camera tilt.
    best=None
    for seam in np.linspace(lo+0.32*(hi-lo),lo+0.68*(hi-lo),81):
        mat=np.column_stack([np.ones(len(xs)),xs-seam,np.abs(xs-seam)])
        coef=np.linalg.lstsq(mat,ys,rcond=None)[0]
        residual=ys-mat@coef
        error=float(np.mean(np.minimum(residual**2,100)))
        if best is None or error<best[0]:
            best=(error,float(seam),coef)
    error,seam,coef=best
    left_slope=float(coef[1]-coef[2]);right_slope=float(coef[1]+coef[2])
    # Image y points downward. A ridge is /\, so left slope <0, right >0.
    if error>20 or min(abs(left_slope),abs(right_slope))<0.08:
        raise ValueError('Ambiguous or unsupported roof boundary')
    if left_slope<0 and right_slope>0:
        decision='ridge'
    elif left_slope>0 and right_slope<0:
        decision='valley'
    else:
        raise ValueError('Roof has no supported central fold')
    return {'roof_bounds':[lo,int(yy.min()),hi,int(yy.max())],
            'roof_pixels':int(mask.sum()),'seam_x':seam,
            'left_image_slope':left_slope,'right_image_slope':right_slope,
            'fit_mse_clipped':error,'decision':decision,
            'trace':['Segment roof surface from pixels','Extract exposed rear roof edge',
                     'Fit adjoining edge slopes after common tilt','Classify their convex or concave fold']}


def explain_from_image(image,question,choices):
    report=measure(image)
    report['answer']=next(c for c in choices if c.lower()==report['decision'])
    return report


def answer_from_image(image,question,choices):
    return explain_from_image(image,question,choices)['answer']
