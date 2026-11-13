# Live Vision Robot Assistant — Version 6

A **live-camera and text-first interactive robot research demo**. Its interface
combines webcam streaming, automatically refreshed scene captions, typed visual
questions, clarification dialogue, step-by-step assembly, human approval and a
2D symbolic output animation. This is a research prototype, **not a physical robot**.

## 1. Install and run on Windows 11

Reuse the existing working Python 3.11 environment and CUDA-enabled PyTorch:

```powershell
cd I:\Projects\interactive_robotics_live_v6
& "I:\Projects\vision_language_robotics_prototype\.venv\Scripts\Activate.ps1"
python -m pip install -r requirements.txt
python -m pytest -q
python -m streamlit run app.py
```

Open http://localhost:8501 in a desktop browser. `run_windows.ps1` also works,
with the existing venv path as default. CUDA PyTorch is not reinstalled.

## 2. For actual vision-language Q&A

Install Ollama from https://ollama.com/download, then run:

```powershell
ollama pull qwen2.5vl:3b
ollama list
```

In the app expand **Vision model** and enable **Answer visual questions with
VLM**. For the RTX 3060 6 GB, a quantized 3B model is an initial choice; VRAM
and response latency vary. The model must have completed downloading and Ollama
must be running. The app makes HTTP requests to your local Ollama API.

## 3. Live video + chat

1. Select **Live camera**, click **START**, and permit webcam access.
2. Automatically scanned frames display an annotated image and text such as:
   `Robot: I can detect 2 people, 1 bottle, 1 cup.`
3. Type `What can you see?` or `Is the person wearing glasses?` into chat.
   If Ollama is enabled, the local VLM answers using the latest analyzed frame.
   If it is unavailable, the application only reports known detector categories.
4. Click **Examine people, clothing and accessories** (with the VLM ready) to
   enrich per-person attributes for more detailed grounding.
5. Type a task such as `Move the blue bottle to the tray` or `Assemble the cup`.
6. Respond to clarifications (`blue one`, `left`, `white lid`) and answer
   **yes** before every assembly step. The GIF updates after approved steps.
7. Use **New conversation** to reset task state.

Object IDs and frames are **frozen while a task is waiting for clarification
or approval**; to work with a changed scene, restart the task and rescan.
For objects not recognized by standard YOLO (e.g., some lids or straws), use
**Correct missed objects** to label their regions. These corrections are
operator input, not AI detections.

## 4. Quick guided example (no model required)

Choose **Cup assembly demo**, then type:

```text
Human: Assemble the cup.
Robot: I can assemble a cup in 3 steps. Step 1: Which cup should I use?
Human: The blue cup.
Robot: Step 1: Position the blue cup. Shall I proceed?
Human: yes
Robot: Step 1 simulated. Step 2: Which lid?
Human: White lid.
Robot: Shall I proceed?
Human: yes
Robot: Step 2 simulated. Step 3: Which straw?
Human: Green straw.
Robot: Shall I proceed?
Human: yes
Robot: Assembly complete in simulation.
```

An actual deterministic transcript and animation are included under
`examples/outputs/live_v6_transcript.txt` and
`examples/outputs/live_v6_cup_assembly.gif`.

## 5. Core source files

| File | Responsibility |
|---|---|
| `app.py` | Single-screen Streamlit GUI and WebRTC live camera |
| `src/live_camera.py` | Thread-safe latest video-frame buffer |
| `src/live_chat.py` | Scene captions and grounded Ollama VLM Q&A |
| `src/live_controller.py` | Text chat, task routing, approval/clarification |
| `src/vision.py` | YOLO detection, boxes and color heuristic |
| `src/vlm.py` | Object/person attribute analysis (optional) |
| `src/assembly.py` | Assembly dialogue, part selection, per-step approval |
| `src/dialogue.py` | General pick/move/inspect clarification |
| `src/assembly_sim.py`, `src/simulation.py` | Symbolic 2D action outputs |
| `tests/` | Deterministic unit tests |

## Ollama JSON errors and model troubleshooting (v6.1 fix)

If you see `Expecting value: line 1 column 1 (char 0)` or a blank scene description,
check whether Ollama is running and the correct vision model is installed:

```powershell
ollama --version
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/version
```

If `qwen2.5vl:3b` is missing, run `ollama pull qwen2.5vl:3b`.
The app expects the base URL `http://127.0.0.1:11434` (not `/api/chat`).

This patch distinguishes malformed **HTTP JSON** from malformed **model JSON**,
retries one malformed/blank structured model answer without JSON mode, and shows
an actionable error if Ollama still fails. It does not invent a scene description.
Large images and the 6 GB GPU can slow or fail inference; reduce image size if
needed. A full local Ollama inference cannot be verified by automated tests
without your local model; run the app's model check on your Windows PC.

## Research and technical limitations

- WebRTC is a live camera feed; detections and VLM descriptions are sampled,
  not real-time continuous semantic tracking.
- Ollama 3B VLM is slower than YOLO and can be uncertain or mistaken about
  glasses, clothing and small details. Detection captions do not imply eyewear
  recognition. No physical motion is inferred from the RGB image.
- Standard COCO YOLO may not recognize lid/straw categories. You can add
  annotated regions or later fine-tune an open-vocabulary detector.
- No calibrated 3D pose, collision checking, gripper force, or actual robot
  actuation is implemented. Safety toggles are **manual simulated blocks**.
- Live WebRTC generally works on `localhost`. Remote browser deployments
  require HTTPS and appropriate ICE/TURN networking.
- This source does not upload anything to GitHub. Before pushing, review
  `.gitignore` and avoid uploading raw personal camera recordings.

Model comparisons and source-paper synthesis are in `docs/PAPER_SYNTHESIS.md`.

## Publish to GitHub and capture environment

See [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md). Run `scripts/export_environment.ps1` from PowerShell to export an exact `requirements-lock.txt` snapshot of the Python environment on your own PC. Never commit the actual `.venv` folder, model weights, or private recordings.
