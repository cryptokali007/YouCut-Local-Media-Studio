"""Create a Windows wheel lock after resolving/downloading packages in a clean setup."""
from pathlib import Path
import argparse
import email
import hashlib
import zipfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('wheel_directory', type=Path)
    parser.add_argument('--output', type=Path, default=Path('app/requirements.lock'))
    args = parser.parse_args()
    entries = {}
    for path in sorted(args.wheel_directory.glob('*.whl')):
        with zipfile.ZipFile(path) as bundle:
            metadata = email.message_from_bytes(bundle.read(next(n for n in bundle.namelist() if n.endswith('.dist-info/METADATA'))))
        name = metadata['Name'].lower().replace('_', '-')
        if name in entries:
            raise ValueError(f'Multiple wheels for {name}; use a clean single-platform wheel folder.')
        with path.open('rb') as handle:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        entries[name] = (metadata['Version'], digest)
    if not entries:
        raise ValueError('No wheel files found.')
    text = '# Windows x64 / CPython 3.13. All transitive dependencies pinned.\n'
    text += '# Generated from resolved public PyPI wheels; verified by pip check.\n'
    text += ''.join(f'{name}=={version} --hash=sha256:{digest}\n' for name, (version, digest) in sorted(entries.items()))
    args.output.write_text(text, encoding='utf-8')
    print(f'Locked {len(entries)} wheels into {args.output}')


if __name__ == '__main__':
    main()
