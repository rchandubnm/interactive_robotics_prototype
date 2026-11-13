"""Live Vision + Interactive Robot Assistant.

Launch: python -m streamlit run app.py
Uses WebRTC browser camera + local Ollama for visual Q&A (when enabled).
All motion is symbolic 2D simulation with human confirmation.
"""
from __future__ import annotations

import io
import json
import time

from PIL import Image
import streamlit as st

from src.live_camera import LatestFrame
from src.live_chat import vision_answer, scene_summary
from src.live_controller import LiveController
from src.vision import detect_image, overlay
from src.demo import demo_scene, demo_image
from src.assembly_demo import assembly_scene, assembly_image
from src.schema import SceneObject
from src.vlm import DEFAULT_MODEL, DEFAULT_URL, available_models, describe_scene, analyze_attributes

st.set_page_config(page_title='Live Vision Robot Assistant',page_icon='🤖',layout='wide')
st.markdown('''<style>
.block-container {max-width:1370px;padding-top:1.4rem;}
[data-testid="stChatMessage"] {border:1px solid rgba(130,145,165,.18);border-radius:14px;}
[data-testid="stImage"] img {border-radius:10px;}
</style>''',unsafe_allow_html=True)


@st.cache_data(ttl=15,show_spinner=False)
def models_at(url: str) -> list[str]:
    return available_models(url)


if 'live_ctrl' not in st.session_state:
    st.session_state.live_ctrl = LiveController()
if 'live_buffer' not in st.session_state:
    st.session_state.live_buffer = LatestFrame()
if 'auto_scan_at' not in st.session_state:
    st.session_state.auto_scan_at = 0.0
if 'auto_vlm_at' not in st.session_state:
    st.session_state.auto_vlm_at = 0.0
if 'source_id' not in st.session_state:
    st.session_state.source_id = ''
ctrl: LiveController = st.session_state.live_ctrl

st.title('🤖 Live Vision Robot Assistant')
st.caption('I describe what I see, answer your messages, ask for clarification, and execute approved steps in a tabletop simulation.')

with st.sidebar:
    st.subheader('Workspace')
    mode = st.radio('Choose input',['Live camera','Cup assembly demo','Object demo','Upload image'],index=1)
    with st.expander('Vision model',expanded=False):
        url=st.text_input('Ollama API',DEFAULT_URL)
        model=st.text_input('Local vision model',DEFAULT_MODEL)
        models=models_at(url)
        model_ready=model in models or f'{model}:latest' in models
        if model_ready:
            st.success('Local vision model available')
        else:
            st.caption('For detailed image answers, install Ollama and run:')
            st.code('ollama pull qwen2.5vl:3b',language='powershell')
        use_vlm=st.checkbox('Answer visual questions with VLM',value=model_ready,disabled=not model_ready)
        live_vlm=st.checkbox('Automatically describe live frames (about every 30 s)',value=False,
                            disabled=not(model_ready and mode=='Live camera'))
        conf=st.slider('YOLO confidence',.1,.8,.25,.05)
    with st.expander('Simulated safety',expanded=False):
        person_close=st.checkbox('Human too close to simulated path',value=False)
        blocked=st.checkbox('Simulated path is blocked',value=False)
    if st.button('↻ New conversation',use_container_width=True):
        st.session_state.live_ctrl=LiveController()
        st.session_state.source_id=''
        st.rerun()
    st.caption('Local-first · No physical robot control')

# The source switch resets a stale dialogue. The live frame buffer remains session scoped.
if st.session_state.source_id!=mode:
    st.session_state.live_ctrl=LiveController()
    ctrl=st.session_state.live_ctrl
    st.session_state.source_id=mode
    st.session_state.auto_scan_at=0
    st.session_state.auto_vlm_at=0
    st.session_state.upload_hash=None

left,right=st.columns([1.1,1],gap='large')


def answer_local(image,question,scene,history):
    return vision_answer(image,question,scene,model,url,history)


