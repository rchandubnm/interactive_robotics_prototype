"""Small deterministic regression benchmark, not a VLM accuracy benchmark."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.demo import demo_scene
from src.dialogue import Dialogue
S=demo_scene()
CASES=[
('Move the bottle near the person wearing glasses to the tray','target',None),
('Move the blue bottle near the person wearing glasses to the tray','ready','B2'),
('Move the red bottle to the tray','ready','B1'),
('Move the green bottle near the person to the tray','target',None),
('Pick the left bottle','ready','B1'),
('Pick the right bottle','ready','B3'),
('Pick up the bottle','target',None),
('Pick up the cup','ready','C1'),
('Inspect the person wearing glasses','ready','P1'),
('Inspect the person','target',None),
('Move the red bottle','destination','B1'),
('The blue bottle','action',None),
('Move the green bottle to the tray','ready','B3'),
('Move the elephant to the tray','target_missing',None),
('Move the bottle closest to the person wearing glasses to the tray','ready','B1'),
]
results=[]
for text,expected_question,expected_target in CASES:
    d=Dialogue(S);q=d.start(text)
    passed=(q['type']==expected_question and (expected_target is None or d.target_id==expected_target))
    results.append({'instruction':text,'expected_state':expected_question,'actual_state':q['type'],'expected_target':expected_target,'actual_target':d.target_id or None,'pass':passed})
score=sum(r['pass'] for r in results)
out=Path(__file__).resolve().parents[1]/'examples'/'outputs'/'synthetic_benchmark.json'
out.write_text(json.dumps({'description':'Deterministic synthetic demonstration; no VLM tested','total':len(results),'passed':score,'pass_rate':score/len(results),'results':results},indent=2))
print(f'Synthetic cases passed: {score}/{len(results)}')
for r in results:
    if not r['pass']: print('FAIL',r)
if score<len(results):raise SystemExit(1)
