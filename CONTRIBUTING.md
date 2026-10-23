# Contributing

Fork this repository, create a focused branch, and open a pull request. Describe
the user-visible change, why it helps, and the checks you actually ran.

Keep the app local, native, button-driven, and usable without accounts or paid
services. Runtime network requests do not belong in normal editing workflows.
Preserve original media and keep one processing operation active at a time.
Use argument arrays for subprocesses; do not build shell commands from filenames.

Follow the setup and test commands in README.md. Include a small regression case
when changing media processing or installer behavior. Use generated media; do not
commit personal footage, voice recordings, model weights, credentials, logs, or
installed runtimes. Hardware/model tests should be explicitly opt-in in CI.

To update dependencies, download compatible Windows x64 CPython 3.13 wheels in a
clean environment, resolve all transitive dependencies, regenerate the lock with
SHA-256 hashes, then test a fresh ZIP installation and offline operation. Do not
hand-wave a version bump as verified. Third-party notices must stay accurate.

Be constructive and specific in issues and reviews. Reports should state Windows
version, selected operation, and the relevant error; remove private paths and
media content before posting logs.
