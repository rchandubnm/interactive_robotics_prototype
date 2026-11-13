"""Offline NLP baseline; optional VLM parser is supplied in vlm.py.

Never treat this shallow parser as equivalent to a general language model.
It is intentionally conservative: unknowns trigger clarification.
"""
import re
from .schema import Intent, Scene

ALIASES = {
    'person': ('people','person','man','woman','human'),
    'bottle': ('bottle','bottles'), 'cup':('cup','cups','mug','mugs'),
    'tray':('tray','trays'), 'table':('table','tables','desk'),
    'box':('box','boxes','carton'), 'book':('book','books'),
    'cell phone':('phone','mobile','cellphone'), 'chair':('chair','chairs'),
    'backpack':('backpack','bag'), 'laptop':('laptop','computer'),
    'apple':('apple','apples'), 'banana':('banana','bananas'),
}
COLORS=('red','blue','green','yellow','orange','black','white','purple','brown','pink','gray','grey')

def _name_matches(scene:Scene, text:str):
    matched=[]
    for obj_label in scene.labels():
        aliases=ALIASES.get(obj_label,(obj_label,obj_label+'s'))
        for alias in aliases:
            for m in re.finditer(r'\b'+re.escape(alias)+r'\b',text):
                matched.append((m.start(),m.end(),obj_label))
    return sorted(set(matched))

def parse_instruction(instruction:str,scene:Scene) -> Intent:
    s=instruction.lower().strip()
    intent=Intent(instruction=instruction)
    if re.search(r'\b(move|put|place|transfer|bring|shift|carry)\b',s): intent.action='move'
    elif re.search(r'\b(pick|grab|grasp|lift|take)\b',s): intent.action='pick'
    elif re.search(r'\b(inspect|look|describe|scan|examine|check|identify|find|locate)\b',s): intent.action='inspect'
    mentions=_name_matches(scene,s)
    if mentions:
        # First mentioned entity is a target in the supported command grammar.
        first=mentions[0]
        intent.target_label=first[2]
        # If only known entity is after a destination preposition, do not
        # mistake it for the target (e.g., 'move elephant to the tray').
        if intent.action=='move' and re.search(r'\b(?:to|onto|into)\s+(?:the |a )?$',s[:first[0]]):
            intent.target_label='unknown'
        before=s[max(0,first[0]-38):first[0]]
        m=list(re.finditer(r'\b('+'|'.join(COLORS)+r')\b',before))
        if m: intent.target_color=m[-1].group(1).replace('grey','gray')
        if re.search(r'\b(leftmost|left-hand|left side|on the left|left)\b',before[-25:]): intent.position='left'
        if re.search(r'\b(rightmost|right-hand|right side|on the right|right)\b',before[-25:]): intent.position='right'
        suffix=s[first[1]:]
        if re.search(r'^\s*(?:on |at )?(?:the )?left\b|\b(on the left|to the left)\b',suffix): intent.position='left'
        if re.search(r'^\s*(?:on |at )?(?:the )?right\b|\b(on the right|to the right)\b',suffix): intent.position='right'
    # The mention of glasses is used as a relational *attribute* only when the
    # instruction also refers to a person.
    has_eyewear=bool(re.search(r'\b(glasses|spectacles|eyeglasses|specs)\b',s))
    if has_eyewear and re.search(r'\b(person|man|woman|people|human)\b',s):
        intent.reference_label='person'
        intent.reference_glasses='yes'
    # Following a preposition, distinguish an anchor from destination.
    for m in re.finditer(r'\b(?:person|man|woman|human)\b.{0,38}?\b(?:in|wearing)\s+(?:a )?(red|blue|green|yellow|black|white|purple|brown|pink|gray)\s+(?:shirt|t-shirt|top)\b',s):
        intent.reference_label='person'; intent.reference_shirt_color=m.group(1)
    near=re.search(r'\b(near|next to|beside|closest to|by)\s+(?:the |a )?(?:person|man|woman|people|human)\b',s)
    if near:
        intent.relation='closest' if 'closest' in near.group(1) else 'near';intent.reference_label='person'
    elif re.search(r'\b(left of|to the left of)\s+(?:the |a )?person\b',s):
        intent.relation='left_of';intent.reference_label='person'
    elif re.search(r'\b(right of|to the right of)\s+(?:the |a )?person\b',s):
        intent.relation='right_of';intent.reference_label='person'
    elif intent.target_label=='person' and has_eyewear:
        intent.reference_label='person';intent.reference_glasses='yes';intent.relation='same'
    # Detect explicit multi-object commands; do not silently act on only one.
    explicit_targets=[(m.start(),m.group(1)) for m in re.finditer(r'\b(red|blue|green|yellow)\s+(?:bottle|cup|box)\b',s)]
    if len(set(x[1] for x in explicit_targets))>1 and re.search(r'\band\b',s):
        intent.multi_target=True
    # Destination after 'to/onto/into/on' and a known object label. Exclude
    # 'to the left of' and other spatial anchor expressions.
    if intent.action=='move':
        for m in re.finditer(r'\b(?:to|onto|into|on)\s+(?:the |a )?',s):
            tail=s[m.end():]
            if re.match(r'(?:left|right|person|man|woman|people)\b',tail): continue
            for obj_label in scene.labels():
                aliases=ALIASES.get(obj_label,(obj_label,))
                if any(re.match(re.escape(alias)+r'\b',tail) for alias in aliases):
                    intent.destination_label=obj_label
    return intent
