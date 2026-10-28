"""Optional integration test against a prepared T3 checkout with dependencies installed."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SID = '11111111-1111-4111-8111-111111111111'


def varint(number):
    result = bytearray()
    while number > 127:
        result.append((number & 127) | 128)
        number >>= 7
    result.append(number)
    return bytes(result)


def message(*fields):
    result = b''
    for key, value in fields:
        if isinstance(value, int):
            result += varint(key * 8) + varint(value)
        else:
            value = value.encode() if isinstance(value, str) else value
            result += varint(key * 8 + 2) + varint(len(value)) + value
    return result


@unittest.skipUnless(os.environ.get('T3_IMPORT_TEST_CHECKOUT') and shutil.which('node'),
                     'Set T3_IMPORT_TEST_CHECKOUT to a patched checkout with dependencies for integration tests')
class PrepareTests(unittest.TestCase):
    def test_sqlite_fallback_is_read_only_and_preserves_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            db_path = root / (SID + '.db')
            db = sqlite3.connect(db_path)
            db.executescript('''
                CREATE TABLE trajectory_meta(cascade_id TEXT);
                CREATE TABLE trajectory_metadata_blob(id TEXT, data BLOB);
                CREATE TABLE steps(idx INTEGER, step_type INTEGER, step_format INTEGER, step_payload BLOB, metadata BLOB);
            ''')
            db.execute('INSERT INTO trajectory_meta VALUES (?)', (SID,))
            db.execute('INSERT INTO trajectory_metadata_blob VALUES (?, ?)', ('main', message((2, message((1, 1700000000))))))
            timestamp = message((1, message((1, 1700000000))))
            for index, kind, field, text in [(0, 14, 19, 'Synthetic question λ'), (1, 15, 20, 'Synthetic answer')]:
                payload = message((1, kind), (field, message((2 if kind == 14 else 1, text))))
                db.execute('INSERT INTO steps VALUES (?, ?, 0, ?, ?)', (index, kind, payload, timestamp))
            db.commit()
            db.close()
            digest = hashlib.sha256(db_path.read_bytes()).hexdigest()
            (root / 'export-report.json').write_text(json.dumps([{'id': SID, 'source': str(db_path), 'error': 'offline'}]))
            output, fallback = root / 'prepared', root / 'fallback'
            command = ['node', str(ROOT / 'tools/prepare.mjs'), '--checkout', os.environ['T3_IMPORT_TEST_CHECKOUT'],
                       '--input', str(root), '--output', str(output), '--fallback', str(fallback)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            prepared = json.loads((output / (SID + '.trajectory.json')).read_text(encoding='utf-8'))
            self.assertEqual(prepared['steps'][0]['userInput']['userResponse'], 'Synthetic question λ')
            self.assertEqual(prepared['steps'][1]['plannerResponse']['response'], 'Synthetic answer')
            self.assertEqual(prepared['t3Import']['workspaceRoot'], str(fallback))
            self.assertEqual(hashlib.sha256(db_path.read_bytes()).hexdigest(), digest)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
