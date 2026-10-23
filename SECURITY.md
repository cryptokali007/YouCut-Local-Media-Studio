# Security

Report security issues privately through GitHub's **Security → Report a
vulnerability** feature when enabled. Do not post private media, tokens, or
personal logs in a public issue. For an ordinary bug, use the issue tracker with
synthetic reproduction files.

Setup intentionally downloads packages, executables, and model assets from the
pinned public sources. The application does not need network access during use.
The source ZIP is not signed; inspect scripts before running software from a fork.

Treat untrusted media as untrusted input. Keep Windows and this project's pinned
decoder/runtime dependencies updated through reviewed releases. The app invokes
FFmpeg as a subprocess and does not sandbox codec parsers.
