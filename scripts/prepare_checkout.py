"""Fetch the pinned upstream source and apply the reviewed patch."""
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    destination = args.destination.expanduser().resolve()
    if destination.exists():
        parser.error('Destination must not exist; existing checkouts are never changed')
    revision = (ROOT / 'UPSTREAM_REVISION').read_text().strip()
    run('git', 'init', str(destination))
    run('git', 'remote', 'add', 'origin', 'https://github.com/pingdotgg/t3code.git', cwd=destination)
    run('git', 'fetch', '--depth=1', 'origin', revision, cwd=destination)
    run('git', 'checkout', '--detach', 'FETCH_HEAD', cwd=destination)
    patch = str(ROOT / 'patches' / 'antigravity-import.patch')
    run('git', 'apply', '--check', patch, cwd=destination)
    run('git', 'apply', patch, cwd=destination)
    print('Pinned checkout prepared. Read upstream AGENTS.md before contributing changes.')


if __name__ == '__main__':
    main()
