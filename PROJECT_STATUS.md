# YouCutOwn Studio project status

Updated 2026-10-23 (America/Los_Angeles).

- Public project: YouCutOwn Studio; dedicated original repository
  https://github.com/cryptokali007/youcutown-studio (publication in progress).
- Canonical development source: this repository, app/app.py.
- Run: windows.bat; first run invokes automatic setup, later runs open the native app.
- Manual setup: Install.bat -NoPause. Offline repair: Repair.bat -Offline -NoPause.
- Architecture: Python 3.13 private runtime, PySide6 native UI, FFmpeg subprocesses,
  local faster-whisper and Kokoro ONNX. One operation at a time; originals preserved.
- Installation: pinned public downloads, 51 resolved package wheels with SHA-256
  lock entries; Python/FFmpeg/model hashes in scripts/setup/assets.json.
- Runtime, models, cache, settings, outputs and logs are excluded from Git.
- Existing personal Media Workbench installation is separate from this public project.
- Current validation: see docs/VALIDATION.md; clean install and release checks ongoing.
- Deployment state: source release preparation; no hosted application or cloud backend.
- Next action: finish clean setup verification, review Jules contribution, publish
  source and release ZIP, and verify download/install from the published repository.
