"""Typed representations used across perception, language, dialogue and simulation."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class SceneObject:
    id: str
    label: str
    bbox: tuple[int,int,int,int]
    color: str = 'unknown'
    confidence: float = 1.0
    attrs: dict[str,str] = field(default_factory=dict)
    description: str = ''
    evidence: str = 'detector'
    def center(self) -> tuple[float,float]:
        a,b,c,d=self.bbox
        return ((a+c)/2,(b+d)/2)
    def description_short(self) -> str:
        a = f'{self.color} ' if self.color and self.color != 'unknown' else ''
        specs = ' · glasses' if self.attrs.get('glasses') == 'yes' else ''
        return f'{self.id}: {a}{self.label}{specs}'
    def to_dict(self): return asdict(self)

@dataclass
class Scene:
    width: int
    height: int
    objects: list[SceneObject]
    source: str = 'user image'
    notes: list[str] = field(default_factory=list)
    def get(self, id: str): return next((o for o in self.objects if o.id == id), None)
    def labels(self): return sorted(set(o.label for o in self.objects))
    def to_dict(self): return {'width':self.width,'height':self.height,'source':self.source,'objects':[o.to_dict() for o in self.objects],'notes':self.notes}

@dataclass
class Intent:
    instruction: str
    action: str = 'unknown'
    target_label: str = 'unknown'
    target_color: str = 'unknown'
    position: str = 'unknown'
    relation: str = 'unknown'
    reference_label: str = 'unknown'
    reference_glasses: str = 'unknown'
    reference_shirt_color: str = 'unknown'
    multi_target: bool = False
    destination_label: str = 'unknown'
    parser: str = 'rules'
    def to_dict(self): return asdict(self)

@dataclass
class Resolution:
    candidates: list[str]
    uncertain: bool = False
    reason: str = ''
    def to_dict(self): return asdict(self)

@dataclass
class Plan:
    accepted: bool
    reason: str
    action: str = ''
    target_id: str = ''
    destination_id: str = ''
    steps: list[dict[str,Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)
