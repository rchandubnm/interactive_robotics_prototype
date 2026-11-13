"""Terminal image workflow; interactive disambiguation with real YOLO detections.
Example:
python scripts/run_image.py --image my_scene.jpg --instruction 'Move the bottle to the table' --vlm
"""
from __future__ import annotations
import sys,argparse,json
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.vision import detect_image,overlay
from src.vlm import describe_scene,analyze_attributes,parse_with_llm
from src.dialogue import Dialogue
from src.simulation import simulate

p=argparse.ArgumentParser()
p.add_argument('--image',required=True)
p.add_argument('--instruction',required=True)
p.add_argument('--output',default='image_run')
p.add_argument('--vlm',action='store_true',help='Use local Ollama vision+language parser')
p.add_argument('--model',default='qwen2.5vl:3b')
a=p.parse_args()
im=Image.open(a.image).convert('RGB')
print('Running YOLO detection...')
scene=detect_image(im)
if a.vlm:
    print('Requesting local Qwen VLM...')
    try:
        scene,_=describe_scene(im,scene,model=a.model)
        scene,_=analyze_attributes(im,scene,model=a.model)
    except Exception as exc:print('VLM unavailable; continuing with YOLO/rules:',exc)
print('Visible objects:')
for o in scene.objects:print(' ',o.description_short(),o.attrs)
parsed=parse_with_llm(a.instruction,scene,model=a.model) if a.vlm else None
d=Dialogue(scene);d.start(a.instruction,parsed)
while True:
    q=d.question()
    if q['type']=='ready':break
    print('\nRobot:',q['text'])
    if q['type']=='action':
        print('Options: ',q['options']);choice=input('Action: ').strip().lower()
    else:
        print('Options:')
        for o in q['options']:
            obj=scene.get(o)
            print(' ',obj.description_short() if obj else o)
        choice=input('Choose object ID: ').strip().upper()
    try:d.respond(q['type'],choice)
    except ValueError as e:print(e)
plan=d.plan()
if not plan.accepted:
    print('Blocked:',plan.reason);raise SystemExit(1)
print('\nProposed plan:',json.dumps(plan.to_dict(),indent=2))
if input('Type APPROVE to run 2D SYMBOLIC simulation (no physical motion): ').strip()!='APPROVE':
    print('Operator declined. No simulation run.');raise SystemExit(0)
sim=simulate(scene,plan)
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
(out/'execution.gif').write_bytes(sim['gif'])
(out/'final.png').write_bytes(sim['png'])
overlay(im,scene,d.target_id).save(out/'perception.png')
(out/'trace.json').write_text(json.dumps({'dialogue':d.trace(),'plan':plan.to_dict(),'simulation_events':sim['trace']},indent=2),encoding='utf-8')
print('Saved:',out.resolve())
