"""Build taktone firmware from stock files in firmware/."""
from pathlib import Path
import runpy
import sys

if __name__ == '__main__':
    internal = Path(__file__).resolve().parent / 'internal'
    sys.path.insert(0, str(internal))
    runpy.run_path(str(internal / 'patch.py'), run_name='__main__')
