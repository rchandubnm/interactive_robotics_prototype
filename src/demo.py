"""Deterministic annotated synthetic scene for reproducible offline research demos.
Labels and attributes are provided as ground truth, NOT model predictions.
"""
from PIL import Image, ImageDraw, ImageFont
from .schema import Scene, SceneObject

def demo_scene():
    objects=[
      SceneObject('P1','person',(116,152,268,422),'blue',1.0,{'glasses':'yes','shirt_color':'blue'},'Person in blue shirt with glasses','demo_ground_truth'),
      SceneObject('P2','person',(753,150,906,421),'green',1.0,{'glasses':'no','shirt_color':'green'},'Person in green shirt without glasses','demo_ground_truth'),
      SceneObject('B1','bottle',(322,346,371,461),'red',1.0,{},'Red bottle near person P1','demo_ground_truth'),
      SceneObject('B2','bottle',(419,345,468,461),'blue',1.0,{},'Blue bottle near person P1','demo_ground_truth'),
      SceneObject('B3','bottle',(713,345,761,461),'green',1.0,{},'Green bottle near person P2','demo_ground_truth'),
      SceneObject('C1','cup',(519,390,587,460),'yellow',1.0,{},'Yellow cup','demo_ground_truth'),
      SceneObject('T1','tray',(594,479,804,529),'silver',1.0,{},'Placement tray','demo_ground_truth'),
      SceneObject('D1','table',(294,464,849,579),'brown',1.0,{},'Tabletop support','demo_ground_truth'),
    ]
    return Scene(1024,640,objects,source='annotated synthetic illustration',notes=['All labels including glasses are predefined ground truth in demo mode.','Use a real photo with VLM enabled to evaluate image-based eyewear recognition.'])

def _font(size=18,bold=False):
    try: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)
    except OSError:
        try: return ImageFont.truetype('arial.ttf',size)
        except OSError: return ImageFont.load_default()

def demo_image():
    im=Image.new('RGB',(1024,640),'#edf4f8')
    d=ImageDraw.Draw(im)
    for y in range(640):
        c=int(245-15*y/640)
        d.line((0,y,1024,y),fill=(c-2,c+2,min(255,c+6)))
    d.rectangle((0,0,1024,82),fill='#182e48')
    d.text((32,24),'SHARED WORKSPACE  /  SIMULATION LAB',font=_font(24,True),fill='#ffffff')
    d.text((32,97),'Illustrative scene: annotations are ground truth, not model inference',font=_font(16),fill='#4b6279')
    # floor + work surface
    d.rectangle((0,573,1024,640),fill='#e1eaf0')
    d.rounded_rectangle((280,460,865,493),radius=8,fill='#b18566',outline='#7e5640',width=3)
    d.rectangle((298,493,320,600),fill='#8a5b41');d.rectangle((816,493,839,600),fill='#8a5b41')
    # two people / stylized, glasses explicitly visible on P1
    for x,shirt,glasses,name in [(192,'#397cce',True,'P1'),(830,'#39976c',False,'P2')]:
        d.ellipse((x-43,147,x+43,229),fill='#e3af85',outline='#996d55',width=2)
        d.rounded_rectangle((x-67,246,x+67,418),radius=24,fill=shirt)
        d.rectangle((x-45,413,x-12,465),fill='#3b4868')
        d.rectangle((x+12,413,x+45,465),fill='#3b4868')
        d.line((x-62,280,x-86,360),fill='#dcab89',width=18)
        d.line((x+62,280,x+86,360),fill='#dcab89',width=18)
        d.ellipse((x-16,180,x-10,186),fill='#282d3e');d.ellipse((x+12,180,x+18,186),fill='#282d3e')
        d.arc((x-16,187,x+18,206),0,180,fill='#8d4b3f',width=2)
        if glasses:
            d.rounded_rectangle((x-32,175,x-3,199),radius=5,outline='#1a2737',width=5)
            d.rounded_rectangle((x+3,175,x+32,199),radius=5,outline='#1a2737',width=5)
            d.line((x-3,182,x+3,182),fill='#1a2737',width=4)
        d.rounded_rectangle((x-28,423,x+28,451),radius=7,fill='#ffffff',outline='#ccd6e0')
        d.text((x-15,428),name,font=_font(14,True),fill='#24405b')
    # bottles
    for x,col,id in [(346,'#dc4f55','B1'),(444,'#3b83d1','B2'),(737,'#41ad6d','B3')]:
        d.rounded_rectangle((x-24,373,x+24,459),radius=13,fill=col,outline='#4d5260',width=2)
        d.rectangle((x-11,350,x+11,378),fill=col,outline='#4d5260',width=2)
        d.rectangle((x-16,345,x+16,352),fill='#40495e')
        d.rectangle((x-17,397,x+17,432),fill='#e2edf8')
        d.text((x-14,405),id,font=_font(12,True),fill='#1e3451')
    # cup and tray
    d.rounded_rectangle((528,395,572,456),radius=10,fill='#f4c44e',outline='#9d6c25',width=3)
    d.arc((567,407,598,447),270,90,fill='#9d6c25',width=6)
    d.ellipse((528,391,572,403),fill='#fff1ae',outline='#b79035')
    d.rounded_rectangle((594,474,806,525),radius=19,fill='#b0c6d5',outline='#446781',width=6)
    d.rounded_rectangle((609,487,792,516),radius=12,fill='#d8e4ec')
    d.text((673,490),'TRAY',font=_font(16,True),fill='#406075')
    # schematic robot arm, not a real manipulator controller
    d.rounded_rectangle((506,133,586,158),radius=8,fill='#334f72')
    d.line((547,158,547,216),fill='#46678c',width=17)
    d.line((547,216,620,269),fill='#47688d',width=15)
    d.ellipse((532,199,563,231),fill='#dbe8f4',outline='#264862',width=4)
    d.ellipse((606,254,635,283),fill='#dbe8f4',outline='#264862',width=4)
    d.line((621,268,623,308),fill='#46678c',width=13)
    d.line((623,305,606,326),fill='#203f60',width=6)
    d.line((623,305,640,326),fill='#203f60',width=6)
    d.text((619,203),'VIRTUAL ROBOT',font=_font(13,True),fill='#52708a')
    return im
