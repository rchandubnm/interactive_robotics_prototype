"""Offline simulation example: generate preview, GIF and full dialogue transcript.

python scripts/run_assembly_demo.py
"""
from pathlib import Path
import sys
import json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.assembly_demo import assembly_scene, assembly_image
from src.assembly import AssemblyDialogue
from src.assembly_sim import simulate_assembly

root=Path(__file__).resolve().parents[1]/'examples'/'outputs'
root.mkdir(parents=True,exist_ok=True)
scene=assembly_scene();dialog=AssemblyDialogue(scene)
dialog.start('Assemble the cup')
for answer in ('blue cup','yes','white lid','yes','green straw','yes'):
    if not dialog.respond_text(answer):
        raise RuntimeError(f'Unexpected clarification failure on {answer}')
if dialog.question()['type']!='complete':
    raise RuntimeError('Assembly did not reach completed state')
result=simulate_assembly(scene,dialog.selected,dialog.completed)
(root/'cup_assembly.gif').write_bytes(result['gif'])
(root/'cup_assembly.png').write_bytes(result['png'])
(root/'cup_assembly_trace.json').write_text(json.dumps(dialog.trace(),indent=2),encoding='utf8')
assembly_image().save(root/'cup_assembly_workspace.png')
for msg in dialog.events:
    print(f"{msg['speaker'].upper()}: {msg['text']}")
print('\nResults written to',root)
