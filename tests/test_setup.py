import importlib.util
import io
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('studio_setup', ROOT / 'scripts/setup/setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class DownloadTests(unittest.TestCase):
    def setUp(self):
        temp_root = ROOT / '.validation' / 'test-tmp'
        temp_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=temp_root)
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'asset.bin'
        self.data = b'the expected downloaded bytes'
        self.asset = {'url': 'https://example.invalid/asset', 'sha256': hashlib.sha256(self.data).hexdigest()}

    def test_valid_offline_cache_never_connects(self):
        self.path.write_bytes(self.data)
        with patch.object(setup.urllib.request, 'urlopen', side_effect=AssertionError('network used')):
            self.assertEqual(setup.download(self.asset, self.path, True), self.path)

    def test_corrupt_offline_cache_is_rejected_without_deletion(self):
        self.path.write_bytes(b'user retained damaged cache')
        with self.assertRaises(RuntimeError):
            setup.download(self.asset, self.path, True)
        self.assertEqual(self.path.read_bytes(), b'user retained damaged cache')

    def test_download_is_atomic_and_verified(self):
        with patch.object(setup.urllib.request, 'urlopen', side_effect=lambda *a, **k: io.BytesIO(self.data)):
            setup.download(self.asset, self.path)
        self.assertEqual(self.path.read_bytes(), self.data)
        self.assertFalse(self.path.with_name('asset.bin.partial').exists())

    def test_bad_download_never_replaces_existing_file(self):
        self.path.write_bytes(b'previous file')
        with patch.object(setup.urllib.request, 'urlopen', side_effect=lambda *a, **k: io.BytesIO(b'bad data')), patch.object(setup.time, 'sleep'):
            with self.assertRaises(RuntimeError):
                setup.download(self.asset, self.path)
        self.assertEqual(self.path.read_bytes(), b'previous file')
        self.assertFalse(self.path.with_name('asset.bin.partial').exists())

    def test_all_manifest_assets_have_hashes_and_https(self):
        assets = setup.ASSETS
        for asset in [assets['python'], assets['pip'], assets['ffmpeg'], assets['vc_runtime']] + assets['models']:
            self.assertRegex(asset['sha256'], r'^[0-9a-f]{64}$')
            self.assertTrue(asset['url'].startswith('https://'))
        self.assertEqual(len({a['path'] for a in assets['models']}), len(assets['models']))

    def test_private_runtime_ignores_global_python_paths(self):
        executable = ROOT / 'app/runtime/python.exe'
        if not executable.exists():
            self.skipTest('Run Install.bat to test the private Windows runtime')
        env = dict(os.environ, PYTHONPATH=str(ROOT.parent / 'unrelated-python-packages'))
        paths = json.loads(subprocess.check_output([str(executable), '-c',
            'import sys,json; print(json.dumps(sys.path))'], env=env, text=True))
        self.assertTrue(paths)
        self.assertTrue(all(Path(p).resolve().is_relative_to(ROOT / 'app') for p in paths), paths)


if __name__ == '__main__':
    unittest.main()
