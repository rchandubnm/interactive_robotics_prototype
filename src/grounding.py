"""Conservative visual grounding. No silent guesses about attributes."""
from math import hypot
from .schema import Scene, Intent, Resolution

def _anchors(intent:Intent,scene:Scene) -> tuple[list, bool]:
    if intent.reference_label=='unknown': return [],False
    anchors=[o for o in scene.objects if o.label==intent.reference_label]
    if intent.reference_shirt_color!='unknown':
        known=[o for o in anchors if o.attrs.get('shirt_color','unknown')==intent.reference_shirt_color]
        unknown=[o for o in anchors if o.attrs.get('shirt_color','unknown')=='unknown']
        if unknown:return known+unknown,True
        anchors=known
    if intent.reference_glasses!='unknown':
        known=[o for o in anchors if o.attrs.get('glasses','unknown')==intent.reference_glasses]
        unknown=[o for o in anchors if o.attrs.get('glasses','unknown')=='unknown']
        if unknown: return known+unknown,True
        return known,False
    return anchors,False

def resolve(intent:Intent,scene:Scene) -> Resolution:
    if intent.target_label=='unknown':
        return Resolution([],True,'No grounded target type was understood. Please name an object visible in the scene.')
    candidates=[o for o in scene.objects if o.label==intent.target_label]
    if intent.multi_target:
        return Resolution([o.id for o in candidates],True,'Multiple targets were requested. This demo executes one object at a time; please select the first object.')
    if intent.target_color!='unknown':
        unknown_color=any(o.color=='unknown' for o in candidates)
        candidates=[o for o in candidates if o.color==intent.target_color or o.color=='unknown']
        if unknown_color and candidates: return Resolution([o.id for o in candidates],True,'At least one object color is unverified; please confirm the target visually.')
    if intent.target_label=='person' and intent.reference_glasses!='unknown' and intent.relation=='same':
        known=[o for o in candidates if o.attrs.get('glasses')==intent.reference_glasses]
        unknown=[o for o in candidates if o.attrs.get('glasses','unknown')=='unknown']
        if unknown: return Resolution([o.id for o in known+unknown],True,'Eyewear is not visually verified for every candidate; please confirm the person.')
        candidates=known
    elif intent.relation!='unknown' and intent.reference_label!='unknown':
        anchors, uncertain = _anchors(intent,scene)
        if not anchors: return Resolution([o.id for o in candidates],True,'Referenced person could not be grounded; please identify the target.')
        if uncertain or len(anchors)>1:
            return Resolution([o.id for o in candidates],True,'Reference person is ambiguous or eyewear is unverified; clarify the target.')
        ax,ay=anchors[0].center()
        if intent.relation=='closest' and candidates:
            md=min(hypot(o.center()[0]-ax,o.center()[1]-ay) for o in candidates)
            candidates=[o for o in candidates if abs(hypot(o.center()[0]-ax,o.center()[1]-ay)-md)<1]
        elif intent.relation=='near':
            # Coarse 2D image-space distance; not metric 3D proximity.
            radius=0.33*max(scene.width,scene.height)
            candidates=[o for o in candidates if hypot(o.center()[0]-ax,o.center()[1]-ay)<=radius]
        elif intent.relation=='left_of': candidates=[o for o in candidates if o.center()[0]<ax]
        elif intent.relation=='right_of': candidates=[o for o in candidates if o.center()[0]>ax]
    if intent.position in ('left','right') and candidates:
        # On its own, "left bottle" / "right bottle" are interpreted as
        # the extreme objects of the grounded candidate set.
        candidates=[(min if intent.position=='left' else max)(candidates,key=lambda o:o.center()[0])]
    return Resolution([o.id for o in candidates],False,('No matching visible object.' if not candidates else 'Grounded using visible labels and attributes.'))

def destination_candidates(intent:Intent,scene:Scene):
    return [o.id for o in scene.objects if o.label==intent.destination_label] if intent.destination_label!='unknown' else []
