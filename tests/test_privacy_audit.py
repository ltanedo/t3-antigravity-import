import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts' / 'verify-public.py'
spec = importlib.util.spec_from_file_location('public_audit', path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def test_rejects_private_artifacts_and_binary_files(self):
        self.assertIn('private artifact filename', audit.inspect('tests/example.db', b'synthetic'))
        self.assertIn('binary or oversized file', audit.inspect('tests/example.py', b'a\0b'))
        self.assertIn('unexpected directory', audit.inspect('userdata/settings.json', b'{}'))

    def test_detects_constructed_credentials_and_email(self):
        token = ('gh' + 'p_' + 'A' * 36).encode()
        email = ('person' + '@' + 'example.org').encode()
        self.assertIn('GitHub credential', audit.inspect('README.md', token))
        self.assertIn('email address', audit.inspect('README.md', email))

    def test_allows_synthetic_documentation(self):
        self.assertEqual(audit.inspect('README.md', b'Local history import; no real fixtures.'), [])


if __name__ == '__main__':
    unittest.main()
