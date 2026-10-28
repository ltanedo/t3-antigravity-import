"""Keep generated private artifacts outside the public source tree."""
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]


def private_output(value):
    path = Path(value).expanduser().resolve()
    if path == REPOSITORY or REPOSITORY in path.parents:
        raise ValueError("Choose an output directory outside this repository")
    gemini = (Path.home() / '.gemini').resolve()
    if path == gemini or gemini in path.parents:
        raise ValueError("Do not write exports inside the original Antigravity store")
    return path
