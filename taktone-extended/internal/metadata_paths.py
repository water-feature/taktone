"""Keep project JSON metadata/reports separate from code and firmware files."""
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
REPORTS = PROJECT / 'reports'


def json_path(path):
    """Resolve legacy project JSON locations into reports/, preserving names.

    Emulator configuration and external files retain their original locations.
    Firmware sidecars live at reports/candidates/<firmware stem>.json.
    """
    path = Path(path)
    if path.suffix != '.json':
        return path
    try:
        relative = path.resolve().relative_to(PROJECT)
    except ValueError:
        return path
    if len(relative.parts) == 1 or relative.parts[0] == 'candidates':
        target = REPORTS / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
    return path
