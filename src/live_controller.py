"""Testable text-first orchestration for visual Q&A and confirmed robot tasks."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable
from PIL import Image

from .assembly import AssemblyDialogue, is_assembly_request, STEP_NAMES
from .dialogue import Dialogue
from .schema import Scene
from .simulation import simulate
from .assembly_sim import simulate_assembly
from .live_chat import scene_summary, is_visual_question, is_task_command

YES = re.compile(r'^\s*(yes|y|yeah|okay|ok|sure|go ahead|proceed|approve|do it|continue)(?:[,! ]+(?:please|go ahead|proceed|continue|do it))*[.! ]*$', re.I)
NO = re.compile(r'^\s*(no|stop|cancel|abort|quit)([.! ]*)$', re.I)


@dataclass
class LiveController:
    scene: Scene | None = None
    image: Image.Image | None = None
    messages: list[dict] = field(default_factory=list)
    assembly: AssemblyDialogue | None = None
    task: Dialogue | None = None
    result: dict | None = None
    caption: str = 'Start the camera or choose a demo to begin.'
    _seen: int = 0
    _selected_scene_name: str = ''

    def idle(self) -> bool:
        if self.assembly:
            return self.assembly.question()['type'] in ('complete', 'cancelled')
        if self.task:
            return self.result is not None
        return True

    def set_scene(self, scene: Scene, image: Image.Image, name: str = 'camera') -> bool:
        """Freeze scene during a pending task to avoid silently changing IDs."""
        if not self.idle():
            return False
        self.scene, self.image = scene, image.copy()
        self.caption = scene_summary(scene)
        self._selected_scene_name = name
        return True

    def _append(self, role: str, text: str):
        self.messages.append({'role':role, 'content':text})

    def _flush(self, flow):
        new = flow.events[self._seen:]
        for e in new:
            self._append('assistant' if e['speaker'] == 'robot' else 'user', e['text'])
        self._seen = len(flow.events)

    def _new(self):
        self.assembly = None
        self.task = None
        self.result = None
        self._seen = 0

    def act(self, text: str, vision_fn: Callable | None = None,
            human_nearby: bool = False, blocked: bool = False):
        """Send text into current dialogue. Only user-confirmed steps may execute."""
        text = text.strip()
        if not text:
            return
        if text.lower() in ('new task','reset task','start over','restart task'):
            self._new(); self._append('user',text)
            self._append('assistant','Task reset. What would you like me to do?')
            return
        if not self.scene or not self.image:
            self._append('user',text)
            self._append('assistant','Please select the demo, upload a photo, or start the camera before asking.')
            return
        # A scene question is allowed during task clarification without moving anything.
        # "what next?" remains with the action state machine.
        if is_visual_question(text) and not (self.assembly and re.search(r'\b(what next|what.s next|what is next|what should|explain|how to proceed|which step|show steps)\b',text,re.I)):
            self._answer_vision(text,vision_fn)
            return
        if self.assembly and self.assembly.question()['type'] not in ('complete','cancelled'):
            self.assembly.respond_text(text,human_nearby,blocked)
            self._flush(self.assembly)
            if self.assembly.completed:
                self.result = simulate_assembly(self.scene, self.assembly.selected, self.assembly.completed)
            return
        if self.task and self.task.question()['type'] == 'ready' and self.result is None:
            self._append('user',text)
            if NO.fullmatch(text):
                self._append('assistant','Task cancelled. Nothing was simulated.')
                self._new()
                return
            if YES.fullmatch(text):
                plan=self.task.plan(human_nearby,blocked)
                if plan is None or not plan.accepted:
                    self._append('assistant','I cannot proceed: ' + (plan.reason if plan else 'No valid plan.'))
                    return
                self._append('assistant','Plan approved. Simulating the action sequence step by step.')
                self.result=simulate(self.scene,plan)
                for i,step in enumerate(plan.steps,1):
                    self._append('assistant',f'✅ Step {i}: {step["skill"].replace("_"," ").capitalize()} — simulated.')
                self._append('assistant','Simulation finished. The animation is shown below.')
                return
            self._append('assistant','Please reply **yes** to approve, **no** to cancel, or type **new task**.')
            return
        if self.task and self.task.question()['type'] in ('action','target','target_missing','destination'):
            if self.task.respond_text(text):
                self._flush(self.task)
                return
            self._append('user',text)
            self._append('assistant','I am not sure which option you mean. Specify a visible **color**, **left/right**, or **object ID**.')
            return
        # New request when idle or after previous completion.
        if is_assembly_request(text):
            self._new(); self.assembly=AssemblyDialogue(self.scene)
            self.assembly.start(text)
            self._flush(self.assembly)
            return
        if is_task_command(text):
            # Existing task parser handles move / pick / inspect. Do not invent other skill execution.
            if re.search(r'\b(attach|insert)\b',text,re.I):
                self._append('user',text)
                self._append('assistant','For supervised cup/lid/straw sequencing, say **assemble the cup**. I cannot execute an arbitrary attachment instruction.')
                return
            self._new(); self.task=Dialogue(self.scene)
            self.task.start(text)
            self._flush(self.task)
            return
        self._answer_vision(text,vision_fn)

    def _answer_vision(self,text: str,vision_fn: Callable | None):
        history=[dict(m) for m in self.messages[-8:]]
        self._append('user',text)
        if vision_fn:
            try:
                answer=vision_fn(self.image,text,self.scene,history)
            except Exception as exc:
                answer=f'I could not get an answer from the local vision model: {str(exc)[:230]}. The detector can still report recognized object categories. ' + self.caption
        else:
            answer=self.caption + ' For detailed questions about glasses, clothing, or relationships, enable the local vision model.'
        self._append('assistant',answer)

    def select(self, object_id: str):
        if self.assembly and self.assembly.question()['type']=='choose_part':
            obj=self.scene.get(object_id)
            self.assembly.choose(object_id,spoken=obj.description_short() if obj else object_id)
            self._flush(self.assembly)
        elif self.task and self.task.question()['type'] in ('target','target_missing','destination'):
            q=self.task.question()['type']; obj=self.scene.get(object_id)
            self.task.respond(q,object_id,spoken_text=obj.description_short() if obj else object_id)
            self._flush(self.task)

    def approve(self, human_nearby=False, blocked=False):
        self.act('yes',human_nearby=human_nearby,blocked=blocked)

    def status(self) -> dict:
        if self.assembly:
            return {'flow':'assembly','question':self.assembly.question(),'step':self.assembly.index,
                    'completed':len(self.assembly.completed)}
        if self.task:
            return {'flow':'task','question':self.task.question()}
        return {'flow':'chat','question':None}
