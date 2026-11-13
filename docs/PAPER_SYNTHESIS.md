# Ten-paper synthesis and implementation traceability

**Research topic:** Interactive Vision–Language Task Planning for Ambiguity Resolution in Shared Human–Robot Workspaces. This synthesis examines **ten distinct articles** supplied as 20 PDF uploads (each article had one duplicate). The ten articles range from robotics NLP, multimodal perception, symbolic and task-and-motion planning, long-horizon demonstration interpretation, to a neighboring autonomous-driving foundation-model survey. Their contributions inform *different layers* of the project; they do **not** collectively establish that the supplied implementation can control a physical robot.

## Per-paper methods, evidence and adaptation

### 1. A Distributed Conversational Framework for Human–Robot Collaborative Manipulation Using Local LLMs and VLMs (RO-MAN 2026)
DOI: `10.1109/RO-MAN72286.2026.11714760`.

The authors separate natural-language understanding, visual grounding, ROS 2 coordination and manipulation execution into modular agents/nodes. Free-form commands become structured pick/place/handover requests; vision-space proposals become robot-frame goals only after depth and camera calibration. A web dashboard shows interpretable intermediate outputs and **explicitly requires operator confirmation before motion**. Their Franka FR3 experiments compare model combinations on dice tasks with increasing ambiguity; the paper also notes that conditional/compositional commands can break extraction.

**Adapted here:** structured `Intent` → `Resolution` → `Plan`, visible object ID overlays, an audit trail and a confirmation gate. **Not reproduced:** ROS 2, depth/robot coordinate transforms, FR3 motion, handovers and original benchmark.

### 2. A Survey for Foundation Models in Autonomous Driving (ICCVDM 2025)
DOI: `10.1109/ICCVDM66874.2025.11290083`.

This survey categorizes LLMs, vision foundation models and multimodal foundation models by their roles in autonomous-driving perception, reasoning, planning and scene synthesis. It surveys adaptation via prompting, fine-tuning and other techniques, while identifying hallucinations, latency, dataset/domain shift and safety as serious problems in foundation-model deployment.

**Adapted here:** separate low-level detection from open-language reasoning, maintain abstention (`unknown`) and trace model evidence. **Boundary:** conclusions about autonomous-driving benchmarks do not directly validate tabletop manipulation.

### 3. Design and System Implementation of an Active Perception Architecture for Maritime Targets Based on the Cognitive Mechanism of Large Models (IEEE Sensors Journal 2026)
DOI: `10.1109/JSEN.2026.3680718`.

The paper builds a hierarchical system combining YOLO11 perception, information filtering and LLM–VLM collaborative reasoning with a downstream control layer. Rather than repeatedly passing unfiltered observations to a large model, it compacts features and selects information for higher-level reasoning and control. Its maritime-UAV experiments report improvements in latency and task performance; intermittent VLM sampling may cause lag for rapidly moving targets.

**Adapted here:** YOLO11 detections and compact object-level records are supplied to the language parser, while cropped people can be sent to the VLM for expensive attribute checks. **Not reproduced:** UAV control, active viewpoint changes, data filtering benchmarks or their reported performance.

### 4. From Perception to Symbolic Task Planning: Vision-Language Guided Human–Robot Collaborative Structured Assembly (IEEE T-ASE 2026)
DOI: `10.1109/TASE.2026.3739177`.

The work connects Perception-to-Symbolic State (PSS), aligning RGB-D evidence with structural/design constraints, to Human-Aware Planning and Replanning (HPR). It verifies symbolic assembly states, updates task assignments only after state deviation and uses minimal-change replanning to preserve stability when humans intervene. It evaluates state synthesis and human-aware task progression on a structured timber-frame assembly task.

**Adapted here:** a typed `Scene` of explicit visible objects, validated symbolic action steps and a trace that separates perception from action. **Not reproduced:** design-file grounding, RGB-D assembly verification, the multi-robot task allocator or minimal-change replanning.

### 5. GameVLM: A Decision-making Framework for Robotic Task Planning Based on Visual Language Models and Zero-sum Games (ICMA 2024)
DOI: `10.1109/ICMA61710.2024.10633088`.

GameVLM recognizes that a single VLM-generated plan can be inconsistent or hallucinated. It uses decision agents and expert agents to construct and check plans, and a zero-sum-game-inspired decision framework to resolve disagreements. The paper reports physical robot experiments and discusses the complexity of multiple agents.

**Adapted here:** we do not trust open-ended generative plans; deterministic validation checks supported skills and visible targets before execution. **Not reproduced:** multiple model agents, zero-sum optimization or the original hardware experiments. An explicit adversarial plan critic remains future work.

### 6. Generating Robot Action Sequences: An Efficient Vision–Language Models with Visual Prompts (IWIS 2024)
DOI: `10.1109/IWIS62722.2024.10706068`.

The method provides VLMs with visual prompts (labelled objects/bounding boxes) so they can resolve spatial references and produce action sequences. It uses action outcome observations to judge success or failure and can regenerate steps following disturbances or unexpected results. Examples include placing a colored cube in a selected drawer.

**Adapted here:** annotated object IDs passed in a scene-image prompt, candidate grounding and a replayed verify step. **Not reproduced:** real action outcome observation/recovery, drawer-state estimation and task-specific end-effector controllers.

### 7. Open-World Task and Motion Planning via Vision–Language Model Generated Constraints (IEEE RA-L 2026)
DOI: `10.1109/LRA.2026.3656799`.

OWL-TAMP uses VLMs for semantic discrete and continuous constraints, while a task-and-motion planner handles geometric feasibility, grasps, placements and collision avoidance. The separation is important because VLMs are not reliable numerical motion planners: they can express *what* should be achieved but need explicit motion search to determine *how*.

