"""Live v6: no WebRTC server or downloaded GPU weights needed for these tests."""
from PIL import Image
import numpy as np

from src.live_camera import LatestFrame
from src.live_chat import scene_summary, is_visual_question, vision_answer
from src.live_controller import LiveController
from src.assembly_demo import assembly_image, assembly_scene
from src.schema import Scene


def make_ctrl():
    c=LiveController()
    assert c.set_scene(assembly_scene(),assembly_image(),'demo')
    return c


def test_camera_frame_store_and_copy():
    f=LatestFrame()
    assert f.snapshot() is None
    im=Image.new('RGB',(10,10),'red')
    f.store(im)
    seq,out=f.snapshot()
    assert seq==1 and out.getpixel((0,0))==(255,0,0)
    out.putpixel((0,0),(0,0,0))
    assert f.snapshot()[1].getpixel((0,0))==(255,0,0)


def test_webcam_callback_no_streamlit_access():
    class Fake:
        def to_ndarray(self,format):
            assert format=='rgb24'
            return np.zeros((20,30,3),dtype='uint8')
    f=LatestFrame(keep_every=1)
    o=Fake()
    assert f.on_frame(o) is o
    assert f.snapshot()[1].size==(30,20)


def test_detection_only_caption_does_not_claim_glasses():
    text=scene_summary(assembly_scene())
    assert 'cups' in text and 'lids' in text and 'straws' in text
    assert 'glasses' not in text
    assert 'not detected' in scene_summary(Scene(40,40,[]))


def test_scene_qa_without_vlm_truthful():
    c=make_ctrl()
    c.act('What can you see?')
    assert c.messages[-1]['role']=='assistant'
    assert 'vision model' in c.messages[-1]['content'].lower()


def test_scene_qa_calls_vlm_with_image():
    c=make_ctrl()
    seen={}
    def fake(im,text,scene,history):
        seen['size']=im.size
        seen['question']=text
        return 'The image shows a blue cup.'
    c.act('Which cup is blue?',vision_fn=fake)
    assert c.messages[-1]['content']=='The image shows a blue cup.'
    assert seen['size']==(1000,580)


def test_assembly_steps_approval_and_ambiguity():
    c=make_ctrl()
    c.act('Assemble the cup')
    assert c.status()['question']['type']=='choose_part'
    assert c.status()['step']==0
    c.act('yes')
    assert c.status()['question']['type']=='choose_part' # cannot skip a choice
    c.act('blue cup')
    assert c.status()['question']['type']=='approve'
    c.act('yes')
    assert c.status()['step']==1
    assert len(c.assembly.completed)==1
    c.act('white lid')
    c.act('yes')
    assert c.status()['step']==2
    c.act('green straw')
    c.act('yes')
    assert c.status()['question']['type']=='complete'
    assert len(c.assembly.completed)==3
    assert c.result and c.result['png'] and c.result['gif']


def test_freeze_active_scene():
    c=make_ctrl()
    c.act('Assemble the cup')
    assert not c.set_scene(Scene(10,10,[]),Image.new('RGB',(10,10)))
    assert c.scene.width==1000


def test_cancel_stops_execution():
    c=make_ctrl()
    c.act('Assemble the cup')
    c.act('no')
    assert c.status()['question']['type']=='cancelled'
    assert c.result is None
    assert not c.assembly.completed


def test_safety_prevents_progress():
    c=make_ctrl()
    c.act('Assemble the cup')
    c.act('blue cup')
    c.act('yes',human_nearby=True)
    assert c.assembly.index==0 and not c.assembly.completed
    c.act('yes',human_nearby=False)
    assert c.assembly.index==1


def test_vision_question_while_assembly_paused_does_not_approve():
    c=make_ctrl()
    c.act('Assemble the cup')
    c.act('What can you see?')
    assert c.assembly.index==0
    assert c.status()['question']['type']=='choose_part'


def test_local_vlm_failures_are_visible():
    c=make_ctrl()
    def fail(*args):
        raise RuntimeError('offline')
    c.act('What color is the cup?',vision_fn=fail)
    assert 'could not get an answer' in c.messages[-1]['content']


def test_visual_question_classification():
    assert is_visual_question('Do you see someone wearing glasses?')
    assert not is_visual_question('Move the blue cup to the tray')


def test_user_has_to_approve_simple_task():
    c=make_ctrl()
    c.act('Pick up the blue cup')
    # Either directly ready or additional question, but must never simulate automatically.
    assert c.result is None


def test_ollama_request_image_payload(monkeypatch):
    import src.live_chat as mod
    seen={}
    class Resp:
        def raise_for_status(self):
            pass
        def json(self):
            return {'message':{'content':'I can see a cup.'}}
    def fake(url,json,timeout):
        seen['json']=json;seen['url']=url
        return Resp()
    monkeypatch.setattr(mod.requests,'post',fake)
    text=vision_answer(assembly_image(),'What do you see?',assembly_scene(),'fake','http://127.0.0.1:11434')
    assert text=='I can see a cup.'
    assert seen['json']['messages'][-1]['images'][0]
    assert seen['json']['stream'] is False
    assert 'api/chat' in seen['url']
