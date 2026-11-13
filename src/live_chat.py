"""Safe scene text and optional live-frame Q&A through a local Ollama VLM.

No image is sent to a cloud service. A failed VLM request raises an explicit
error rather than fabricating results. Image answers never authorize actions.
"""
from __future__ import annotations

from collections import Counter
import re

from PIL import Image
import requests

from .schema import Scene
from .vlm import DEFAULT_MODEL, DEFAULT_URL, _picture


def scene_summary(scene: Scene) -> str:
    """A factual, detection-only sentence; it cannot verify clothing/accessories."""
    if not scene.objects:
        return 'I have a frame, but I have not detected any recognized objects. Try better lighting or ask the vision model for a description.'
    counts = Counter(o.label for o in scene.objects)
    terms = [f'{n} {label}{"s" if n != 1 else ""}' for label, n in sorted(counts.items())]
    return 'I can detect ' + ', '.join(terms) + '. You can ask me about them or give an instruction.'


def is_visual_question(text: str) -> bool:
    s = text.lower().strip()
    # Queries about current scene are not robot motion instructions.
    patterns = (
        r'\b(what|which|who|where|how many|describe|tell me|can you see|do you see|is there|are there|look at|identify|explain)\b',
        r'\b(wearing|glasses|spectacles|specs|shirt|color of|colour of|visible|scene|camera|frame)\b',
    )
    return bool(re.search(patterns[0], s) or (s.endswith('?') and re.search(patterns[1], s)))


def is_task_command(text: str) -> bool:
    return bool(re.search(r'\b(move|pick up|pick|place|put|bring|transfer|lift|grab|assemble|assembly|build|inspect|examine|check|attach|insert)\b', text, re.I))


def vision_answer(image: Image.Image, prompt: str, scene: Scene,
                  model: str = DEFAULT_MODEL, base_url: str = DEFAULT_URL,
                  history: list[dict] | None = None, timeout: int = 100) -> str:
    """Grounded VLM answer from the current frame. Returns plain text, not actions.

    History is text-only and bounded. Camera frame is encoded once; callers
    must use an intentional, recent frame. The model may still be mistaken.
    """
    if not prompt.strip():
        return 'Please enter a question.'
    recent = [m for m in (history or []) if m.get('role') in ('user', 'assistant')]
    recent = [{'role':m['role'], 'content':str(m.get('content',''))[:500]} for m in recent[-6:]]
    system = (
        'You are a cautious vision-enabled tabletop robot assistant. Answer the user in friendly '
        'plain text using the supplied camera image. Do not invent objects or human attributes. '
        'If glasses or clothes cannot be verified, say you are unsure. Use object IDs from the '
        'detection summary only when you can visually associate them. '
        'For requests involving physical actions, explain that only supervised symbolic simulation '
        'is available; never claim you moved physical objects. Answer in 1-5 short sentences. '
        'Never claim successful execution without deterministic confirmation. '
        'Scene detections are fallible, so correct them if image evidence disagrees.'
    )
    labels = scene_summary(scene)
    content = f'Scene detection summary (may contain errors): {labels}\nUser question: {prompt}'
    messages = [{'role':'system','content':system}, *recent,
                {'role':'user','content':content,'images':[_picture(image, max_size=960)]}]
    result = requests.post(base_url.rstrip('/') + '/api/chat', json={
        'model':model, 'messages':messages, 'stream':False,
        'options':{'temperature':0.15, 'num_ctx':3072, 'num_predict':320}},
        timeout=timeout)
    try:
        result.raise_for_status()
    except requests.RequestException as exc:
        raise ValueError('Ollama vision question failed. Ensure the server is running and the model is installed: '+str(exc)) from exc
    try:
        payload=result.json()
    except ValueError as exc:
        raise ValueError('Ollama returned a non-JSON API response. Verify the Ollama API URL (usually http://127.0.0.1:11434).') from exc
    if not isinstance(payload,dict) or not isinstance(payload.get('message'),dict):
        raise ValueError('Ollama returned an unexpected API response without a message.')
    response=payload['message'].get('content') or ''
    if not isinstance(response,str) or not response.strip():
        raise ValueError('The vision model returned an empty answer. Try reducing image size or restarting Ollama.')
    return response.strip()[:2500]
