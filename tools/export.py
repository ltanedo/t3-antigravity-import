"""Export local Antigravity trajectories. No requests leave loopback."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from privacy import private_output

UUID = re.compile(r'^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$', re.I)
MAX_RESPONSE = 128 * 1024 * 1024
METHOD = '/exa.language_server_pb.LanguageServerService/GetCascadeTrajectory'
STORES = ('antigravity', 'antigravity-cli', 'antigravity-ide', 'antigravity-backup')


def discover(root):
    files = {}
    for store in STORES:
        for path in (Path(root) / store / 'conversations').glob('*'):
            if not path.is_file() or path.suffix not in ('.db', '.pb') or not UUID.fullmatch(path.stem):
                continue
            previous = files.get(path.stem)
            if previous is None or (path.suffix == '.db' and previous.suffix == '.pb') or (
                path.suffix == previous.suffix and path.stat().st_mtime > previous.stat().st_mtime
            ):
                files[path.stem] = path
    return files


def fetch_trajectory(port, token, session_id):
    if not UUID.fullmatch(session_id):
        raise ValueError('Invalid conversation identifier')
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=25)
    try:
        connection.request('POST', METHOD, json.dumps({
            'cascadeId': session_id,
            'trajectoryVerbosity': 'CLIENT_TRAJECTORY_VERBOSITY_FULL',
            'disableRehydration': True,
        }), {'Content-Type': 'application/json', 'x-codeium-csrf-token': token,
             'Connect-Protocol-Version': '1'})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError('Local service HTTP ' + str(response.status))
        raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise ValueError('Trajectory exceeds 128 MiB')
        trajectory = json.loads(raw).get('trajectory')
        if not isinstance(trajectory, dict) or trajectory.get('cascadeId') != session_id:
            raise ValueError('Trajectory identity mismatch')
        return trajectory
    finally:
        connection.close()


def local_endpoint(pid):
    if os.name != 'nt':
        raise ValueError('Automatic endpoint discovery is Windows-only')
    helper = Path(__file__).resolve().parents[1] / 'scripts' / 'Find-Antigravity.ps1'
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                             '-File', str(helper), '-ProcessId', str(pid or 0)],
                            capture_output=True, text=True)
    if result.returncode:
        # Process output can contain command-line credentials. Never echo it.
        raise ValueError('No unique local server; start Antigravity or select --pid')
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='Private folder outside this repository')
    parser.add_argument('--root', type=Path, default=Path.home() / '.gemini')
    parser.add_argument('--pid', type=int, help='Choose a local Antigravity language-server process')
    parser.add_argument('--offline', action='store_true', help='Inventory SQLite files without a server')
    args = parser.parse_args()
    output = private_output(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / 'export-report.json'
    if report_path.exists():
        raise ValueError('Output already has a report; choose a new export folder')
    conversations = output / 'conversations'
    conversations.mkdir(exist_ok=True)
    files = discover(args.root)
    endpoint = None
    if files and not args.offline:
        try:
            endpoint = local_endpoint(args.pid)
        except ValueError:
            print('Local server unavailable. SQLite files can still be prepared offline.', file=sys.stderr)

    def export_one(item):
        sid, source = item
        record = {'id': sid, 'source': str(source.resolve()), 'error': 'Local export unavailable'}
        if endpoint:
            for port in endpoint['ports']:
                try:
                    trajectory = fetch_trajectory(port, endpoint['token'], sid)
                    with (conversations / (sid + '.trajectory.json')).open('x', encoding='utf-8') as stream:
                        json.dump(trajectory, stream, ensure_ascii=False)
                    record['error'] = None
                    break
                except (OSError, ValueError, http.client.HTTPException):
                    # Do not expose response bodies, tokens, paths, or conversation text in logs.
                    continue
        return record

    with ThreadPoolExecutor(max_workers=2) as pool:
        report = list(pool.map(export_one, files.items()))
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'discovered': len(report), 'exported': sum(r['error'] is None for r in report),
                      'needs_offline_fallback': sum(r['error'] is not None for r in report)}))
    return 0 if all(r['error'] is None for r in report) else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        print('Export stopped: ' + (str(error) if isinstance(error, ValueError) else type(error).__name__), file=sys.stderr)
        sys.exit(1)
