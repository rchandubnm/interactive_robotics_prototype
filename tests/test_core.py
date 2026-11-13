import pytest
from src.demo import demo_scene,demo_image
from src.language import parse_instruction
from src.grounding import resolve
from src.dialogue import Dialogue
from src.planner import build_plan
from src.schema import Scene,SceneObject
from src.simulation import simulate

@pytest.fixture
def scene():return demo_scene()

def test_demo_scene_has_person_with_glasses(scene):
    assert scene.get('P1').attrs['glasses']=='yes'
    assert scene.get('P2').attrs['glasses']=='no'

def test_nlp_extracts_relation_and_destination(scene):
    i=parse_instruction('Move the blue bottle near the person wearing glasses to the tray',scene)
    assert (i.action,i.target_label,i.target_color,i.relation,i.reference_label,i.reference_glasses,i.destination_label)==('move','bottle','blue','near','person','yes','tray')

def test_ambiguous_bottles_prompt_select(scene):
    d=Dialogue(scene)
    q=d.start('Move the bottle near the person wearing glasses to the tray')
    assert q['type']=='target';assert set(q['options'])=={'B1','B2'}
    d.respond('target','B2')
    assert d.question()['type']=='ready'
    assert d.plan().accepted

def test_unambiguous_color_spatial(scene):
    d=Dialogue(scene)
    assert d.start('Move the blue bottle near the person wearing glasses to the tray')['type']=='ready'
    assert d.target_id=='B2' and d.destination_id=='T1'

def test_missing_destination(scene):
    d=Dialogue(scene)
    assert d.start('Move the red bottle')['type']=='destination'
    assert d.target_id=='B1'
    d.respond('destination','T1')
    assert d.question()['type']=='ready'

def test_missing_action(scene):
    d=Dialogue(scene)
    assert d.start('The red bottle')['type']=='action'
    d.respond('action','pick');assert d.question()['type']=='ready'

def test_unknown_eyewear_requires_clarification(scene):
    s=Scene(640,480,[SceneObject('P1','person',(40,20,120,320),attrs={'glasses':'unknown'}),SceneObject('B1','bottle',(140,200,210,310)),SceneObject('B2','bottle',(220,200,290,310)),SceneObject('T1','tray',(370,370,500,410))])
    d=Dialogue(s);q=d.start('Move the bottle near the person wearing glasses to the tray')
    assert q['type']=='target' and 'unverified' in q['text']

def test_no_invented_object(scene):
    i=parse_instruction('Move the elephant to the tray',scene)
    assert i.target_label=='tray' or i.target_label=='unknown' # fallback must not invent elephant
    r=resolve(i,scene)
    assert not any(o.label=='elephant' for o in scene.objects)

def test_safety_flag_blocks(scene):
    d=Dialogue(scene);d.start('Move the red bottle to the tray')
    assert d.plan().accepted
    assert not d.plan(human_in_zone=True).accepted
    assert not d.plan(path_obstructed=True).accepted

def test_no_grasp_person(scene):
    p=build_plan(scene,'pick','P1')
    assert not p.accepted

def test_invalid_selection_rejected(scene):
    d=Dialogue(scene);d.start('Move the bottle near the person wearing glasses to the tray')
    with pytest.raises(ValueError):d.respond('target','B3')

def test_simulation_outputs_valid_gif(scene):
    d=Dialogue(scene);d.start('Move the blue bottle to the tray')
    r=simulate(scene,d.plan())
    assert r['gif'][:6] in (b'GIF87a',b'GIF89a')
    assert r['png'][:8]==b'\x89PNG\r\n\x1a\n'
    assert len(r['trace'])==7

def test_inspect_person(scene):
    d=Dialogue(scene)
    q=d.start('Inspect the person wearing glasses')
    assert q['type']=='ready';assert d.target_id=='P1'
    assert d.plan().accepted

def test_blue_shirt_anchor(scene):
    d=Dialogue(scene)
    q=d.start('Move the bottle near the person in a blue shirt to the tray')
    assert q['type']=='target' and set(q['options'])=={'B1','B2'}

def test_closest_relation(scene):
    d=Dialogue(scene)
    assert d.start('Move the bottle closest to the person wearing glasses to the tray')['type']=='ready'
    assert d.target_id=='B1'

def test_multi_target_does_not_silently_choose(scene):
    d=Dialogue(scene)
    q=d.start('Move the red bottle and blue bottle to the tray')
    assert q['type']=='target' and 'Multiple targets' in q['text']

def test_mock_yolo_vision():
    import numpy as np
    from PIL import Image
    from types import SimpleNamespace
    from src.vision import detect_image
    raw=np.zeros((100,120,3),dtype=np.uint8);raw[20:75,30:65]=(250,15,20)
    box=SimpleNamespace(xyxy=np.array([[30,20,65,75]]),cls=[39],conf=[.93])
    result=SimpleNamespace(boxes=[box],names={39:'bottle'})
    fake=SimpleNamespace(predict=lambda **kwargs:[result])
    s=detect_image(Image.fromarray(raw),model=fake)
    assert len(s.objects)==1 and s.objects[0].label=='bottle'
    assert s.objects[0].color=='red'

def test_mock_vlm_eyewear_crop(monkeypatch):
    from src import vlm
    from PIL import Image
    s=Scene(200,160,[SceneObject('P1','person',(15,15,100,140),attrs={'glasses':'unknown'})])
    monkeypatch.setattr(vlm,'_chat',lambda *args,**kwargs:{'glasses':'yes','shirt_color':'blue','hat':'no','watch':'unknown','description':'Visible dark spectacles and blue top'})
    r,logs=vlm.analyze_attributes(Image.new('RGB',(200,160),'white'),s)
    assert r.get('P1').attrs['glasses']=='yes'
    assert r.get('P1').attrs['hat']=='no'
    assert s.get('P1').attrs['glasses']=='unknown'
    assert len(logs)==1

def test_mock_vlm_description_drops_unseen_ids(monkeypatch):
    from src import vlm
    from PIL import Image
    s=Scene(200,160,[SceneObject('P1','person',(15,15,100,140),attrs={'glasses':'unknown'})])
    monkeypatch.setattr(vlm,'_chat',lambda *args,**kwargs:{'scene_summary':'one person','objects':[{'id':'P1','description':'Person with uncertain glasses','glasses':'unknown'},{'id':'fake123','description':'invented object'}]})
    r,log=vlm.describe_scene(Image.new('RGB',(200,160),'white'),s)
    assert len(r.objects)==1 and r.get('fake123') is None
    assert log['described_count']==1
