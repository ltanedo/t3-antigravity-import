import importlib.util
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import export
from privacy import private_output

SID = '11111111-1111-4111-8111-111111111111'


class ExportTests(unittest.TestCase):
    def test_discovery_prefers_database_and_ignores_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for store, suffix in [('antigravity', '.pb'), ('antigravity-cli', '.db')]:
                directory = root / store / 'conversations'
                directory.mkdir(parents=True)
                (directory / (SID + suffix)).write_bytes(b'synthetic placeholder')
                (directory / 'not-a-conversation.db').write_bytes(b'')
            found = export.discover(root)
            self.assertEqual(list(found), [SID])
            self.assertEqual(found[SID].suffix, '.db')

    def test_private_outputs_cannot_land_in_repository_or_original_store(self):
        with self.assertRaises(ValueError):
            private_output(ROOT / 'exports')
        with self.assertRaises(ValueError):
            private_output(Path.home() / '.gemini' / 'antigravity')
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(private_output(temporary), Path(temporary).resolve())

    def test_loopback_export_identity_and_response_limit(self):
        responses = [{'trajectory': {'cascadeId': SID, 'steps': []}},
                     {'trajectory': {'cascadeId': 'wrong'}},
                     {'trajectory': {'cascadeId': SID, 'padding': 'x' * 100}}]
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append((self.path, self.headers['x-codeium-csrf-token'],
                                 json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                body = json.dumps(responses.pop(0)).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            port = server.server_address[1]
            result = export.fetch_trajectory(port, 'synthetic-local-token', SID)
            self.assertEqual(result['cascadeId'], SID)
            with self.assertRaisesRegex(ValueError, 'identity'):
                export.fetch_trajectory(port, 'synthetic-local-token', SID)
            with patch.object(export, 'MAX_RESPONSE', 32):
                with self.assertRaisesRegex(ValueError, '128 MiB'):
                    export.fetch_trajectory(port, 'synthetic-local-token', SID)
            self.assertEqual(requests[0][0], export.METHOD)
            self.assertTrue(requests[0][2]['disableRehydration'])
            self.assertEqual(requests[0][2]['cascadeId'], SID)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_invalid_identifier_is_rejected_before_network(self):
        with self.assertRaises(ValueError):
            export.fetch_trajectory(1, 'synthetic-local-token', '../not-an-id')


if __name__ == '__main__':
    unittest.main()
