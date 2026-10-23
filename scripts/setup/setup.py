"""Network is confined to explicit setup. The application itself stays offline."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'app'
CACHE = APP / 'cache'
ASSETS = json.loads(Path(__file__).with_name('assets.json').read_text(encoding='utf-8-sig'))


def sha256(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def download(asset, destination, offline=False):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and sha256(destination) == asset['sha256']:
        print('Verified:', destination.name, flush=True)
        return destination
    if offline:
        raise RuntimeError(f'Offline setup needs a valid cached file: {destination.name}. Run Install.bat online first.')
    partial = destination.with_name(destination.name + '.partial')
    try:
        for attempt in range(1, 4):
            try:
                print(f'Downloading {destination.name} (attempt {attempt}/3)', flush=True)
                request = urllib.request.Request(asset['url'], headers={'User-Agent': 'YouCutOwn-Studio-Setup/1.0'})
                with urllib.request.urlopen(request, timeout=90) as response, partial.open('wb') as output:
                    last_report = time.monotonic()
                    total = 0
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                        total += len(chunk)
                        if time.monotonic() - last_report > 3:
                            print(f'  {total / 1024 / 1024:.1f} MiB downloaded', flush=True)
                            last_report = time.monotonic()
                if sha256(partial) != asset['sha256']:
                    raise RuntimeError(f'SHA-256 mismatch: {destination.name}')
                os.replace(partial, destination)
                return destination
            except Exception:
                partial.unlink(missing_ok=True)
                if attempt == 3:
                    raise
                time.sleep(attempt)
    finally:
        partial.unlink(missing_ok=True)


def command(args):
    print('Running:', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--core-only', action='store_true', help='Skip speech model weights; install all application packages.')
    parser.add_argument('--offline', action='store_true', help='Use only verified locally cached assets.')
    parser.add_argument('--repair', action='store_true', help='Reinstall packages without touching models or outputs.')
    args = parser.parse_args()
    for folder in ['downloads', 'wheels', 'tmp']:
        (CACHE / folder).mkdir(parents=True, exist_ok=True)
    for folder in ['bin', 'models', 'outputs', 'work', 'logs', 'licenses']:
        (APP / folder).mkdir(exist_ok=True)
    os.environ['TEMP'] = os.environ['TMP'] = str(CACHE / 'tmp')
    os.environ['PIP_DISABLE_PIP_VERSION_CHECK'] = '1'
    os.environ['PIP_NO_INPUT'] = '1'
    os.environ['PIP_CONFIG_FILE'] = os.devnull
    lock = APP / 'requirements.lock'
    print('[3/5] Verified package wheels', flush=True)
    pip = [sys.executable, '-m', 'pip']
    expected_hashes = set(re.findall(r'--hash=sha256:([0-9a-f]{64})', lock.read_text()))
    cached_hashes = {sha256(path) for path in (CACHE / 'wheels').glob('*.whl')}
    if not args.offline and not expected_hashes.issubset(cached_hashes):
        command(pip + ['--isolated', 'download', '--index-url', 'https://pypi.org/simple', '--only-binary=:all:',
                       '--require-hashes', '--dest', CACHE / 'wheels', '-r', lock])
    install = pip + ['--isolated', 'install', '--no-index', '--find-links', CACHE / 'wheels',
                     '--target', APP / 'runtime/Lib/site-packages', '--upgrade', '--ignore-installed',
                     '--require-hashes', '-r', lock]
    if args.repair:
        install.append('--force-reinstall')
    command(install)
    command(pip + ['check'])
    print('[4/5] FFmpeg / ffprobe', flush=True)
    archive = download(ASSETS['ffmpeg'], CACHE / 'downloads' / ASSETS['ffmpeg']['filename'], args.offline)
    with zipfile.ZipFile(archive) as bundle:
        for name in ['ffmpeg.exe', 'ffprobe.exe']:
            member = next(n for n in bundle.namelist() if n.endswith('/bin/' + name))
            with bundle.open(member) as source, (APP / 'bin' / name).open('wb') as output:
                shutil.copyfileobj(source, output)
        member = next(n for n in bundle.namelist() if n.endswith('/LICENSE'))
        (APP / 'licenses' / 'FFmpeg-LICENSE').write_bytes(bundle.read(member))
    print('[5/5] Offline speech assets' + (' (skipped: core-only)' if args.core_only else ''), flush=True)
    if not args.core_only:
        for asset in ASSETS['models']:
            destination = APP / 'models' / asset['path']
            cached = CACHE / 'downloads' / asset['filename']
            if destination.exists() and sha256(destination) == asset['sha256']:
                print('Verified model:', asset['path'], flush=True)
                continue
            download(asset, cached, args.offline)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cached, destination)
    command([sys.executable, '-c', 'from PySide6.QtWidgets import QApplication; from PIL import Image; import faster_whisper,kokoro_onnx,soundfile,espeakng_loader; print("All application imports passed")'])
    command([APP / 'bin' / 'ffmpeg.exe', '-v', 'error', '-f', 'lavfi', '-i', 'color=s=32x32:d=0.1', '-f', 'null', '-'])
    lock_hash = sha256(lock)
    (APP / 'runtime' / '.setup-ready').write_text(json.dumps({'requirements_sha256': lock_hash, 'core_only': args.core_only}), encoding='utf-8')
    print('Setup checks passed. Normal use is offline.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        import traceback
        log = APP / 'logs' / 'setup.log'
        log.parent.mkdir(exist_ok=True)
        with log.open('a', encoding='utf-8') as handle:
            traceback.print_exc(file=handle)
        print(f'SETUP FAILED: {error}\nDetails: {log}', file=sys.stderr, flush=True)
        raise SystemExit(1)
