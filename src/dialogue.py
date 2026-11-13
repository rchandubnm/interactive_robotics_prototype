"""Conservative, multi-turn clarification dialogue for a simulated robot.

A spoken reply is *never* treated as a target unless it selects exactly one
currently allowed object. The VLM/NLP parser is deliberately separate from
this state machine and cannot skip approval or safety validation.
"""
from dataclasses import dataclass, field
import re

from .schema import Scene, Intent
from .language import parse_instruction, ALIASES, COLORS
from .grounding import resolve, destination_candidates
from .planner import build_plan


@dataclass
class Dialogue:
    scene: Scene
    intent: Intent | None = None
    target_id: str = ''
    destination_id: str = ''
    events: list[dict] = field(default_factory=list)
    confirmed: bool = False

    def start(self, instruction: str, parsed: Intent | None = None):
        instruction = instruction.strip()
        self.intent = parsed if parsed is not None else parse_instruction(instruction, self.scene)
        self.target_id = ''
        self.destination_id = ''
        self.confirmed = False
        self.events = [{'speaker': 'user', 'text': instruction, 'kind': 'instruction'}]
        self._auto_resolve()
        q = self.question()
        self.events.append({'speaker': 'robot', 'text': q['text'], 'kind': q['type']})
        return q

    def _auto_resolve(self):
        if not self.intent:
            return
        r = resolve(self.intent, self.scene)
        if not r.uncertain and len(r.candidates) == 1:
            self.target_id = r.candidates[0]
        destinations = destination_candidates(self.intent, self.scene)
        if len(destinations) == 1:
            self.destination_id = destinations[0]

    def question(self):
        if self.intent is None:
            return {'type': 'instruction', 'text': 'Tell me what you would like to do.'}
        if self.intent.action == 'unknown':
            return {'type': 'action', 'text': 'Would you like me to move, pick up, or inspect the object?', 'options': ['move', 'pick', 'inspect']}
        if not self.target_id:
            r = resolve(self.intent, self.scene)
            if not r.candidates:
                return {'type': 'target_missing', 'text': 'I could not find a clear match. Which visible object do you mean?', 'options': [o.id for o in self.scene.objects]}
            message = (r.reason + ' Which object do you mean?') if r.uncertain else 'I found more than one possible match. Which object do you mean?'
            return {'type': 'target', 'text': message, 'options': r.candidates}
        if self.intent.action == 'move' and not self.destination_id:
            destinations = destination_candidates(self.intent, self.scene)
            alternatives = [o.id for o in self.scene.objects if o.id != self.target_id and o.label in ('tray', 'table', 'box', 'cup', 'bottle')]
            return {'type': 'destination', 'text': 'Where should I place it?', 'options': destinations or alternatives}
        return {'type': 'ready', 'text': 'I have the target and action. Here is the plan for your approval.'}

    def respond(self, kind: str, value: str, spoken_text: str | None = None):
        question = self.question()
        if question['type'] != kind:
            raise ValueError(f'Expected {question["type"]!r} answer, got {kind!r}')
        if kind == 'action':
            if value not in ('move', 'pick', 'inspect'):
                raise ValueError('Unsupported action')
            self.intent.action = value
        elif kind in ('target', 'target_missing'):
            if not self.scene.get(value) or value not in question['options']:
                raise ValueError('Object not an allowed candidate')
            self.target_id = value
        elif kind == 'destination':
            if value not in question['options']:
                raise ValueError('Destination not an allowed candidate')
            self.destination_id = value
        else:
            raise ValueError('No clarification needed')
        self.confirmed = False
        displayed = spoken_text.strip() if spoken_text and spoken_text.strip() else value
        self.events.append({'speaker': 'user', 'kind': 'clarification_' + kind, 'text': displayed})
        nextq = self.question()
        self.events.append({'speaker': 'robot', 'kind': nextq['type'], 'text': nextq['text']})
        return nextq

    def _interpret_text(self, kind: str, text: str) -> str | None:
        """Resolve plain English against currently permitted choices only.

        Returns None if zero or multiple candidates match; does not guess.
        """
        text = text.lower().strip()
        if not text:
            return None
        if kind == 'action':
            groups = {
                'move': r'\b(move|place|put|transfer|shift|carry|bring)\b',
                'pick': r'\b(pick|grab|grasp|lift|take)\b',
                'inspect': r'\b(inspect|look|describe|check|examine|identify|scan)\b',
            }
            matches = [action for action, pattern in groups.items() if re.search(pattern, text)]
            return matches[0] if len(matches) == 1 else None

        question = self.question()
        options = question.get('options', [])
        # An ID in the reply takes priority only if exactly one allowed ID appears.
        ids = [oid for oid in options if re.search(r'\b' + re.escape(oid.lower()) + r'\b', text)]
        if len(ids) == 1:
            return ids[0]
        if len(ids) > 1:
            return None

        candidates = [self.scene.get(oid) for oid in options if self.scene.get(oid)]
        if not candidates:
            return None
        color_names = [c.replace('grey', 'gray') for c in COLORS if re.search(r'\b' + re.escape(c) + r'\b', text)]
        colors = set(color_names)
        if colors:
            if len(colors) != 1:
                return None
            candidates = [o for o in candidates if o.color in colors]
            if not candidates:
                return None

        # Match category mentions when the user says 'the bottle', 'the tray', etc.
        mentioned_labels = set()
        for label in {o.label for o in candidates}:
            names = ALIASES.get(label, (label, label + 's'))
            if any(re.search(r'\b' + re.escape(alias) + r'\b', text) for alias in names):
                mentioned_labels.add(label)
        if len(mentioned_labels) == 1:
            candidates = [o for o in candidates if o.label in mentioned_labels]
        elif len(mentioned_labels) > 1:
            return None

        if re.search(r'\b(with|wearing|has)\s+(?:the\s+)?(?:glasses|specs|spectacles)\b', text):
            candidates = [o for o in candidates if o.attrs.get('glasses') == 'yes']
        if re.search(r'\b(left|leftmost)\b', text) and not re.search(r'\b(right|rightmost)\b', text):
            if len(candidates) > 1:
                extreme = min(o.center()[0] for o in candidates)
                candidates = [o for o in candidates if o.center()[0] == extreme]
        elif re.search(r'\b(right|rightmost)\b', text) and not re.search(r'\b(left|leftmost)\b', text):
            if len(candidates) > 1:
                extreme = max(o.center()[0] for o in candidates)
                candidates = [o for o in candidates if o.center()[0] == extreme]
        # Avoid accepting empty/generic affirmations as an object selection.
        meaningful = bool(colors or mentioned_labels or ids or re.search(r'\b(left|right|glasses|specs|spectacles)\b', text))
        return candidates[0].id if meaningful and len(candidates) == 1 else None

    def respond_text(self, text: str) -> bool:
        """Apply a clarification written in everyday language, if unambiguous."""
        kind = self.question()['type']
        if kind not in ('action', 'target', 'target_missing', 'destination'):
            return False
        choice = self._interpret_text(kind, text)
        if choice is None:
            return False
        self.respond(kind, choice, spoken_text=text)
        return True

    def plan(self, human_in_zone: bool = False, path_obstructed: bool = False):
        if self.intent is None or self.question()['type'] != 'ready':
            return None
        return build_plan(self.scene, self.intent.action, self.target_id, self.destination_id, human_in_zone, path_obstructed)

    def trace(self):
        return {'instruction': self.intent.to_dict() if self.intent else None,
                'grounding': resolve(self.intent, self.scene).to_dict() if self.intent else None,
                'selected_target': self.target_id or None,
                'selected_destination': self.destination_id or None,
                'next_question': self.question(),
                'events': self.events,
                'confirmed_for_simulation': self.confirmed}
