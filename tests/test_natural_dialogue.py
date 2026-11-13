from src.demo import demo_scene
from src.dialogue import Dialogue


def test_blue_one_replies_to_ambiguous_instruction():
    d = Dialogue(demo_scene())
    assert d.start('Move the bottle near the person wearing glasses to the tray')['type'] == 'target'
    assert d.respond_text('the blue one')
    assert d.target_id == 'B2' and d.question()['type'] == 'ready'
    assert d.events[-2]['text'] == 'the blue one'


def test_right_one_is_selected():
    d = Dialogue(demo_scene())
    d.start('Move the bottle near the person wearing glasses to the tray')
    assert d.respond_text('the right one')
    assert d.target_id == 'B2'


def test_unknown_reply_keeps_question_pending():
    d = Dialogue(demo_scene())
    d.start('Move the bottle near the person wearing glasses to the tray')
    assert not d.respond_text('okay sure')
    assert d.question()['type'] == 'target' and not d.target_id


def test_missing_destination_can_answer_naturally():
    d = Dialogue(demo_scene())
    assert d.start('Move the red bottle')['type'] == 'destination'
    assert d.respond_text('put it on the tray')
    assert d.destination_id == 'T1' and d.question()['type'] == 'ready'


def test_action_clarification_in_plain_english():
    d = Dialogue(demo_scene())
    assert d.start('The red bottle')['type'] == 'action'
    assert d.respond_text('Please pick it up')
    assert d.question()['type'] == 'ready'


def test_unrelated_object_rejected():
    d = Dialogue(demo_scene())
    d.start('Move the bottle near the person wearing glasses to the tray')
    assert not d.respond_text('green bottle')
    assert not d.target_id


def test_ids_work_for_choice():
    d = Dialogue(demo_scene())
    d.start('Move the bottle near the person wearing glasses to the tray')
    assert d.respond_text('B1')
    assert d.target_id == 'B1'
