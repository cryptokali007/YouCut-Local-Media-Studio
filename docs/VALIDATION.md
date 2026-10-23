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

Fresh source-ZIP, independent Windows CI, and offline repair checks are recorded
here as those release checks complete. A prepared download cache was used for
part of local package installation; it is not committed or included in source ZIPs.

The source repository includes real output tests for image formats, video/audio
operations, transitions, high-speed exports, cancellation, Unicode paths and source
preservation. Speech and NVIDIA checks are separate from core Windows CI because
they need model downloads or compatible hardware.
