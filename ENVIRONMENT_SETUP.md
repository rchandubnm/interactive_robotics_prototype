# Environment Setup

Python: 3.11
GPU: NVIDIA RTX 3060
PyTorch CUDA wheel: cu128

Install CUDA-enabled PyTorch:

python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

Install remaining project dependencies:

python -m pip install -r requirements.txt

Run application:

python -m streamlit run app.py
