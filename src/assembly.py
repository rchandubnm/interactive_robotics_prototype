"""Human-supervised cup assembly conversation in a symbolic workspace.

This state machine is intentionally conservative. Neither a language model nor a
simple "yes" can skip missing-part resolution, per-step approval or safety flags.
Only visible, scene-registered IDs may be selected. Physical manipulation is NOT
implemented here; every action is a 2D symbolic simulation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from .schema import Scene, SceneObject


PARTS = ('cup', 'lid', 'straw')
STEP_NAMES = (
    'Pick up the cup and place it at the assembly station',
    'Pick up the lid and place it onto the cup',
    'Pick up the straw and insert it through the lid opening',
)
STEP_SKILLS = ('position_cup', 'attach_lid', 'insert_straw')
COLORS = ('red', 'blue', 'green', 'yellow', 'black', 'white', 'pink', 'orange', 'purple', 'brown', 'gray', 'silver')
YES = re.compile(r'^(?:(?:yes|yeah|yep|y|ok|okay|sure)(?:[,! ]+(?:please|go ahead|proceed|continue|do it))?|(?:please\s+)?(?:go ahead|proceed|continue|next|do it|approve|start))[.! ]*$', re.I)
NO = re.compile(r'^(?:no|nope|stop|cancel|abort|end|quit)[.! ]*$', re.I)
INFO = re.compile(r'\b(what next|what.s next|what now|what should|explain|why|how|what will|which step|show steps)\b', re.I)
CHANGE = re.compile(r'\b(change|different|instead|another|replace|switch)\b', re.I)


def is_assembly_request(text: str) -> bool:
    return bool(re.search(r'\b(assemble|assembly|put together|build)\b', text, re.I)
                and re.search(r'\b(cup|cups|lid|straw)\b', text, re.I))


@dataclass
class AssemblyDialogue:
    scene: Scene
    instruction: str = ''
    selected: dict[str, str] = field(default_factory=dict)
    index: int = 0
    completed: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, str]] = field(default_factory=list)
    cancelled: bool = False
    requested_colors: dict[str, str] = field(default_factory=dict)

    def _say(self, text: str, kind: str = 'message') -> None:
        self.events.append({'speaker': 'robot', 'kind': kind, 'text': text})

    def _user(self, text: str) -> None:
        self.events.append({'speaker': 'user', 'kind': 'reply', 'text': text})

    def start(self, instruction: str) -> dict:
        if not is_assembly_request(instruction):
            raise ValueError('This dialogue handles cup-assembly instructions only.')
        self.instruction = instruction.strip()
        self.selected.clear(); self.index = 0; self.completed.clear()
        self.events.clear(); self.cancelled = False; self.requested_colors.clear()
        self._user(self.instruction)
        for part in PARTS:
            found = re.search(r'\b(' + '|'.join(COLORS) + r')\s+' + part + r'\b', instruction, re.I)
            if found:
                self.requested_colors[part] = found.group(1).lower()
        self._say('I can assemble a cup in **3 steps**:\n\n'
                  '**Step 1:** Pick up the cup and place it at the assembly station.\n\n'
                  '**Step 2:** Pick up the lid and attach it to the cup.\n\n'
                  '**Step 3:** Pick up the straw and insert it through the lid.\n\n'
                  'I will ask which part you mean when needed, and **wait for your approval before each step**. '
                  'This is a simulated assembly, not real robot movement.', 'plan')
        return self._prompt_current()

    @property
    def current_part(self) -> str | None:
        return PARTS[self.index] if self.index < len(PARTS) else None

    def _candidates(self, part: str) -> list[SceneObject]:
        objects = [o for o in self.scene.objects if o.label.lower() == part]
        desired = self.requested_colors.get(part)
        if desired:
            objects = [o for o in objects if o.color == desired or o.color == 'unknown']
        return objects

    def _prompt_current(self) -> dict:
        q = self.question()
        self._say(q['text'], q['type'])
        return q

    def question(self) -> dict:
        if self.cancelled:
            return {'type': 'cancelled', 'text': 'Task cancelled. No further steps will run.'}
        if self.index >= len(PARTS):
            return {'type': 'complete', 'text': 'Cup assembly completed in the simulation. All three steps were approved individually.'}
        part = PARTS[self.index]
        candidates = self._candidates(part)
        if not candidates:
            return {'type': 'missing', 'part': part, 'options': [],
                    'text': f'Step {self.index+1}: I cannot find a {part} in this scene. Please add or show a {part} and restart the task. I will not invent a missing part.'}
        target_id = self.selected.get(part)
        if not target_id or not any(o.id == target_id for o in candidates):
            if len(candidates) != 1:
                names = ', '.join(o.description_short() for o in candidates)
                return {'type': 'choose_part', 'part': part, 'options': [o.id for o in candidates],
                        'text': f'Step {self.index+1}: I see {len(candidates)} possible {part}s: {names}. Which {part} should I use? You can answer with the color, left/right, or object ID.'}
            target_id = candidates[0].id
        obj = self.scene.get(target_id)
        title = STEP_NAMES[self.index]
        return {'type': 'approve', 'part': part, 'options': [target_id],
                'text': f'**Step {self.index+1} of 3:** {title}.\n\nSelected: **{obj.description_short()}**. '
                        'Shall I proceed with this step? Reply **yes**, **no**, ask **what next?**, or request a different component.'}

    def _resolve_answer(self, part: str, text: str) -> str | None:
        text = text.strip().lower()
        candidates = self._candidates(part)
        ids = [o for o in candidates if re.search(r'\b' + re.escape(o.id.lower()) + r'\b', text)]
        if len(ids) == 1:
            return ids[0].id
        if len(ids) > 1:
            return None
        colors = {color for color in COLORS if re.search(r'\b' + re.escape(color) + r'\b', text)}
        if colors:
            if len(colors) != 1:
                return None
            candidates = [o for o in candidates if o.color in colors]
        left = bool(re.search(r'\bleft(?:most)?\b', text))
        right = bool(re.search(r'\bright(?:most)?\b', text))
        if left == right and not colors:
            return None
        if left != right and candidates:
            extreme = min(o.center()[0] for o in candidates) if left else max(o.center()[0] for o in candidates)
            candidates = [o for o in candidates if o.center()[0] == extreme]
        return candidates[0].id if len(candidates) == 1 else None

    def choose(self, object_id: str, spoken: str = '') -> dict:
        q = self.question()
        if q['type'] != 'choose_part' or object_id not in q['options']:
            raise ValueError('Select one currently offered candidate; no silent guessing.')
        self._user(spoken or object_id)
        self.selected[q['part']] = object_id
        return self._prompt_current()

    def approve(self, human_in_zone: bool = False, path_obstructed: bool = False, spoken: str = 'Yes, proceed') -> bool:
        q = self.question()
        if q['type'] != 'approve':
            raise ValueError('No approved-ready step. Resolve missing or ambiguous parts first.')
        self._user(spoken)
        if human_in_zone or path_obstructed:
            self._say('I cannot proceed: a simulated safety block is active. Clear the block and approve this step again.', 'safety_block')
            return False
        part = PARTS[self.index]
        id_ = self.selected.get(part) or q['options'][0]
        obj = self.scene.get(id_)
        if obj is None or obj.label.lower() != part:
            raise ValueError('The selected part is no longer visible. Please rescan the scene.')
        self.selected[part] = id_
        self.completed.append({'step': self.index+1, 'skill': STEP_SKILLS[self.index],
                               'part': part, 'object_id': id_, 'status': 'simulated',
                               'description': STEP_NAMES[self.index]})
        self._say(f'✅ Step {self.index+1} simulated: {STEP_NAMES[self.index].lower()} using **{obj.description_short()}**.', 'step_complete')
        self.index += 1
        if self.index >= len(PARTS):
            self._say('✅ **Assembly complete in simulation.** The cup, lid and straw were processed in order, with human confirmation at each step.', 'complete')
        else:
            self._prompt_current()
        return True

    def respond_text(self, text: str, human_in_zone: bool = False, path_obstructed: bool = False) -> bool:
        text = text.strip()
        if not text: return False
        q = self.question()
        if q['type'] in ('cancelled', 'complete'):
            self._say('The task has ended. Start a new task to continue.', 'message')
            return False
        if NO.fullmatch(text):
            self._user(text)
            self.cancelled = True
            self._say('Task cancelled on your instruction. No additional simulation steps were executed.', 'cancelled')
            return True
        if INFO.search(text):
            self._user(text)
            self._say(q['text'] + '\n\nYou can confirm this step, choose a different object, or stop the task.', 'explanation')
            return True
        if q['type'] == 'choose_part':
            # Support a combined, explicit answer, e.g. "white lid, then green straw".
            current = q['part']
            explicit = re.search(r'\b(' + '|'.join(COLORS) + r')\s+' + current + r'\b', text, re.I)
            id_ = self._resolve_answer(current, explicit.group(0)) if explicit else self._resolve_answer(current, text)
            if id_:
                self.choose(id_, spoken=text)
                reservations = []
                for part in PARTS[self.index+1:]:
                    hit = re.search(r'\b(' + '|'.join(COLORS) + r')\s+' + part + r'\b', text, re.I)
                    if hit:
                        next_id = self._resolve_answer(part, hit.group(0))
                        if next_id:
                            self.selected[part] = next_id
                            reservations.append(self.scene.get(next_id).description_short())
                if reservations:
                    self._say('I also noted your selection for a later step: ' + ', '.join(reservations) + '. I will still require approval before each step.', 'advance_selection')
                return True
            self._user(text)
            self._say('I am not sure which one you mean. Please specify a **color**, **left/right**, or one of the visible **object IDs**.', 'clarification')
            return False
        if q['type'] == 'missing':
            self._user(text)
            self._say('That component is not registered in the scene. Add or correct it using the workspace controls, then start the task again.', 'missing')
            return False
        if q['type'] == 'approve':
            if CHANGE.search(text):
                earlier = [part for part in PARTS[:self.index] if re.search(r'\b' + part + r'\b', text, re.I)]
                if earlier:
                    self._user(text)
                    self._say(f'The {earlier[0]} step was already simulated. To change it, restart the assembly; I cannot undo previously completed steps.', 'clarification')
                    return False
            if YES.fullmatch(text):
                return self.approve(human_in_zone, path_obstructed, spoken=text)
            if CHANGE.search(text) or re.search(r'\b(' + '|'.join(COLORS) + r')\b', text, re.I):
                id_ = self._resolve_answer(q['part'], text)
                if id_:
                    self._user(text)
                    self.selected[q['part']] = id_
                    self._prompt_current()
                    return True
                self._user(text)
                self.selected.pop(q['part'], None)
                self._prompt_current()
                return False
            self._user(text)
            self._say('I did not interpret that as approval. Reply **yes** to run this step, **no** to cancel, or ask me what to do next.', 'clarification')
            return False
        return False

    def trace(self) -> dict:
        return {'instruction': self.instruction, 'status': self.question()['type'],
                'step_index': self.index, 'selected': self.selected.copy(),
                'completed': self.completed.copy(), 'events': self.events.copy(),
                'simulation_only': True}
