"""Generate authentic outputs by actually executing symbolic pipeline offline."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.demo import demo_scene,demo_image
from src.dialogue import Dialogue
from src.planner import build_plan
from src.simulation import simulate
from src.vision import overlay

root=Path(__file__).resolve().parents[1]
out=root/'examples'/'outputs';out.mkdir(parents=True,exist_ok=True)
scene=demo_scene();pic=demo_image()
pic.save(out/'synthetic_workspace.png')
overlay(pic,scene).save(out/'detected_objects_demo_ground_truth.png')
log={'mode':'synthetic demo only (no YOLO/VLM used)','scene':scene.to_dict(),'cases':[]}

d=Dialogue(scene)
q=d.start('Move the bottle near the person wearing glasses to the tray')
assert q['type']=='target',q
assert sorted(q['options'])==['B1','B2'],q
log['cases'].append({'instruction':d.intent.instruction,'initial_question':q,'dialogue_events':d.events.copy(),'expected':'ambiguous'})
assert d.respond_text('the blue one')
assert d.question()['type']=='ready',d.question()
plan=d.plan()
assert plan.accepted
sim=simulate(scene,plan)
(out/'task_execution.gif').write_bytes(sim['gif'])
(out/'task_final_frame.png').write_bytes(sim['png'])
(out/'plan.json').write_text(json.dumps({'plan':plan.to_dict(),'events':sim['trace'],'dialogue':d.trace(),'output_type':'symbolic 2D simulation, not robot motion'},indent=2),encoding='utf-8')
log['cases'].append({'instruction':d.intent.instruction,'clarification':'the blue one → B2 (blue bottle)','result':plan.to_dict(),'simulation_events':sim['trace'],'expected':'successful symbolic execution'})

d2=Dialogue(scene);q=d2.start('Move the blue bottle near the person wearing glasses to the tray')
assert q['type']=='ready',q
assert d2.target_id=='B2'
log['cases'].append({'instruction':d2.intent.instruction,'result':d2.plan().to_dict(),'expected':'unambiguous'})
blocked=d2.plan(human_in_zone=True)
assert not blocked.accepted
log['cases'].append({'instruction':d2.intent.instruction,'result':blocked.to_dict(),'expected':'simulation blocked by safety flag'})
(out/'demo_trace.json').write_text(json.dumps(log,indent=2),encoding='utf-8')
print('Created sample outputs in',out)
print('Clarification:',q if q['type']=='target' else log['cases'][0]['initial_question'])
print('Simulated plan:',[x['skill'] for x in plan.steps])
print('Files:',', '.join(p.name for p in sorted(out.iterdir())))
