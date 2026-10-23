# Validation

This file records checks actually completed for the public package. Earlier private
workbench tests are useful history, but are not treated as proof of public setup.

Public package validation completed locally on Windows x64 on 2026-10-23:

- Automatic Install.bat bootstrapped the pinned private Python runtime, installed
  51 hash-locked package wheels, verified/extracted FFmpeg, downloaded/verified
  both Whisper models and public Kokoro model/voice files, and passed pip check.
- All installed distributions and interpreter search paths were inside app/;
  global/user Python packages were excluded. A regression test checks this boundary.
- Six setup tests passed: valid offline cache, damaged-cache rejection, atomic
  verified download, bad-download recovery, manifest integrity, and runtime isolation.
- Nine image checks passed, including exact lossless PNG/WebP RGBA pixels, hidden
  transparent colors, odd dimensions, JPEG fidelity/chroma, Fit/Fill and source hashes.
- Twenty-one real media checks passed. A 256-second clip exported to 4/2/1 seconds
  at 64/128/256x; mixed-clip transitions, audio operations, captions, slideshows and
  a real NVIDIA H.264 encode were verified. Video outputs were fully decoded.
- Actual Kokoro narration and Whisper transcription completed with outbound Python
  socket connections blocked. Word-level transcription was burned into video.
- Cancellation, partial cleanup, invalid settings, Unicode paths, source preservation
  and edited subtitle timing passed the recovery checks.
- Three native converter-button exports passed (JPEG, lossless WebP, PNG), including
  remembered format selection. The BAT smoke launch and readable UI capture passed.

- A fresh source-only ZIP was extracted to a path containing spaces with no Git
  metadata, runtime, models, or download cache. Install.bat -CoreOnly -NoPause
  fetched the public assets and all wheels, bootstrapped its private runtime, and
  passed imports, dependency checks, FFmpeg execution, all six setup tests, all
  nine image tests, and windows.bat --smoke.
- Repair.bat -Offline -NoPause completed against the full installation using its
  verified cache. Models and generated outputs remained available afterward.
- Independent GitHub Windows runners installed from an extracted source ZIP and
  passed setup integrity, image/media/recovery, native button exports, and BAT
  launch checks. See the [source-ZIP CI run](https://github.com/cryptokali007/YouCut-Local-Media-Studio/actions/runs/40017165328)
  and the [current workflow](https://github.com/cryptokali007/YouCut-Local-Media-Studio/actions/workflows/windows.yml).
- A separate Luna agent used only the README, in-app guide, screenshots, and
  ordinary Qt mouse/keyboard/drop events. It successfully found and exported
  high-quality JPEG, lossless WebP, and a 2x video edit, then inspected the files.
  The guide opened and was readable. This was an app-owned QA controller test,
  not OS-wide mouse automation. An inactive-window focus issue in that controller
  was corrected; it was not a failure of normal narration text entry. The agent
  then replaced the narration text through the visible field and generated a
  valid 24 kHz mono, 16-bit Kokoro WAV. The app displayed Saved at 100%.

A prepared download cache was used for part of the first full local installation;
the separate fresh-ZIP and hosted CI installations fetched their own assets.
No prepared cache is committed or included in source ZIPs.

The source repository includes real output tests for image formats, video/audio
operations, transitions, high-speed exports, cancellation, Unicode paths and source
preservation. Speech and NVIDIA checks are separate from core Windows CI because
they need model downloads or compatible hardware.
