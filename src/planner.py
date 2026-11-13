"""Symbolic, simulation-only robot plans. This is NOT a physical safety controller."""
from .schema import Plan, Scene

SUPPORTED={'move','pick','inspect'}

def build_plan(scene:Scene, action:str, target_id:str, destination_id:str='', human_in_zone:bool=False, path_obstructed:bool=False)->Plan:
    target=scene.get(target_id)
    dest=scene.get(destination_id) if destination_id else None
    warnings=['RGB-image positions are not calibrated robot coordinates.',
              'A passing check authorizes a visualization only, never physical robot motion.']
    if action not in SUPPORTED: return Plan(False,'Unknown or unsupported action; request clarification.',warnings=warnings)
    if not target: return Plan(False,'Target ID is not present in current scene.',warnings=warnings)
    if action in ('pick','move') and target.label in ('person','table','tray','chair'):
        return Plan(False,'Target is not permitted for simulated grasping.',warnings=warnings)
    if action=='move' and not dest: return Plan(False,'Destination must be a visible, uniquely identified object.',warnings=warnings)
    if action=='move' and dest.id==target.id: return Plan(False,'Source and destination cannot be the same object.',warnings=warnings)
    if human_in_zone or path_obstructed:
        return Plan(False,'Blocked by explicit safety flag: human in motion zone or path obstructed.',warnings=warnings)
    steps=[{'skill':'verify_visible','object_id':target.id,'status':'planned'}]
    if action=='inspect': steps += [{'skill':'inspect','object_id':target.id,'status':'planned'}]
    elif action=='pick': steps += [{'skill':'approach','object_id':target.id,'status':'planned'}, {'skill':'grasp','object_id':target.id,'status':'planned'}, {'skill':'hold','object_id':target.id,'status':'planned'}]
    elif action=='move': steps += [
      {'skill':'approach','object_id':target.id,'status':'planned'},
      {'skill':'grasp','object_id':target.id,'status':'planned'},
      {'skill':'transport','object_id':target.id,'destination_id':dest.id,'status':'planned'},
      {'skill':'release','object_id':target.id,'destination_id':dest.id,'status':'planned'},
      {'skill':'verify_result','object_id':target.id,'status':'planned'}]
    return Plan(True,'Checks passed for simulation only; requires explicit operator confirmation.',action,target_id,destination_id,steps,warnings)
