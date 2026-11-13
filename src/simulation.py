"""Reproducible *symbolic* tabletop execution animation.

Object positions are image-normalized display points. This is NOT inverse
kinematics, collision planning, depth estimation, or real robot motion.
"""
from __future__ import annotations
from PIL import Image,ImageDraw,ImageFont
from io import BytesIO
from .schema import Scene,Plan

W,H=1024,650
COLORS={'red':'#eb656f','blue':'#5a9dec','green':'#4cd19c','yellow':'#f5c659','silver':'#becad7','brown':'#ad8064','unknown':'#95a8bf'}

def _font(sz=17,bold=False):
    try:return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',sz)
    except OSError:
        try:return ImageFont.truetype('arial.ttf',sz)
        except OSError:return ImageFont.load_default()

def _pos(scene,obj):
    x,y=obj.center()
    return int(48+928*x/max(1,scene.width)),int(145+380*y/max(1,scene.height))

def render_frame(scene:Scene,plan:Plan,phase:int):
    if not plan.accepted: raise ValueError('Cannot animate a rejected plan')
    target=scene.get(plan.target_id)
    dest=scene.get(plan.destination_id) if plan.destination_id else None
    if target is None:raise ValueError('Missing target')
    frames=['Perceive','Approach','Grasp','Lift','Transport','Release','Verify'] if plan.action=='move' else ['Perceive','Approach','Act','Verify']
    phase=min(max(phase,0),len(frames)-1)
    im=Image.new('RGB',(W,H),'#13233a');d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,90),fill='#0d1729')
    d.text((28,18),'INTERACTIVE ROBOT / SYMBOLIC EXECUTION',font=_font(24,True),fill='white')
    d.text((28,56),'2D image-space replay  |  NOT physical motion',font=_font(15),fill='#9ec7dc')
    d.rounded_rectangle((26,112,998,554),radius=20,fill='#1b3450',outline='#385570',width=2)
    # Workcell grid
    for x in range(63,987,55):d.line((x,120,x,545),fill='#25425e',width=1)
    for y in range(135,550,55):d.line((33,y,989,y),fill='#25425e',width=1)
    tpos=_pos(scene,target)
    destpos=_pos(scene,dest) if dest else tpos
    if dest:
        d.line((tpos,destpos),fill='#6b92be',width=5)
        for j in range(1,5):
            x=tpos[0]+(destpos[0]-tpos[0])*j/5
            y=tpos[1]+(destpos[1]-tpos[1])*j/5
            d.ellipse((x-5,y-5,x+5,y+5),fill='#a3caef')
    # Drawing order: destinations and stationary objects first
    for obj in scene.objects:
        if obj.id==target.id:continue
        x,y=_pos(scene,obj)
        color=COLORS.get(obj.color,COLORS['unknown'])
        if obj.label=='person':
            d.ellipse((x-19,y-42,x+19,y-4),fill='#e5b396',outline='#fff1e2',width=2)
            d.rounded_rectangle((x-26,y-2,x+26,y+46),radius=9,fill=color)
            if obj.attrs.get('glasses')=='yes':
                d.rectangle((x-16,y-30,x-3,y-18),outline='#162339',width=3)
                d.rectangle((x+3,y-30,x+16,y-18),outline='#162339',width=3)
                d.line((x-3,y-24,x+3,y-24),fill='#162339',width=2)
        elif obj.label in ('tray','table'):
            d.rounded_rectangle((x-53,y-16,x+53,y+17),radius=11,fill=color,outline='#e6eef6',width=2)
        else:
            d.ellipse((x-19,y-19,x+19,y+19),fill=color,outline='#e9f4ff',width=2)
        d.text((x-20,y+30 if obj.label!='person' else y+51),obj.id+' '+obj.label,font=_font(12),fill='#d4e6f2')
    # Animate an abstract object icon. Avoid changing photographic pixels.
    progress = [0,0,0,0,.65,1,1][phase] if plan.action=='move' else 0
    x=int(tpos[0]+(destpos[0]-tpos[0])*progress)
    y=int(tpos[1]+(destpos[1]-tpos[1])*progress - (24 if phase in (3,4) and plan.action=='move' else 0))
    col=COLORS.get(target.color,COLORS['unknown'])
    d.ellipse((x-24,y-24,x+24,y+24),fill=col,outline='#ffffff',width=4)
    d.text((x-13,y-9),target.id,font=_font(13,True),fill='#0d2035')
    # Draw virtual gripper on approach/grasp/transport
    if phase in (1,2,3,4,5):
        gx,gy=x,y-42
        d.line((gx,gy-31,gx,gy-4),fill='#a8d2e7',width=9)
        d.line((gx,gy-4,gx-14,gy+8),fill='#a8d2e7',width=4)
        d.line((gx,gy-4,gx+14,gy+8),fill='#a8d2e7',width=4)
    # Footer
    d.text((30,568),f'STAGE {phase+1}/{len(frames)}  ·  {frames[phase]}',font=_font(21,True),fill='#f4f8ff')
    d.text((30,608),f'Target: {target.description_short()}'+(f'   →   Destination: {dest.description_short()}' if dest else ''),font=_font(16),fill='#a9c4da')
    d.text((750,574),'SIMULATION ONLY',font=_font(16,True),fill='#f6c86b')
    return im

def simulate(scene:Scene,plan:Plan):
    count=7 if plan.action=='move' else 4
    frames=[render_frame(scene,plan,i) for i in range(count)]
    stream=BytesIO()
    frames[0].save(stream,format='GIF',save_all=True,append_images=frames[1:],duration=650,loop=0,optimize=True)
    pic=BytesIO();frames[-1].save(pic,format='PNG')
    trace=[{'step':i+1,'event':label,'status':'simulated'} for i,label in enumerate((['perceive','approach','grasp','lift','transport','release','verify'] if plan.action=='move' else ['perceive','approach','act','verify']))]
    return {'gif':stream.getvalue(),'png':pic.getvalue(),'trace':trace,'frames':frames}
