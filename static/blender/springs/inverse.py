"""Pixel-only crossbar localization, spring grouping, and compliance calculation."""
import numpy as np
import cv2


def measure(image):
    rgb = np.asarray(image.convert('RGB'))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    # Natural brass crossbars are chromatic; steel coils and frames are neutral.
    mask = ((hsv[:,:,0] >= 8) & (hsv[:,:,0] <= 38) &
            (hsv[:,:,1] > 65) & (hsv[:,:,2] > 65)).astype(np.uint8)
    mask = cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,5),np.uint8))
    mask = cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((1,55),np.uint8))
    num, labels, stats, centroids = cv2.connectedComponentsWithStats(mask)
    bars = []
    for x,y,w,h,area in stats[1:]:
        if w > 150 and 6 < h < 60 and w/h > 5 and area > 1200:
            bars.append([int(x),int(y),int(w),int(h)])
    if len(bars) not in [6,8]:
        raise ValueError('Cannot recover six or eight distinct brass crossbars: '+str(bars))
    centers = sorted([b[0]+b[2]/2 for b in bars])
    split = (centers[len(centers)//2-1]+centers[len(centers)//2])/2
    groups = [[b for b in bars if b[0]+b[2]/2 < split],
              [b for b in bars if b[0]+b[2]/2 > split]]
    gray = cv2.cvtColor(rgb,cv2.COLOR_RGB2GRAY)
    result = []
    for group in groups:
        group.sort(key=lambda b:b[1])
        stages = []
        for upper,lower in zip(group,group[1:]):
            # Exclude bar faces and eyelets; each coil crosses this central band.
            y1 = upper[1]+upper[3]
            y2 = lower[1]
            ya = int(y1+0.26*(y2-y1))
            yb = int(y1+0.74*(y2-y1))
            xa = int(max(upper[0],lower[0])+7)
            xb = int(min(upper[0]+upper[2],lower[0]+lower[2])-7)
            crop = gray[ya:yb,xa:xb]
            threshold = min(112.0, float(np.median(crop)) * 0.70)
            dark = (crop < threshold).astype(np.uint8)
            # A coil is a persistent vertical band of dark wire. Integrating
            # across its turns bridges horizontal holes without joining coils.
            profile = dark.mean(axis=0)
            active = (profile > 0.13).astype(np.uint8)
            active = cv2.morphologyEx(active.reshape(1,-1), cv2.MORPH_CLOSE,
                                     np.ones((1,17),np.uint8)).reshape(-1)
            transitions = np.diff(np.r_[0,active,0].astype(int))
            starts = np.where(transitions == 1)[0]
            ends = np.where(transitions == -1)[0]
            spans = [[int(a+xa),int(b+xa)] for a,b in zip(starts,ends) if 10 <= b-a <= 48]
            if not 1 <= len(spans) <= 4:
                raise ValueError('Ambiguous spring count: '+str(spans))
            stages.append({'band':[xa,ya,xb,yb], 'spring_spans':spans, 'parallel_count':len(spans)})
        result.append({'crossbars':group,'stages':stages,
                       'compliance':float(sum(1/s['parallel_count'] for s in stages))})
    a,b = [r['compliance'] for r in result]
    separation = abs(a-b)/max(a,b)
    if separation < 0.12:
        raise ValueError('Indistinguishable assembly compliances')
    return {'assemblies':result,'relative_separation':separation,
            'decision':'Left assembly' if a>b else 'Right assembly',
            'trace':'parallel stage stiffness = n*k; series compliance = sum(1/n)/k'}


def explain_from_image(image,question,choices):
    result = measure(image)
    if result['decision'] not in choices:
        raise ValueError('Unsupported choices')
    return result


def answer_from_image(image,question,choices):
    return explain_from_image(image,question,choices)['decision']
