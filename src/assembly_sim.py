"""Incremental symbolic cup assembly animation; no physical robot control."""
from __future__ import annotations
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from .schema import Scene

PALETTE={'red':'#e85c65','blue':'#539cfa','white':'#f5f5f0','black':'#293647','yellow':'#eac74a','green':'#3dbb80','silver':'#b7cada','unknown':'#b7c3d0'}

def _font(size=18,bold=False):
    try: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)
    except OSError:
        try: return ImageFont.truetype('arial.ttf',size)
        except OSError: return ImageFont.load_default()


def assembly_frame(scene:Scene, selected:dict, completed_count:int, movement:float | None=None) -> Image.Image:
    if not (0 <= completed_count <= 3):
        raise ValueError('Invalid number of assembly steps')
    im=Image.new('RGB',(960,560),'#14253b');d=ImageDraw.Draw(im)
    d.rectangle((0,0,960,82),fill='#0d1829')
    d.text((26,18),'CUP ASSEMBLY  /  SIMULATED WORKCELL',fill='white',font=_font(23,True))
    d.text((27,54),'Human-approved stepwise symbolic assembly',fill='#a2cbde',font=_font(15))
    d.rounded_rectangle((25,102,935,483),radius=20,fill='#1e3b56',outline='#42617c',width=2)
    for x in range(66,938,61): d.line((x,112,x,472),fill='#284761',width=1)
    for y in range(122,474,55): d.line((35,y,925,y),fill='#284761',width=1)
    d.text((68,131),'SOURCE COMPONENTS',fill='#b0cfe2',font=_font(18,True))
    d.text((555,131),'ASSEMBLY STATION',fill='#b0cfe2',font=_font(18,True))
    spots={'cup':(125,330),'lid':(267,330),'straw':(398,330)}
    for part,(x,y) in spots.items():
        obj=scene.get(selected.get(part,''))
        label=obj.description_short() if obj else 'Not chosen'
        d.rounded_rectangle((x-59,230,x+59,408),radius=14,fill='#274862',outline='#587b96',width=2)
        color=PALETTE.get(obj.color if obj else 'unknown','#b7c3d0')
        if ('cup','lid','straw').index(part) >= completed_count:
            if part=='cup':
                d.polygon([(x-34,270),(x-25,359),(x+25,359),(x+34,270)],fill=color)
                d.ellipse((x-34,259,x+34,283),fill='#edf4f8',outline='#879daf',width=3)
            elif part=='lid': d.rounded_rectangle((x-43,304,x+43,330),radius=9,fill=color,outline='#dce7eb',width=2)
            else: d.rounded_rectangle((x-7,260,x+7,364),radius=4,fill=color,outline='#f0f3f7',width=2)
        else:
            d.text((x-23,308),'USED',fill='#b4d9e2',font=_font(15,True))
        d.text((x-48,382),part.upper(),fill='#e4eef7',font=_font(13,True))
        d.text((x-48,412),label[:20],fill='#b2cadd',font=_font(12))
    d.rounded_rectangle((536,379,866,419),radius=13,fill='#b8cfdf',outline='#d9e9f5',width=3)
    d.text((638,425),'Assembly tray',fill='#b9d5e8',font=_font(15))
    center=702
    # Completed milestones persist. The last active phase can be animated from source to destination.
    cup=scene.get(selected.get('cup',''))
    if completed_count>=1:
        cc=PALETTE.get(cup.color if cup else 'unknown','#a5b6c5')
        d.polygon([(center-42,264),(center-31,379),(center+31,379),(center+42,264)],fill=cc)
        d.ellipse((center-42,254,center+42,280),fill='#ecf3fa',outline='#7798ae',width=4)
        d.text((center-14,317),'CUP',fill='#10253a',font=_font(14,True))
    if completed_count>=2:
        lid=scene.get(selected.get('lid',''))
        lc=PALETTE.get(lid.color if lid else 'unknown','#f0f0f0')
        d.rounded_rectangle((center-48,241,center+48,272),radius=10,fill=lc,outline='#cbd8e1',width=3)
        d.ellipse((center-12,246,center+12,256),fill='#607a8e')
    if completed_count>=3:
        straw=scene.get(selected.get('straw',''))
        sc=PALETTE.get(straw.color if straw else 'unknown','#eed36a')
        d.rounded_rectangle((center-5,171,center+5,304),radius=4,fill=sc,outline='#dfe8ee',width=1)
    if movement is not None and completed_count < 3:
        # An illustrative end-effector transports the next component symbol.
        part=('cup','lid','straw')[completed_count]
        obj=scene.get(selected.get(part,''))
        if obj:
            sx,sy=spots[part]
            ey={'cup':300,'lid':253,'straw':214}[part]
            ex=center
            p=max(0.0,min(1.0,float(movement)))
            x=int(sx+(ex-sx)*p)
            y=int(sy+(ey-sy)*p-40*max(0,1-abs(2*p-1)))
            d.line((sx,sy,ex,ey),fill='#648fa7',width=3)
            fill=PALETTE.get(obj.color,PALETTE['unknown'])
            if part=='cup':
                d.polygon([(x-23,y-23),(x-16,y+22),(x+16,y+22),(x+23,y-23)],fill=fill)
            elif part=='lid':
                d.rounded_rectangle((x-28,y-10,x+28,y+10),radius=6,fill=fill,outline='white',width=2)
            else:
                d.rounded_rectangle((x-5,y-32,x+5,y+32),radius=4,fill=fill,outline='white',width=1)
            # Symbolic gripper, not a collision-checked robot arm.
            d.line((x,y-67,x,y-29),fill='#a2d6ec',width=8)
            d.line((x,y-29,x-15,y-15),fill='#a2d6ec',width=5)
            d.line((x,y-29,x+15,y-15),fill='#a2d6ec',width=5)
    label=['READY','CUP POSITIONED','LID ATTACHED','STRAW INSERTED'][completed_count]
    d.text((27,500),f'PROGRESS  {completed_count}/3  ·  {label}',fill='white',font=_font(21,True))
    d.text((27,537),'2D symbolic animation. Does not simulate forces, grasping physics or real motion.',fill='#a2cbde',font=_font(13))
    return im


def simulate_assembly(scene:Scene, selected:dict, completed:list[dict]) -> dict:
    n=len(completed)
    if n>3: raise ValueError('At most three steps supported')
    # Display each human-approved operation separately with motion tween frames.
    frames=[assembly_frame(scene,selected,0)]
    durations=[600]
    for step in range(n):
        for p in (0.08,0.25,0.45,0.65,0.85,0.98):
            frames.append(assembly_frame(scene,selected,step,movement=p))
            durations.append(150)
        frames.append(assembly_frame(scene,selected,step+1))
        durations.append(850)
    if n==0: durations=[600]
    out=BytesIO()
    frames[0].save(out,format='GIF',save_all=True,append_images=frames[1:],duration=durations,loop=0,optimize=True)
    last=BytesIO(); frames[-1].save(last,format='PNG')
    return {'gif':out.getvalue(),'png':last.getvalue(),'trace':completed.copy()}
