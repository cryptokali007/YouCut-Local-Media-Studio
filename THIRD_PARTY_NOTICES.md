# Third-party components

YouCutOwn Studio source is licensed GPL-3.0-or-later. No model weights, installed
Python packages, or FFmpeg executables are committed to this repository. Setup
downloads them into the user's extracted project folder; their own licenses apply.

| Component | Source and licensing |
| --- | --- |
| CPython 3.13 | [python.org](https://www.python.org/), Python Software Foundation license; runtime includes LICENSE.txt |
| PySide6 / Qt for Python | [Qt licensing](https://doc.qt.io/qtforpython-6/licenses.html), LGPLv3/GPLv3/commercial options; bundled package notices retained |
| FFmpeg 8 full Windows build | [GyanD 8.0 release](https://github.com/GyanD/codexffmpeg/releases/tag/8.0), GPLv3-or-later build; license copied to app/licenses/FFmpeg-LICENSE |
| FFmpeg upstream | [FFmpeg source n8.0](https://github.com/FFmpeg/FFmpeg/tree/n8.0), [legal information](https://ffmpeg.org/legal.html); configured optional libraries carry their own notices |
| faster-whisper / CTranslate2 | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper), [OpenNMT/CTranslate2](https://github.com/OpenNMT/CTranslate2), MIT |
| Whisper weights | [Systran base.en](https://huggingface.co/Systran/faster-whisper-base.en), [small](https://huggingface.co/Systran/faster-whisper-small), MIT; source model [OpenAI Whisper](https://github.com/openai/whisper) |
| Kokoro ONNX runner | [thewh1teagle/kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), MIT |
| Kokoro model and voice assets | [Kokoro-82M model card](https://huggingface.co/hexgrad/Kokoro-82M), Apache-2.0 model; [ONNX release assets](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0); retain upstream model/voice provenance |
| phonemizer / eSpeak NG loader | [phonemizer](https://github.com/bootphon/phonemizer), GPLv3; [espeakng-loader](https://pypi.org/project/espeakng-loader/), GPLv3; [eSpeak NG](https://github.com/espeak-ng/espeak-ng), GPLv3-or-later |
| Pillow | [Pillow](https://pillow.readthedocs.io/), HPND/Pillow license |
| Other Python dependencies | Exact versions/hashes in app/requirements.lock; license files and metadata remain in installed distributions |

The installation pattern was inspired by Tech Jarves's MIT-licensed Portable Local
Studio. Its Node/React application and backend installers are not bundled here.
Our Python/FFmpeg implementation and setup scripts are maintained in this project.

If redistributing a prepared offline bundle, you are also redistributing these
components. Include their notices and fulfill the applicable source and license
obligations for the exact binaries you distribute; source ZIP publication alone
does not satisfy a separate binary distributor's obligations.

Project screenshots and test media are generated locally from synthetic patterns,
sine waves, simple original graphics, and an original test sentence. User footage
is excluded. Company and product names identify compatibility or dependencies.
