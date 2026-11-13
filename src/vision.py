"""Real YOLO perception and visual annotation. Imports model lazily."""
from __future__ import annotations
from PIL import Image,ImageDraw,ImageFont
import numpy as np
from .schema import Scene,SceneObject

def _dominant_color(crop:Image.Image)->str:
    if crop.width<5 or crop.height<5: return 'unknown'
    import cv2
    arr=np.array(crop.convert('RGB'))
    hsv=cv2.cvtColor(arr,cv2.COLOR_RGB2HSV)
    mask=(hsv[:,:,1]>=65)&(hsv[:,:,2]>=45)
    if int(mask.sum())<max(30,arr.shape[0]*arr.shape[1]*0.04): return 'unknown'
    h=hsv[:,:,0][mask]
    counts={
      'red':np.sum((h<10)|(h>=170)),
      'orange':np.sum((h>=10)&(h<20)),
      'yellow':np.sum((h>=20)&(h<38)),
      'green':np.sum((h>=38)&(h<88)),
      'blue':np.sum((h>=90)&(h<135)),
      'purple':np.sum((h>=135)&(h<170)),
    }
    color,count=max(counts.items(),key=lambda a:a[1])
    return color if float(count)/len(h)>.45 else 'unknown'

def detect_image(im:Image.Image,model=None,confidence=.24)->Scene:
    """Real YOLO inference; model download happens on first use via Ultralytics."""
    if model is None:
        from ultralytics import YOLO
        model=YOLO('yolo11n.pt')
    try:
        import torch
        device=0 if torch.cuda.is_available() else 'cpu'
    except ImportError: device='cpu'
    result=model.predict(source=np.asarray(im.convert('RGB')),conf=float(confidence),device=device,verbose=False)[0]
    objects=[]
    aliases={'dining table':'table','potted plant':'plant','cell phone':'cell phone'}
    for n,box in enumerate(result.boxes):
        x1,y1,x2,y2=[int(round(float(v))) for v in box.xyxy[0].tolist()]
        x1=max(0,x1); y1=max(0,y1);x2=min(im.width,x2);y2=min(im.height,y2)
        if x2<=x1 or y2<=y1:continue
        label=aliases.get(str(result.names[int(box.cls[0])]),str(result.names[int(box.cls[0])]))
        crop=im.crop((x1,y1,x2,y2))
        color=_dominant_color(crop) if label!='person' else 'unknown'
        attrs={'glasses':'unknown','shirt_color':'unknown'} if label=='person' else {}
        objects.append(SceneObject(f'O{n+1}',label,(x1,y1,x2,y2),color,round(float(box.conf[0]),3),attrs,'','YOLO+heuristic color'))
    return Scene(im.width,im.height,objects,source='YOLO image detection',notes=['COCO detector may miss uncommon items such as spectacles and non-COCO objects.','Color estimation is heuristic; attributes need optional VLM validation.'])

def overlay(im:Image.Image,scene:Scene,selected:str='')->Image.Image:
    im=im.convert('RGB').copy()
    d=ImageDraw.Draw(im)
    for obj in scene.objects:
        color='#08a375' if obj.id==selected else '#ec693d'
        w=5 if obj.id==selected else 3
        d.rectangle(obj.bbox,outline=color,width=w)
        txt=f'{obj.id} {obj.label}'+(f' {obj.color}' if obj.color!='unknown' else '')
        if obj.attrs.get('glasses')=='yes': txt+=' · glasses'
        x1,y1,x2,y2=obj.bbox
        # Label stays in image bounds.
        r=(x1,max(0,y1-25),min(im.width,x1+max(94,8*len(txt))),max(22,y1))
        d.rectangle(r,fill=color)
        d.text((r[0]+5,r[1]+4),txt,fill='white')
    return im
