"""Audit the exact Git index without echoing suspect content."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ROOT = {'README.md', 'LICENSE', 'NOTICE', 'SECURITY.md', 'CONTRIBUTING.md',
                'UPSTREAM_REVISION', '.gitignore', '.gitattributes'}
ALLOWED_DIRS = {'tools', 'scripts', 'tests', 'patches', '.github'}
PATTERNS = {
    'GitHub credential': r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b',
    'private key': r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
    'credential assignment': r'(?i)(?:csrf_token|access_token|refresh_token|api_key)\s*[:=]\s*[\x22\x27][A-Za-z0-9_./+-]{24,}',
    'personal Windows path': r'(?i)[A-Z]:[\\/]+Users[\\/]+(?!Example(?:[\\/]|$)|Public(?:[\\/]|$))[^\s\x22\x27<>]+',
    'personal Unix path': r'/(?:Users|home)/(?!example(?:/|$))[^\s\x22\x27<>]+',
    'email address': r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
}


def inspect(path, data):
    problems = []
    p = Path(path)
    if len(p.parts) == 1 and path not in ALLOWED_ROOT:
        problems.append('unexpected root file')
    elif len(p.parts) > 1 and p.parts[0] not in ALLOWED_DIRS:
        problems.append('unexpected directory')
    if len(data) > 1024 * 1024 or b'\0' in data:
        problems.append('binary or oversized file')
    if re.search(r'(?i)\.(?:db|sqlite\d*|pb|asar|log|pem|key)$|\.trajectory\.json$|-report\.json$', path):
        problems.append('private artifact filename')
    text = data.decode('utf-8', errors='replace')
    for label, pattern in PATTERNS.items():
        if re.search(pattern, text):
            problems.append(label)
    return problems


def main():
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    failures = []
    count = 0
    for path in filter(None, paths):
        data = subprocess.check_output(['git', 'show', ':' + path], cwd=ROOT)
        failures.extend((path, reason) for reason in inspect(path, data))
        count += 1
    if not count:
        raise SystemExit('No staged files to audit')
    for path, reason in failures:
        print(path + ': ' + reason, file=sys.stderr)
    if failures:
        raise SystemExit(1)
    print(f'Audited {count} indexed files: no prohibited artifacts or matched private-data patterns.')


if __name__ == '__main__':
    main()
