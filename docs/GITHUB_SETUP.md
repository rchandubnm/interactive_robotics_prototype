# Publish the robotics research project to GitHub

This project includes the corrected v6.1 Ollama JSON parser, the Streamlit live camera app, dialogue and assembly code, source modules, tests, and examples. It does **not** contain your Windows virtual environment or Ollama weights.

## 1. Open the project and activate Python 3.11

```powershell
cd I:\Projects\interactive_robotics_github_ready
& 'I:\Projects\vision_language_robotics_prototype\.venv\Scripts\Activate.ps1'
python --version
python -m pip check
```

Change the first path to whichever folder contains `app.py`.

## 2. Export exact Python dependencies

```powershell
.\scripts\export_environment.ps1
Get-Content .\requirements-lock.txt | Select-Object -First 20
```

Review the entire lock file **before publishing**. `pip freeze` can include local paths, other unrelated libraries, or private package indexes because the venv is shared with another project. The existing `requirements.txt` lists the main application libraries; `requirements-lock.txt` is a Windows/Python 3.11 snapshot.

The Ollama app and Qwen model are *not Python pip packages*. Install them separately:

```powershell
ollama pull qwen2.5vl:3b
```

Your CUDA-enabled torch was installed separately from the official PyTorch CUDA wheel index. If recreating on another compatible NVIDIA PC, install the matching CUDA-enabled torch build from https://pytorch.org/get-started/locally/ **before** the application requirements. A pinned lock with `+cu128` may require adding `--extra-index-url https://download.pytorch.org/whl/cu128` when installing the lock file.

## 3. Validate tests

```powershell
python -m pytest -q
```

## 4. Verify what Git will upload

```powershell
git init
git branch -M main
git add .
git status
```

Confirm **no `.venv/`, `.env`, secrets, raw video, or large `.pt` weights** appear under staged changes. If you see `requirements-lock.txt` entries containing tokens or private URLs, edit/remove them before committing.

```powershell
git commit -m "Initial interactive vision-language robotics research project"
```

If this is an existing repository with commits, use `git status` and add/commit normally; do not overwrite the history.

## 5A. New private repository with GitHub CLI

Install GitHub CLI: https://cli.github.com/ . Then:

```powershell
gh auth login
gh repo create interactive-vision-language-robotics --private --source=. --remote=origin --push
```

The GitHub CLI create command expects a local Git repository with at least one commit. It creates the remote repository and pushes existing commits.

## 5B. Already-created GitHub repository

Create a **blank** private repository on https://github.com/new (without initializing a README), copy its actual HTTPS URL, then:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

Replace the placeholder URL with your actual repo URL. If `origin` exists, use `git remote -v` and inspect it before doing anything; do not re-add it.

## Subsequent updates

```powershell
python -m pytest -q
git add .
git commit -m "Describe the change here"
git push
```

If package versions changed, rerun the export script and review the updated lock before committing.
