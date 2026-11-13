"""Full stepwise cup assembly state-machine tests."""
import json
import pytest
from PIL import Image
from src.assembly import AssemblyDialogue, is_assembly_request, STEP_NAMES
from src.assembly_demo import assembly_scene, assembly_image
from src.assembly_sim import simulate_assembly
from src.schema import Scene,SceneObject


def dialog():
    d=AssemblyDialogue(assembly_scene())
    d.start('Assemble the cup')
    return d


def test_recognizes_assembly_intent():
    assert is_assembly_request('assemble the cup')
    assert is_assembly_request('Can you put together my cup?')
    assert not is_assembly_request('move the blue bottle')


def test_starts_with_three_step_text_and_questions():
    d=dialog()
    assert len(STEP_NAMES)==3
    assert d.question()['type']=='choose_part' and d.question()['part']=='cup'
    assert 'Step 1' in d.events[1]['text']
    assert 'Step 2' in d.events[1]['text']
    assert 'Step 3' in d.events[1]['text']
    assert d.completed==[]


def test_answer_by_color_does_not_execute():
    d=dialog()
    assert d.respond_text('the blue cup')
    assert d.selected['cup']=='C2'
    assert d.question()['type']=='approve'
    assert len(d.completed)==0


def test_ambiguous_color_requires_specific_reply():
    d=dialog()
    assert not d.respond_text('cup')
    assert d.question()['type']=='choose_part'
    assert not d.respond_text('the red and blue ones')
    assert not d.completed


def test_left_right_reply():
    d=dialog()
    assert d.respond_text('cup on the right')
    assert d.selected['cup']=='C2'


def test_rejects_proceed_before_selection():
    d=dialog()
    assert not d.respond_text('yes')
    assert d.question()['type']=='choose_part'
    with pytest.raises(ValueError): d.approve()


def test_full_three_stage_dialogue():
    d=dialog()
    assert d.respond_text('blue cup')
    assert d.respond_text('what should I do next?')
    assert d.question()['type']=='approve'
    assert d.respond_text('yes')
    assert d.index==1 and d.question()['part']=='lid' and d.question()['type']=='choose_part'
    assert d.respond_text('white lid')
    assert d.question()['type']=='approve'
    assert d.respond_text('proceed')
    assert d.index==2 and d.question()['part']=='straw'
    assert d.respond_text('the green straw')
    assert d.respond_text('go ahead')
    assert d.question()['type']=='complete'
    assert d.selected=={'cup':'C2','lid':'L1','straw':'S2'}
    assert [s['skill'] for s in d.completed]==['position_cup','attach_lid','insert_straw']
    assert all(s['status']=='simulated' for s in d.completed)
    assert sum(e['kind']=='step_complete' for e in d.events)==3


def test_change_selected_lid_before_approval():
    d=dialog();d.respond_text('blue cup');d.approve()
    d.respond_text('white lid')
    assert d.selected['lid']=='L1'
    assert d.respond_text('change to black lid')
    assert d.selected['lid']=='L2'
    assert d.question()['type']=='approve' and len(d.completed)==1


def test_cancel_prevents_rest():
    d=dialog();d.respond_text('C1')
    assert d.respond_text('stop')
    assert d.question()['type']=='cancelled'
    assert d.completed==[]
    with pytest.raises(ValueError): d.approve()


def test_safety_block_halts_progress():
    d=dialog();d.respond_text('red cup')
    assert not d.approve(human_in_zone=True)
    assert d.index==0 and d.completed==[]
    assert not d.approve(path_obstructed=True)
    assert d.question()['type']=='approve'
    assert d.approve()
    assert d.index==1


def test_unknown_or_missing_part_halts():
    s=Scene(640,480,[SceneObject('C1','cup',(0,0,50,50),'red'),SceneObject('L1','lid',(60,0,95,35),'white')])
    d=AssemblyDialogue(s)
    d.start('Assemble the cup')
    assert d.question()['type']=='approve'
    d.approve(); d.approve()
    assert d.question()['type']=='missing' and d.current_part=='straw'
    with pytest.raises(ValueError): d.approve()
    assert len(d.completed)==2


def test_adjective_filter():
    d=AssemblyDialogue(assembly_scene())
    d.start('Assemble the blue cup with a white lid and yellow straw')
    assert d.question()['type']=='approve'
    d.approve()
    assert d.question()['type']=='approve'
    d.approve()
    assert d.question()['type']=='approve'
    d.approve()
    assert d.selected=={'cup':'C2','lid':'L1','straw':'S1'}


def test_invalid_id_rejected():
    d=dialog()
    with pytest.raises(ValueError): d.choose('S1')


def test_visual_outputs_and_traces():
    d=dialog(); d.respond_text('blue cup');d.approve();d.respond_text('black lid');d.approve();d.respond_text('yellow straw');d.approve()
    r=simulate_assembly(d.scene,d.selected,d.completed)
    assert r['gif'][:6] in (b'GIF87a',b'GIF89a')
    assert r['png'][:8]==b'\x89PNG\r\n\x1a\n'
    assert len(r['trace'])==3
    assert json.loads(json.dumps(d.trace()))['simulation_only']
    assert isinstance(assembly_image(),Image.Image)


def test_no_progress_on_unrelated_statement():
    d=dialog();d.respond_text('red cup')
    assert not d.respond_text('I like cats')
    assert d.question()['type']=='approve' and len(d.completed)==0


def test_combined_answer_can_reserve_future_selection():
    d=dialog();d.respond_text('blue cup');d.approve()
    assert d.respond_text('white lid. Then use the green straw.')
    assert d.selected['lid']=='L1'
    assert d.selected['straw']=='S2'
    assert d.question()['type']=='approve' and d.question()['part']=='lid'
    d.approve()
    assert d.question()['type']=='approve' and d.question()['part']=='straw'
    assert len(d.completed)==2
