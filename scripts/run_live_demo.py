"""Generate a real deterministic transcript and simulated animation without GPU/Ollama."""
from pathlib import Path
from src.assembly_demo import assembly_scene, assembly_image
from src.live_controller import LiveController

c=LiveController()
c.set_scene(assembly_scene(),assembly_image(),'guided demo')
for line in ['What can you see?', 'Assemble the cup', 'blue cup', 'yes',
             'white lid', 'yes', 'green straw', 'yes']:
    c.act(line)
assert c.status()['question']['type']=='complete'
assert len(c.assembly.completed)==3
out=Path(__file__).resolve().parents[1]/'examples'/'outputs'
out.mkdir(parents=True,exist_ok=True)
(out/'live_v6_transcript.txt').write_text('\n\n'.join(
    ('Human' if m['role']=='user' else 'Robot')+': '+m['content']
    for m in c.messages),encoding='utf-8')
(out/'live_v6_cup_assembly.gif').write_bytes(c.result['gif'])
(out/'live_v6_cup_assembly.png').write_bytes(c.result['png'])
print('Completed steps:',len(c.assembly.completed))
print('Saved to:',out)
