# YouCutOwn Studio project status

Updated 2026-10-23 (America/Los_Angeles).

- Public project: YouCutOwn Studio; dedicated original repository
  https://github.com/cryptokali007/YouCut-Local-Media-Studio.
- Repository name is exactly YouCut-Local-Media-Studio; repository links and Git
  remote were updated in place. Existing app code, installation and v1.0.0 release
  are preserved.
- Canonical development source: this repository root; entry point app/app.py.
- Version: 1.0.0; source ZIP and SHA-256 checksum distributed through GitHub Releases.
- Run: windows.bat; first run invokes automatic setup, later runs open the native app.
- Manual setup: Install.bat -NoPause. Offline repair: Repair.bat -Offline -NoPause.
- Architecture: Python 3.13 private runtime, PySide6 native UI, FFmpeg subprocesses,
  local faster-whisper and Kokoro ONNX. One operation at a time; originals preserved.
- Installation: pinned public downloads, 51 resolved package wheels with SHA-256
  lock entries; Python/FFmpeg/model hashes in scripts/setup/assets.json.
- Runtime, models, cache, settings, outputs and logs are excluded from Git.
- Existing personal Media Workbench installation is separate from this public project.
- Validation: full local setup, 6 setup tests, 9 image checks, 21 media checks,
  recovery checks, native exports, actual offline Kokoro/Whisper inference and
  T1000 encoding passed. Fresh source-ZIP install/launch and offline repair passed.
  Independent Windows source-ZIP CI passed. See docs/VALIDATION.md for evidence.
- Blind usability: a Luna agent used the guide and visible controls to export
  JPEG, lossless WebP, a 2x video edit, and Kokoro narration. QA focus was corrected.
- Jules contribution: reviewed source-ZIP CI change merged through PR #1.
- Deployment state: public Windows x64 source distribution; native local app.
  First setup uses public downloads; normal editing and speech work offline.
- Next action: collect user feedback and review changes against the existing
  installer, offline, media-preservation and output checks before future releases.