with left:
    st.subheader('What I see')
    if mode=='Live camera':
        st.caption('Click START, grant camera permission. Live feed stays on while you type in chat.')
        try:
            from streamlit_webrtc import webrtc_streamer, WebRtcMode
            ctx=webrtc_streamer(
                key='robot-live-camera',mode=WebRtcMode.SENDRECV,
                media_stream_constraints={'video':True,'audio':False},
                video_frame_callback=st.session_state.live_buffer.on_frame,
                async_processing=True,
                rtc_configuration={'iceServers':[{'urls':['stun:stun.l.google.com:19302']}]} ,
            )
        except ImportError:
            ctx=None
            st.error('Live camera dependency missing. Run: python -m pip install streamlit-webrtc')
        st.caption('Automatically scans object categories every few seconds. Object IDs are frozen during an active task.')

        @st.fragment(run_every=4)
        def scan_live():
            snapshot=st.session_state.live_buffer.snapshot()
            if snapshot is None:
                st.info('Waiting for camera frames. Click START above, or choose a demo.')
                return
            seq, frame=snapshot
            now=time.monotonic()
            if ctrl.idle() and now-st.session_state.auto_scan_at>=4:
                try:
                    with st.spinner('Scanning live view…'):
                        scene=detect_image(frame,confidence=conf)
                    ctrl.set_scene(scene,frame,'live camera')
                    st.session_state.auto_scan_at=now
                except Exception as exc:
                    st.warning(f'Frame detection failed: {exc}')
            if ctrl.image is not None and ctrl.scene is not None:
                st.image(overlay(ctrl.image,ctrl.scene),caption='Latest analyzed frame (not the live video feed)',use_container_width=True)
            st.write('**Robot:** '+ctrl.caption)
            if live_vlm and model_ready and ctrl.idle() and now-st.session_state.auto_vlm_at>30 and ctrl.scene:
                try:
                    details=vision_answer(frame,'Describe what you can see in this frame, including clearly visible clothing and accessories.',ctrl.scene,model,url,timeout=75)
                    st.session_state.auto_vlm_at=time.monotonic()
                    st.session_state.latest_live_detail=details
                    ctrl._append('assistant','Live visual description: '+details)
                except Exception as exc:
                    st.session_state.latest_live_detail=f'Local model could not analyze the frame ({type(exc).__name__}).'
                    st.session_state.auto_vlm_at=time.monotonic()
            if live_vlm and st.session_state.get('latest_live_detail'):
                st.write('**Detailed visual description:** '+st.session_state.latest_live_detail)
            if not ctrl.idle():
                st.caption('Current task uses a frozen frame. Restart the task to scan a new scene.')
        scan_live()
        if st.button('Analyze latest frame now',use_container_width=True):
            frame_info=st.session_state.live_buffer.snapshot()
            if frame_info is None:
                st.warning('No live camera frame received yet.')
            elif not ctrl.idle():
                st.info('Finish or reset the current task before replacing its reference frame.')
            else:
                with st.spinner('Analyzing…'):
                    ctrl.set_scene(detect_image(frame_info[1],confidence=conf),frame_info[1],'camera')
                st.rerun()
    elif mode=='Cup assembly demo':
        if ctrl.scene is None:
            ctrl.set_scene(assembly_scene(),assembly_image(),'pre-labelled demo')
        st.image(overlay(ctrl.image,ctrl.scene),use_container_width=True)
        st.write('**Robot:** '+ctrl.caption)
        st.caption('Guided scene — components and colors are pre-labelled, not detected by AI.')
    elif mode=='Object demo':
        if ctrl.scene is None:
            ctrl.set_scene(demo_scene(),demo_image(),'pre-labelled demo')
        st.image(overlay(ctrl.image,ctrl.scene),use_container_width=True)
        st.write('**Robot:** '+ctrl.caption)
        st.caption('Guided scene — predefined labels demonstrate object ambiguity.')
    else:
        upload=st.file_uploader('Upload a workspace photo',type=['png','jpg','jpeg'])
        camera_snap=st.camera_input('Or take one photo')
        selected=camera_snap or upload
        if selected is not None:
            data=selected.getvalue()
            import hashlib
            digest=hashlib.sha256(data).hexdigest()
            if st.session_state.get('upload_hash')!=digest:
                try:
                    img=Image.open(io.BytesIO(data)).convert('RGB')
                    ctrl._new()
                    ctrl.set_scene(detect_image(img,confidence=conf),img,'uploaded photo')
                    st.session_state.upload_hash=digest
                except Exception as exc:
                    st.error(f'Cannot load image: {exc}')
            if ctrl.scene:
                st.image(overlay(ctrl.image,ctrl.scene),use_container_width=True)
                st.write('**Robot:** '+ctrl.caption)
        else:
            st.info('Upload or capture a photo to begin.')
    if ctrl.scene and mode in ('Live camera','Upload image'):
        if model_ready and ctrl.idle():
            if st.button('✨ Examine people, clothing and accessories',use_container_width=True):
                with st.spinner('Asking the local vision model to inspect visible regions…'):
                    try:
                        enriched, report = describe_scene(ctrl.image,ctrl.scene,model,url)
                        enriched, logs = analyze_attributes(ctrl.image,enriched,model,url)
                        ctrl.scene = enriched
                        ctrl.caption = scene_summary(enriched)
                        ctrl._append('assistant',str(report.get('scene_summary') or ctrl.caption))
                        st.rerun()
                    except Exception as exc:
                        st.error('Could not analyze this scene with Ollama: '+str(exc))
                        st.info('Try checking Ollama in another PowerShell window with: ollama list')
        with st.expander('Correct missed objects (optional)'):
            st.caption('Use this if an object such as a lid or straw was not detected. Added annotations are operator-provided, not AI predictions.')
            with st.form('label_parts'):
                name=st.selectbox('Part',['cup','lid','straw','tray','bottle','person','table'])
                color=st.selectbox('Color',['unknown','red','blue','green','yellow','white','black','orange'])
                cols=st.columns(2)
                with cols[0]:
                    x1=st.number_input('Left',min_value=0,max_value=max(0,ctrl.scene.width-1),value=0)
                    y1=st.number_input('Top',min_value=0,max_value=max(0,ctrl.scene.height-1),value=0)
                with cols[1]:
                    x2=st.number_input('Right',min_value=1,max_value=ctrl.scene.width,value=max(1,ctrl.scene.width//2))
                    y2=st.number_input('Bottom',min_value=1,max_value=ctrl.scene.height,value=max(1,ctrl.scene.height//2))
                add=st.form_submit_button('Add part')
            if add:
                if x2<=x1 or y2<=y1:
                    st.error('Please enter a valid region.')
                else:
                    num=1
                    while ctrl.scene.get(f'M{num}'):
                        num+=1
                    ctrl.scene.objects.append(SceneObject(f'M{num}',name,(int(x1),int(y1),int(x2),int(y2)),color,1.0,{},'', 'manual operator label'))
                    ctrl.caption=scene_summary(ctrl.scene)
                    st.rerun()
        with st.expander('Object list'):
            st.dataframe([{'ID':o.id,'Label':o.label,'Color':o.color,'Source':o.evidence} for o in ctrl.scene.objects],hide_index=True,use_container_width=True)

with right:
    st.subheader('Talk to the robot')
    if not ctrl.messages:
        st.markdown('Try **“What can you see?”**, **“Is someone wearing glasses?”**, or **“Assemble the cup.”**')
        if mode=='Cup assembly demo':
            if st.button('Try: Assemble the cup',use_container_width=True):
                ctrl.act('Assemble the cup')
                st.rerun()
        elif mode=='Object demo':
            if st.button('Try: Move the bottle near the person wearing glasses to the tray',use_container_width=True):
                ctrl.act('Move the bottle near the person wearing glasses to the tray')
                st.rerun()
    for msg in ctrl.messages[-60:]:
        with st.chat_message(msg['role'],avatar='🤖' if msg['role']=='assistant' else '👤'):
            st.markdown(msg['content'])

    state=ctrl.status()
    q=state.get('question')
    if state['flow']=='assembly':
        with st.container(border=True):
            st.markdown('**Assembly plan**')
            for i,label in enumerate(('Position the cup','Attach the lid','Insert the straw')):
                glyph='✅' if i<state['step'] else ('🔵' if i==state['step'] else '◯')
                st.markdown(f'{glyph} **Step {i+1}:** {label}')
            st.progress(min(3,state['step'])/3)
    if q and q['type'] in ('choose_part','target','target_missing','destination'):
        st.caption('Choose an object, or reply by typing its color, position, or ID.')
        opts=q.get('options',[])
        cols=st.columns(2)
        for i,oid in enumerate(opts):
            obj=ctrl.scene.get(oid) if ctrl.scene else None
            if obj:
                with cols[i%2]:
                    if st.button(obj.description_short(),key=f'choose-{state["flow"]}-{oid}-{state.get("step",0)}',use_container_width=True):
                        ctrl.select(oid)
                        st.rerun()
    elif q and q['type']=='action':
        for action in ('move','pick','inspect'):
            if st.button(action.title(),key='action-'+action):
                ctrl.act(action)
                st.rerun()
    elif q and (q['type']=='approve' or (q['type']=='ready' and ctrl.result is None)):
        if q['type']=='ready' and ctrl.task:
            tentative=ctrl.task.plan(person_close,blocked)
            if tentative:
                with st.container(border=True):
                    st.markdown('**Proposed action steps**')
                    for i,step in enumerate(tentative.steps,1):
                        label=str(step["skill"]).replace("_"," ").capitalize()
                        st.markdown(f"**Step {i}:** {label}")
                    if not tentative.accepted:
                        st.warning('Simulation blocked: '+tentative.reason)
        c1,c2=st.columns(2)
        with c1:
            if st.button('▶ Yes, proceed',type='primary',use_container_width=True):
                ctrl.act('yes',human_nearby=person_close,blocked=blocked)
                st.rerun()
        with c2:
            if st.button('■ Stop',use_container_width=True):
                ctrl.act('stop',human_nearby=person_close,blocked=blocked)
                st.rerun()
    elif q and q['type']=='missing':
        st.warning('A required part is missing from the current scene. Show or label it, then start a new task.')

    prompt=st.chat_input('Ask a question, give a task, or reply yes/no…')
    if prompt:
        with st.spinner('Thinking…'):
            ctrl.act(prompt, vision_fn=answer_local if use_vlm else None,
                     human_nearby=person_close,blocked=blocked)
        st.rerun()
    if ctrl.result:
        st.markdown('### Simulation output')
        st.caption('Approved steps only · symbolic 2D visualization, not physical robot motion')
        if 'png' in ctrl.result:
            st.image(ctrl.result['png'],use_container_width=True)
        if 'gif' in ctrl.result:
            with st.expander('Watch animation and download result'):
                st.image(ctrl.result['gif'],use_container_width=True)
                st.download_button('Download animation (GIF)',ctrl.result['gif'],file_name='robot_steps.gif',mime='image/gif')
        st.download_button('Download conversation (JSON)',json.dumps(ctrl.messages,indent=2),file_name='conversation.json',mime='application/json')

st.caption('Computer-vision results may be uncertain. The live camera provides periodic analyzed frames; VLM questions use the last analyzed frame. Every simulated action still needs human approval.')