**Adapted here:** NLP supplies high-level goals and a non-generative planner emits predeclared skills; the model does not generate executable Python or motion commands. **Not reproduced:** constraint synthesis, a real TAMP solver, 3D geometry and collision-free trajectories.

### 8. Towards Object-Level Multimodal Task Planning for Long-Term Robotic Manipulation with Vision Language Model and Behavior Tree (ICASSP 2026)
DOI: `10.1109/ICASSP55912.2026.11461939`.

The framework combines object-level multimodal scene representations and language-conditioned prototype plans with a compilation stage producing Behavior Trees (BTs). It grounds tasks into controller/status pairs and checks conditions involving force and geometry. It evaluates long-horizon tabletop manipulation using an embodied robotic platform.

**Adapted here:** explicit object IDs and sequential, typed action primitives. **Not reproduced:** BT runtime, force and geometric constraints, feedback-control conditions or the real-world benchmark.

### 9. VLM See, Robot Do: Human Demo Video to Robot Action Plan via Vision Language Model (IROS 2025)
DOI: `10.1109/IROS60139.2025.11246682`.

The SeeDo pipeline detects temporal keyframes using hand-motion speed valleys, uses object tracking and visual prompts to resolve entities, then employs a VLM interpreter to turn demonstrations into step-by-step plans for simulated and real robots. The hand-guided temporal selection and tracking are critical for long videos.

**Adapted here:** video-file sampling as a first step toward temporally grounded interaction. **Not reproduced:** hand-motion-based keyframe selection, object identity tracking through time, learning from videos or SeeDo benchmark evaluation. Our frame sampler is uniform and manual; it should not be described as SeeDo.

### 10. VLM-Driven Task Planning for Industrial Robot Workcells with Multiple Identical Targets (ICCCR 2026)
DOI: `10.1109/ICCCR69988.2026.11642753`.

The framework addresses multiple identical or similar targets through a four-stage process: intent analysis, object detection, task planning and operation sequencing. A reusable skill library supports primitive operations such as grasp, place and scan, along with compositional meta-skills; the paper reports a task success rate for its specific industrial experiments.

**Adapted here:** explicitly detect multiple grounded candidate IDs and ask the operator, then issue typed steps (`approach`, `grasp`, `transport`, `release`). **Not reproduced:** long-term skill/meta-skill learning, industrial operation optimization or original accuracy claims.

## Synthesis into the proposed architecture

```text
RGB image/camera/sample video frame
           |
           v
YOLO11 object detection -> typed scene (IDs, colors, bounding boxes)
           |                                  |
           |                      cropped/person / full-scene VLM
           |                          -> attributes + unknown
           v                                  |
          instruction -> NLP (local model or conservative fallback)
                                   |
                                   v
                   scene-grounded candidate resolution
                                   |
                  ambiguous / unknown / missing parameter?
                       | yes                     | no
                       v                         v
             human clarification        unique target & goal
                       \_______________________/
                                   |
                                   v
                      structured symbolic planner
                                   |
                   explicit operator approval + blocking flags
                                   |
                                   v
                  symbolic execution, GIF, PNG, JSON trace
```

### Directly implemented versus suggested by sources

| Design element | Status in v3 | Evidence/limits |
|---|---|---|
| YOLO image detection with object IDs | Implemented for real still images | Detector weights download needed on user's PC |
| People wearing spectacles / clothing attribute | Implemented as *optional VLM inference* on crops | Not verified by our local offline tests; can output unknown |
| Open-ended NLP | Implemented optionally with Ollama JSON | Rule parser remains available but limited |
| Color/spatial reference grounding | Implemented; 2D only | Not calibrated metric geometry |
| Multi-turn clarification and candidate selection | Implemented, tested on synthetic scene | Real scene errors depend on object detection accuracy |
| Human confirmation and audit trail | Implemented, synthetic tests passed | Safety flags are manual |
| Deterministic symbolic plan and GIF | Implemented and exercised | No physical robot or PyBullet manipulator |
| Replanning on unexpected action failure | Not yet | Requires state tracking and executed outcome observation |
| Behavior-tree compilation | Not yet | Typed steps are **not** a BT runtime |
| Motion feasibility / collision-free planning | Not yet | Requires 3D calibration and a motion planner |
| Long-horizon temporal tracking | Not yet | Video is sampled, not object-tracked |

## Proposed publishable experiments (not yet performed)

1. **Dataset:** collect 100+ indoor tabletop RGB images and optionally short videos with a ground-truth roster of objects, eyewear/accessories, spatial relations, targets, valid destinations, and human reference ambiguities. Include scenes with unobservable attributes and high object similarity.
2. **Baselines:** YOLO + deterministic rules; YOLO + VLM language parser without clarification; full YOLO + VLM + ambiguity clarification. Ensure equal perception budgets or report differences.
3. **Metrics:** target-object grounding top-1 accuracy, ambiguity precision/recall/F1, abstention accuracy on unclear eyewear, clarification turns, successful task-plan rate, end-to-end latency, and fraction of unsafe plans blocked by independent oracle flags.
4. **Ablations:** remove crop-based VLM attributes, operator clarification, spatial grounding, and the deterministic plan checker separately.
5. **Safety boundary:** no claims about physical collision avoidance can be made from a single RGB image. The current flags are input assumptions and should never be used to certify operation.

**Positioning:** This project combines ideas already demonstrated individually by these papers. A claim of scientific novelty requires a broader literature review and new experimental evidence; the current synthetic tests establish software consistency, not robot or VLM benchmark accuracy.
