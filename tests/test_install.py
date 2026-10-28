import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Installer targets Windows only')
class InstallerTests(unittest.TestCase):
    def test_verify_install_rollback_and_integrity_rejection(self):
        with tempfile.TemporaryDirectory(prefix='synthetic-agy-install-', dir=ROOT.parent) as temporary:
            root = Path(temporary)
            install, bundle = root / 'installation', root / 'bundle'
            resources = install / 'resources'
            resources.mkdir(parents=True)
            bundle.mkdir()
            original, updated = b'synthetic original archive', b'synthetic updated archive'
            current = resources / 'server.asar'
            current.write_bytes(original)
            (bundle / 'server.asar').write_bytes(updated)
            manifest = {'originalSha256': hashlib.sha256(original).hexdigest(),
                        'updatedSha256': hashlib.sha256(updated).hexdigest(), 'nativeHashes': {}}
            (bundle / 'manifest.json').write_text(json.dumps(manifest))
            command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                       str(ROOT / 'scripts/Install-Windows.ps1'), '-Bundle', str(bundle),
                       '-InstallDirectory', str(install), '-T3Home', str(root / 'profile')]

            def run(*args):
                return subprocess.run([*command, *args], capture_output=True, text=True)

            verified = run('-VerifyOnly')
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(current.read_bytes(), original)
            installed = run()
            self.assertEqual(installed.returncode, 0, installed.stderr)
            self.assertEqual(current.read_bytes(), updated)
            self.assertFalse((root / 'profile/userdata/statev2.sqlite').exists())
            restored = run('-Restore')
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual(current.read_bytes(), original)
            (bundle / 'server.asar').write_bytes(b'corrupted synthetic update')
            self.assertNotEqual(run().returncode, 0)
            self.assertEqual(current.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
