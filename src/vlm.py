"""Optional local Qwen2.5-VL through Ollama HTTP API. Explicit uncertainty handling.

Structured outputs are model *claims*, not validated observations. Never let
model-generated text execute arbitrary code, or drive a physical robot.
"""
from __future__ import annotations
import base64,io,json,re
from PIL import Image
import requests
from .schema import Intent,Scene

DEFAULT_URL='http://127.0.0.1:11434'
DEFAULT_MODEL='qwen2.5vl:3b'

def available_models(base_url=DEFAULT_URL):
    try:
        r=requests.get(base_url.rstrip('/')+'/api/tags',timeout=2);r.raise_for_status()
        return [x.get('name','') for x in r.json().get('models',[])]
    except (requests.RequestException,ValueError):return []

def _picture(img:Image.Image,max_size=1024):
    img=img.convert('RGB').copy()
    img.thumbnail((max_size,max_size))
    b=io.BytesIO();img.save(b,format='JPEG',quality=88)
    return base64.b64encode(b.getvalue()).decode('ascii')

class VLMResponseError(ValueError):
    """Ollama completed a request but did not return a usable JSON result."""


def _extract_json_object(content: str) -> dict:
    """Accept strict JSON or a single JSON object inside a Markdown code fence."""
    cleaned = content.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned, flags=re.I).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        # Some local models wrap their JSON in a short introductory sentence.
        start = cleaned.find('{')
        if start < 0:
            raise VLMResponseError('The vision model returned text instead of JSON.') from None
        try:
            value, _ = json.JSONDecoder().raw_decode(cleaned[start:])
        except json.JSONDecodeError as exc:
            raise VLMResponseError('The vision model returned incomplete or invalid JSON. ' +
                                   f'Parser detail: {exc.msg}.') from exc
    if not isinstance(value, dict):
        raise VLMResponseError('The vision model returned JSON, but it was not a JSON object.')
    return value


