"""Labelled cup-assembly demo scene. NO model recognition is claimed."""
from PIL import Image, ImageDraw, ImageFont
from .schema import Scene, SceneObject


def assembly_scene() -> Scene:
    return Scene(1000, 580, [
        SceneObject('C1','cup',(115,275,220,405),'red',1.0,{},'Red cup','synthetic ground truth'),
        SceneObject('C2','cup',(245,275,350,405),'blue',1.0,{},'Blue cup','synthetic ground truth'),
        SceneObject('L1','lid',(475,298,555,329),'white',1.0,{},'White lid','synthetic ground truth'),
        SceneObject('L2','lid',(580,298,660,329),'black',1.0,{},'Black lid','synthetic ground truth'),
        SceneObject('S1','straw',(730,225,749,396),'yellow',1.0,{},'Yellow straw','synthetic ground truth'),
        SceneObject('S2','straw',(798,225,817,396),'green',1.0,{},'Green straw','synthetic ground truth'),
        SceneObject('A1','tray',(385,420,670,479),'silver',1.0,{},'Assembly tray','synthetic ground truth'),
    ], source='annotated synthetic cup assembly workspace', notes=['Labels are predefined in demo; they are not YOLO/VLM predictions.'])


def _font(size=18,bold=False):
    try: return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)
    except OSError:
        try: return ImageFont.truetype('arial.ttf',size)
        except OSError: return ImageFont.load_default()


def assembly_image() -> Image.Image:
    im=Image.new('RGB',(1000,580),'#eef4fa'); d=ImageDraw.Draw(im)
    d.rectangle((0,0,1000,81),fill='#172c44')
    d.text((33,21),'CUP ASSEMBLY  /  INTERACTIVE LAB',fill='white',font=_font(25,True))
    d.text((33,94),'Choose components, clarify ambiguity and approve each action',fill='#455a70',font=_font(17))
    d.rounded_rectangle((35,145,962,525),radius=24,fill='#ffffff',outline='#dce6ed',width=3)
    d.rounded_rectangle((380,415,681,484),radius=20,fill='#bfd4e4',outline='#557795',width=5)
    d.text((438,440),'ASSEMBLY TRAY',font=_font(19,True),fill='#476882')
    for x,col,id in [(160,'#e44d54','C1'),(290,'#458be2','C2')]:
        d.ellipse((x-50,270,x+50,300),fill='#f5f9fd',outline='#495869',width=4)
        d.polygon([(x-50,282),(x-39,403),(x+39,403),(x+50,282)],fill=col)
        d.line((x-39,403,x+39,403),fill='#435469',width=4)
        d.ellipse((x-50,269,x+50,296),fill='#fafbfd',outline='#566b80',width=4)
        d.text((x-16,351),id,fill='white',font=_font(20,True))
    for x,col,id in [(515,'#f0f0ed','L1'),(620,'#293c51','L2')]:
        d.rounded_rectangle((x-40,300,x+40,328),radius=13,fill=col,outline='#536278',width=3)
        d.text((x-13,304),id,fill='#25354b' if id=='L1' else 'white',font=_font(17,True))
    for x,col,id in [(740,'#e4c945','S1'),(808,'#40a96d','S2')]:
        d.rounded_rectangle((x-7,226,x+7,393),radius=6,fill=col,outline='#4b6376',width=2)
        d.text((x-12,402),id,fill='#35475b',font=_font(15,True))
    for x,s in [(106,'CUPS'),(468,'LIDS'),(720,'STRAWS')]:
        d.text((x,170),s,fill='#536f88',font=_font(19,True))
    d.text((55,542),'Illustrative demo scene: all object IDs and attributes are predefined',fill='#4f6174',font=_font(14))
    return im