def _chat(messages, model=DEFAULT_MODEL, base_url=DEFAULT_URL, timeout=150):
    """Get structured VLM content, with one fallback if JSON mode produces no answer.

    `requests.Response.json()` decodes the Ollama HTTP envelope, whereas
    `message.content` must be decoded separately as model-generated JSON.
    Those are two independent failure points, both checked explicitly here.
    """
    api = base_url.rstrip('/') + '/api/chat'
    last_error = None
    for attempt in range(2):
        body = {
            'model': model,
            'messages': messages,
            'stream': False,
            'options': {'temperature': 0, 'num_ctx': 4096, 'num_predict': 1000},
        }
        # On first attempt, request strict JSON. Some local VLM combinations
        # produce an empty answer with JSON mode, so retry once without it.
        if attempt == 0:
            body['format'] = 'json'
        try:
            response = requests.post(api, json=body, timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise VLMResponseError(
                'Could not complete the Ollama request. Confirm Ollama is running '
                f'at {base_url}, and that model {model} is installed. Detail: {exc}'
            ) from exc
        try:
            envelope = response.json()
        except ValueError as exc:
            status = getattr(response, 'status_code', 'unknown')
            ctype = getattr(response, 'headers', {}).get('content-type', 'unknown')
            raise VLMResponseError(
                f'Ollama returned a non-JSON HTTP response (status {status}, '
                f'content-type {ctype}). Check the Ollama API URL: {base_url}.'
            ) from exc
        if not isinstance(envelope, dict):
            raise VLMResponseError('Ollama returned an unexpected API response structure.')
        if envelope.get('error'):
            raise VLMResponseError(f'Ollama reported an error: {str(envelope["error"])[:250]}')
        message = envelope.get('message') or {}
        if not isinstance(message, dict):
            raise VLMResponseError('Ollama API response did not include a valid message.')
        content = message.get('content') or ''
        if not isinstance(content, str):
            raise VLMResponseError('Ollama message content had an unexpected type.')
        if not content.strip():
            reason = envelope.get('done_reason') or 'unspecified'
            last_error = (f'The vision model returned an empty answer (done_reason={reason}). '
                          'Try a smaller image, ensure enough available memory, or restart Ollama.')
            continue
        try:
            return _extract_json_object(content)
        except VLMResponseError as exc:
            last_error = str(exc)
            continue
    raise VLMResponseError(
        (last_error or 'The vision model did not produce a valid JSON result.') +
        ' The app has not used this model output for object selection.'
    )


def describe_scene(image:Image.Image,scene:Scene,model=DEFAULT_MODEL,base_url=DEFAULT_URL):
    """Single VLM pass describes only existing detector objects via visual ID prompts.

    No model-supplied boxes or novel IDs are accepted. Descriptions are
    tentative and never replace detections; confirmation is still required.
    """
    from copy import deepcopy
    from .vision import overlay
    out=deepcopy(scene)
    annotated=overlay(image,scene)
    ids=[o.id for o in scene.objects][:18]
    prompt=("Describe this workspace image. Each detected region has a visible boxed ID. "
      "Look at the objects and provide concise factual visual descriptions. "
      "Return a JSON object with keys scene_summary (string) and objects (array of "
      "{id, description, color, glasses, shirt_color, hat, watch, face_mask, backpack}). "
      "Only use these IDs: "+json.dumps(ids)+". "
      "Choose 'unknown' when a detail such as glasses, eyewear, masks, watches, "
      "or small text cannot be verified. Do not invent people or objects. "
      "Do not infer personal identity or sensitive characteristics.")
    data=_chat([{'role':'user','content':prompt,'images':[_picture(annotated,1240)]}],model,base_url)
    for element in data.get('objects',[]):
        if not isinstance(element,dict): continue
        obj=out.get(str(element.get('id','')))
        if obj is None:continue
        description=str(element.get('description','')).strip()
        if description:obj.description=description[:240]
        for extra in ('glasses','hat','watch','face_mask','backpack'):
            v=str(element.get(extra,'unknown')).lower().strip()
            if v in ('yes','no','unknown') and obj.label=='person':obj.attrs[extra]=v
        shirt=str(element.get('shirt_color','unknown')).lower().strip()
        if obj.label=='person' and shirt in ('red','blue','green','yellow','orange','white','black','purple','gray','brown','pink','unknown'):
            obj.attrs['shirt_color']=shirt
        color=str(element.get('color','unknown')).lower().strip()
        if obj.color=='unknown' and color in ('red','blue','green','yellow','orange','white','black','purple','gray','brown','pink'):
            obj.color=color
        obj.evidence+=' + tentative VLM description'
    return out,{'status':'response received','scene_summary':str(data.get('scene_summary',''))[:700], 'described_count':sum(bool(o.description) for o in out.objects),'raw':data}

def analyze_attributes(image:Image.Image,scene:Scene,model=DEFAULT_MODEL,base_url=DEFAULT_URL,max_people=5):
    """Per-object person crops help with small eyewear; uncertain = unknown.

    Returns a copied Scene and the VLM logs. Only existing detector IDs may
    be updated. Other objects remain as detected.
    """
    from copy import deepcopy
    out=deepcopy(scene);logs=[]
    people=[o for o in out.objects if o.label=='person'][:max_people]
    for obj in people:
        x1,y1,x2,y2=obj.bbox
        pad=max(12,int((x2-x1)*.15))
        crop=image.crop((max(0,x1-pad),max(0,y1-pad),min(image.width,x2+pad),min(image.height,y2+pad)))
        prompt=(f'Examine cropped image of detected person {obj.id}. Describe only directly visible attributes. '
          'Look carefully at their face. A thin dark frame may be hard to see; if unclear choose "unknown". '
          'Do not infer identity, age, sex, religion or emotions. '
          'Answer JSON with keys "glasses" (yes/no/unknown), "shirt_color" (short color/unknown), '
          '"hat" (yes/no/unknown), "face_mask" (yes/no/unknown), "watch" (yes/no/unknown), "backpack" (yes/no/unknown), "description" (one concise factual sentence), "reason" (short observable evidence). '
          'Never invent eyewear when the image is blurry or face is hidden.')
        try:
            data=_chat([{'role':'user','content':prompt,'images':[_picture(crop,896)]}],model,base_url)
            gl=str(data.get('glasses','unknown')).lower().strip()
            if gl not in ('yes','no','unknown'):gl='unknown'
            shirt=str(data.get('shirt_color','unknown')).lower()[:25]
            if shirt not in ('red','blue','green','yellow','orange','white','black','purple','gray','brown','pink','unknown'):shirt='unknown'
            obj.attrs['glasses']=gl;obj.attrs['shirt_color']=shirt
            for extra in ('hat','face_mask','watch','backpack'):
                v=str(data.get(extra,'unknown')).lower().strip()
                obj.attrs[extra]=v if v in ('yes','no','unknown') else 'unknown'
            obj.description=str(data.get('description',''))[:240]
            obj.evidence='VLM inference (unverified)'
            logs.append({'object_id':obj.id,'model_attributes':data,'status':'response received'})
        except (ValueError,KeyError,requests.RequestException) as exc:
            logs.append({'object_id':obj.id,'error':str(exc)[:300],'status':'failed; attributes remain unknown'})
    return out,logs

def parse_with_llm(instruction:str,scene:Scene,model=DEFAULT_MODEL,base_url=DEFAULT_URL)->Intent:
    """Parse only; caller must independently ground all fields in the actual scene."""
    from .language import parse_instruction
    fallback=parse_instruction(instruction,scene)
    system=('You parse natural-language robot instructions into JSON; you do NOT execute tasks. '
      'Output exactly keys action, target_label, target_color, position, relation, reference_label, '
      'reference_glasses, reference_shirt_color, destination_label. Only choose labels from supplied visible labels. '
      'If ambiguous/uncertain set field to "unknown". '
      'action one of move,pick,inspect,unknown. position left,right,unknown. '
      'relation near,left_of,right_of,same,unknown. reference_glasses yes,no,unknown. '
      'Do not invent target objects or destinations. Do not use arbitrary computer commands.')
    user='Visible object label vocabulary: '+json.dumps(scene.labels())+'\nInstruction: '+instruction
    try:
        data=_chat([{'role':'system','content':system},{'role':'user','content':user}],model,base_url,timeout=90)
        allowed_labels=set(scene.labels())|{'unknown'}
        for key in ('target_label','reference_label','destination_label'):
            value=str(data.get(key,'unknown')).strip().lower()
            setattr(fallback,key,value if value in allowed_labels else 'unknown')
        for key,allowed in {
            'action':('move','pick','inspect','unknown'),
            'position':('left','right','unknown'),
            'relation':('near','left_of','right_of','same','unknown'),
            'reference_glasses':('yes','no','unknown'),
            'target_color':('red','blue','green','yellow','orange','black','white','purple','brown','pink','gray','unknown')
        }.items():
            val=str(data.get(key,'unknown')).strip().lower()
            setattr(fallback,key,val if val in allowed else 'unknown')
        c=str(data.get('reference_shirt_color','unknown')).lower().strip()
        if c in ('red','blue','green','yellow','orange','white','black','purple','gray','brown','pink','unknown'):fallback.reference_shirt_color=c
        fallback.parser='Ollama JSON (must be grounded)'
    except (ValueError,KeyError,requests.RequestException):
        fallback.parser='rules (VLM parser unavailable)'
    return fallback
